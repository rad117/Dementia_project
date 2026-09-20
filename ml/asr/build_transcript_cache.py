"""Batch-transcribes the ADReSSo dataset and caches results to disk.

Run as: python -m ml.asr.build_transcript_cache
        python -m ml.asr.build_transcript_cache --limit 3   # smoke test

Standalone script -- does NOT touch ml/training/train_baseline.py or the
manifest schema. It produces data/adresso2021_transcripts_cache.csv, which
the future ml/nlp/ layer (and a later retrain step) will consume. Resumable:
already-cached filepaths are skipped on re-run, and the cache is rewritten
after every new transcription so an interrupted run loses no progress.
"""

import argparse
from pathlib import Path

import pandas as pd

from ml.asr.transcribe import TranscriptionError, transcribe
from ml.preprocessing.manifest import build_manifest

_CACHE_COLUMNS = [
    "participant_id",
    "filepath",
    "transcript_text",
    "word_count",
    "avg_logprob",
    "no_speech_prob",
]

DEFAULT_CACHE_PATH = Path("data/adresso2021_transcripts_cache.csv")


def _load_cache(cache_path: Path) -> list[dict]:
    if not cache_path.exists():
        return []
    return pd.read_csv(cache_path)[_CACHE_COLUMNS].to_dict("records")


def build_transcript_cache(
    data_root: Path = Path("data/adresso2021"),
    cache_path: Path = DEFAULT_CACHE_PATH,
    *,
    language: str = "en",
    model_size: str = "small.en",
    limit: int | None = None,
) -> pd.DataFrame:
    manifest = build_manifest(data_root)
    if limit is not None:
        manifest = manifest.head(limit)

    rows = _load_cache(cache_path)
    cached_filepaths = {row["filepath"] for row in rows}

    for _, record in manifest.iterrows():
        filepath = record["filepath"]
        if filepath in cached_filepaths:
            continue
        try:
            result = transcribe(Path(filepath), language=language, model_size=model_size)
        except TranscriptionError as exc:
            print(f"SKIP {filepath}: {exc}")
            continue

        rows.append(
            {
                "participant_id": record["participant_id"],
                "filepath": filepath,
                "transcript_text": result["transcript_text"],
                "word_count": result["word_count"],
                "avg_logprob": result["avg_logprob"],
                "no_speech_prob": result["no_speech_prob"],
            }
        )
        cached_filepaths.add(filepath)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=_CACHE_COLUMNS).to_csv(cache_path, index=False)
        print(f"OK   {filepath} ({result['word_count']} words)")

    return pd.DataFrame(rows, columns=_CACHE_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/adresso2021"))
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--language", default="en")
    parser.add_argument("--model-size", default="small.en")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    df = build_transcript_cache(
        data_root=args.data_root,
        cache_path=args.cache_path,
        language=args.language,
        model_size=args.model_size,
        limit=args.limit,
    )
    print(f"\n{len(df)} transcripts cached at {args.cache_path}")


if __name__ == "__main__":
    main()
