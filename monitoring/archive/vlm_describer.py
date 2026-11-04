"""
vlm_describer.py
----------------
Fine-grained scene description using Qwen2.5-VL.

Unlike the previous design, this sends ACTUAL IMAGE FRAMES to the model,
as a short video clip, so the model can describe motion and fine detail
("reaching into the upper cabinet with the left hand") rather than a
three-word pose label.

Model: Qwen/Qwen2.5-VL-7B-Instruct
  bf16  ~16 GB VRAM  -> fits A5000 24GB
  AWQ   ~7 GB VRAM   -> use if you want headroom for YOLO + others
"""

import time
import torch
from PIL import Image

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor


DEFAULT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


SYSTEM_PROMPT = (
    "You are a careful observer watching a short clip from a home monitoring "
    "camera. The person may be an older adult living with dementia. "
    "Describe ONLY what you can actually see. Never guess identity, mood, or "
    "medical state. If something is unclear or out of frame, say so."
)

DESCRIBE_PROMPT = """Describe this clip in detail. Cover, in plain prose:

1. The person: where they are in the room, body position, which way they face.
2. Hands: what each hand is holding or touching, and what it is doing.
3. The action across the clip: what changes between the first and last frame.
4. Objects in reach: appliances, burners, taps, doors, containers, and whether
   each appears on/off, open/closed, occupied/empty.
5. Anything unsafe or unusual, stated as an observation, not a conclusion.

Write 4-8 sentences. Be specific and concrete. If no person is visible, say
that plainly and describe the room and the state of any appliances instead."""


class VLMDescriber:
    """Wraps Qwen2.5-VL for clip-level free-text description."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        device: str = "cuda",
        max_new_tokens: int = 320,
        min_pixels: int = 256 * 28 * 28,
        max_pixels: int = 768 * 28 * 28,
    ):
        """
        min_pixels / max_pixels bound how many visual tokens each frame costs.
        Lowering max_pixels is the main lever for speed and VRAM.
        """
        print(f"Loading {model_id} ... (first run downloads ~16 GB)")
        t0 = time.time()

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
            device_map=device,
        )
        self.model.eval()

        self.processor = AutoProcessor.from_pretrained(
            model_id,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

        self.max_new_tokens = max_new_tokens
        self.device = device
        print(f"VLM ready in {time.time() - t0:.1f}s")

    # ------------------------------------------------------------------

    def describe_clip(self, frames, fps: float = 2.0, prompt: str = None) -> dict:
        """
        Args:
            frames: list of PIL.Image (or numpy RGB arrays), typically 4-8 frames
                    spanning ~2-4 seconds
            fps:    the sampling rate the frames were captured at
            prompt: override the default description prompt

        Returns:
            {"description": str, "latency_s": float, "n_frames": int}
        """
        if not frames:
            return {"description": "", "latency_s": 0.0, "n_frames": 0}

        pil_frames = [
            f if isinstance(f, Image.Image) else Image.fromarray(f)
            for f in frames
        ]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "video", "video": pil_frames, "fps": fps},
                    {"type": "text", "text": prompt or DESCRIBE_PROMPT},
                ],
            },
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(
            text=[text],
            videos=[pil_frames],
            return_tensors="pt",
            padding=True,
        ).to(self.device)

        t0 = time.time()
        with torch.inference_mode():
            out_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
            )
        latency = time.time() - t0

        trimmed = [
            out[len(inp):]
            for inp, out in zip(inputs.input_ids, out_ids)
        ]
        description = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        return {
            "description": description,
            "latency_s": round(latency, 2),
            "n_frames": len(pil_frames),
        }

    # ------------------------------------------------------------------

    def compare_to_previous(self, frames, previous_description: str,
                            fps: float = 2.0) -> dict:
        """
        Describe the clip with the previous description as context, so the model
        reports CHANGE rather than repeating static scene content. Useful for
        long monitoring sessions where most clips look the same.
        """
        prompt = (
            f"For context, the previous clip was described as:\n"
            f"\"{previous_description}\"\n\n"
            f"Now describe the current clip. Lead with what has CHANGED since "
            f"the previous clip (position, hands, objects, appliance state). "
            f"If essentially nothing changed, say so in one sentence and note "
            f"roughly how the person is positioned. Then note anything newly "
            f"unsafe or unusual."
        )
        return self.describe_clip(frames, fps=fps, prompt=prompt)


if __name__ == "__main__":
    # Smoke test: describe a clip made from a local video file
    import sys
    import cv2

    if len(sys.argv) < 2:
        print("Usage: python vlm_describer.py <video_file.mp4>")
        sys.exit(1)

    cap = cv2.VideoCapture(sys.argv[1])
    frames = []
    while len(frames) < 8:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        for _ in range(14):          # sample ~2 fps from a 30fps source
            cap.read()
    cap.release()

    describer = VLMDescriber()
    result = describer.describe_clip(frames)
    print(f"\n--- {result['n_frames']} frames, {result['latency_s']}s ---")
    print(result["description"])