import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ppt_ai_coach.demo import create_demo  # noqa: E402
from ppt_ai_coach.storage import data_dir  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an original fictional demo PPTX")
    parser.add_argument("--output", type=Path, default=data_dir() / "demo" / "OrbitDesk.pptx")
    args = parser.parse_args()
    print(create_demo(args.output))
