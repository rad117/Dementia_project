"""
nurse_observer.py
-----------------
Per-clip structured observation using Qwen2.5-VL.

Replaces free-text description with a fixed schema, so observations can be
compared across time by care_state.py. The VLM reports only what it SEES.
It does not assign risk -- risk needs history, and this layer has none.
"""

import json
import re
import time

import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor


DEFAULT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"

SYSTEM_PROMPT = (
    "You are a visual observer for a home safety monitor. You report only what "
    "is directly visible in the clip. You never guess identity, diagnosis, mood, "
    "or intent. When something is unclear or out of frame, you say 'unknown'. "
    "You reply with JSON only."
)

SCHEMA_PROMPT = """Observe this clip and reply with ONE JSON object, no other text:

{
  "person_present": true or false,
  "posture": "standing" | "sitting" | "lying" | "kneeling" | "bent_over" | "unknown",
  "on_floor": true or false,
  "motion": "active" | "slow" | "still" | "none",
  "location": "<short phrase, e.g. 'at the kitchen counter'>",
  "hands": "<what the hands are holding or doing, or 'empty'>",
  "activity": "<short verb phrase, e.g. 'stirring a pot', or 'none'>",
  "appliances": [
    {"name": "<burner|stove|oven|microwave|toaster|kettle|tap>",
     "state": "on" | "off" | "unknown"}
  ],
  "water_running": true or false,
  "door_open": true or false,
  "sharp_or_hot_object_in_hand": true or false,
  "visible_smoke_or_flame": true or false,
  "unsteady_or_swaying": true or false,
  "fall_in_progress": true or false,
  "sudden_descent": true or false,
  "note": "<one short sentence ONLY if something is unusual, else empty string>"
}

Rules:
- "on_floor" is true only if the torso is on the ground, not merely low or seated.
- "fall_in_progress" is true if, ACROSS the frames of this clip, the person is
  visibly losing balance, collapsing, or dropping -- not yet settled.
- "sudden_descent" is true if the person's height in frame drops sharply between
  the first and last frame, e.g. from standing to floor, or down a stairway.
  Set it true even if the final position is unclear or out of frame.
- List an appliance only if you can actually see it. Use "unknown" for its state
  if you cannot tell whether it is on.
- "visible_smoke_or_flame" means smoke or open flame in the room, not a lit burner.
- If no person is visible, set person_present false and still report appliances,
  water, doors and smoke."""


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of the model's reply."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON in reply: {text[:200]}")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"unterminated JSON: {text[:200]}")


EMPTY_OBSERVATION = {
    "person_present": False,
    "posture": "unknown",
    "on_floor": False,
    "motion": "none",
    "location": "unknown",
    "hands": "unknown",
    "activity": "none",
    "appliances": [],
    "water_running": False,
    "door_open": False,
    "sharp_or_hot_object_in_hand": False,
    "visible_smoke_or_flame": False,
    "unsteady_or_swaying": False,
    "fall_in_progress": False,
    "sudden_descent": False,
    "note": "",
}


class NurseObserver:
    def __init__(self, model_id: str = DEFAULT_MODEL, device: str = "cuda",
                 max_pixels: int = 768 * 28 * 28):
        print(f"Loading {model_id} ...")
        t0 = time.time()
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
            device_map=device,
        )
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(
            model_id, min_pixels=256 * 28 * 28, max_pixels=max_pixels
        )
        self.device = device
        print(f"Observer ready in {time.time() - t0:.1f}s")

    def observe(self, frames, fps: float = 2.0) -> dict:
        """
        Args:
            frames: list of RGB numpy arrays or PIL Images (4-8 frames)
        Returns:
            observation dict matching the schema, plus "_latency_s" and "_raw"
        """
        if not frames:
            return {**EMPTY_OBSERVATION, "_latency_s": 0.0, "_raw": ""}

        pil = [f if isinstance(f, Image.Image) else Image.fromarray(f)
               for f in frames]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "video", "video": pil, "fps": fps},
                {"type": "text", "text": SCHEMA_PROMPT},
            ]},
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text], videos=[pil], return_tensors="pt", padding=True
        ).to(self.device)

        t0 = time.time()
        with torch.inference_mode():
            out = self.model.generate(
                **inputs, max_new_tokens=400, do_sample=False,
                temperature=None, top_p=None,
            )
        latency = time.time() - t0

        trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out)]
        raw = self.processor.batch_decode(
            trimmed, skip_special_tokens=True
        )[0].strip()

        try:
            obs = {**EMPTY_OBSERVATION, **_extract_json(raw)}
        except Exception as e:
            print(f"  [parse failed: {e}]")
            obs = dict(EMPTY_OBSERVATION)

        obs["_latency_s"] = round(latency, 2)
        obs["_raw"] = raw
        return obs