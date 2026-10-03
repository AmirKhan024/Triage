"""Download NLBSE'24 benchmark dataset into data/ directory.

Downloads:
- data/issues_train.csv
- data/issues_test.csv
"""

import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/nlbse2024/issue-report-classification/main/data"
DATA_FILES = ["issues_train.csv", "issues_test.csv"]


def download_benchmark_data(output_dir: Path | None = None) -> None:
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent / "data"

    output_dir.mkdir(parents=True, exist_ok=True)

    for filename in DATA_FILES:
        target_path = output_dir / filename
        url = f"{BASE_URL}/{filename}"
        print(f"Downloading {url} -> {target_path}...")
        try:
            urllib.request.urlretrieve(url, target_path)
            size_kb = target_path.stat().st_size / 1024
            print(f"Saved {filename} ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"Error downloading {filename}: {e}", file=sys.stderr)
            raise


if __name__ == "__main__":
    download_benchmark_data()
