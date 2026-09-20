"""Builds linguistic/semantic features from cached ASR transcripts.

Run as: python -m ml.nlp.build_linguistic_cache

Reads data/adresso2021_transcripts_cache.csv (produced by
ml/asr/build_transcript_cache.py) and writes
data/adresso2021_linguistic_cache.csv, one row per transcript. Standalone --
does not touch ml/training/train_baseline.py. Depends entirely on the ASR
cache already existing; run the ASR batch first.
"""

import argparse
from pathlib import Path

import pandas as pd

from ml.nlp.linguistic import LinguisticFeatureError, extract_linguistic_features

DEFAULT_TRANSCRIPTS_PATH = Path("data/adresso2021_transcripts_cache.csv")
DEFAULT_CACHE_PATH = Path("data/adresso2021_linguistic_cache.csv")


def build_linguistic_cache(
    transcripts_path: Path = DEFAULT_TRANSCRIPTS_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> pd.DataFrame:
    transcripts = pd.read_csv(transcripts_path)

    rows = []
    for _, record in transcripts.iterrows():
        try:
            feats = extract_linguistic_features(str(record["transcript_text"]))
        except LinguisticFeatureError as exc:
            print(f"SKIP {record['filepath']}: {exc}")
            continue
        rows.append(
            {
                "participant_id": record["participant_id"],
                "filepath": record["filepath"],
                **feats,
            }
        )
        print(f"OK   {record['filepath']}")

    df = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts-path", type=Path, default=DEFAULT_TRANSCRIPTS_PATH)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH)
    args = parser.parse_args()

    df = build_linguistic_cache(args.transcripts_path, args.cache_path)
    print(f"\n{len(df)} linguistic feature rows cached at {args.cache_path}")


if __name__ == "__main__":
    main()
