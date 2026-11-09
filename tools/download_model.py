"""Run from repository root: python tools/download_model.py --model base.en."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ppt_ai_coach.errors import CoachError  # noqa: E402
from ppt_ai_coach.transcription import MODEL_NAMES, Transcriber  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download/load a CPU int8 Whisper model")
    parser.add_argument("--model", choices=MODEL_NAMES, default="base.en")
    parser.add_argument("--offline", action="store_true", help="Check cached files without network")
    args = parser.parse_args()
    try:
        Transcriber(args.model, args.offline).load()
        print(f"Ready: {args.model}, CPU int8")
    except CoachError as exc:
        parser.exit(1, f"{exc}\n")
