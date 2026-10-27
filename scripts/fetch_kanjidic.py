#!/usr/bin/env python3
"""Download KANJIDIC2 XML dictionary into data/kanji/.

Idempotent: skips download if the file already exists unless --force is given.
The .gz file is gitignored (third-party reference data, like data/cache/).
"""

import argparse
import sys
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
KANJIDIC_URL = "https://www.edrdg.org/kanjidic/kanjidic2.xml.gz"
OUT_FILE = ROOT / "data" / "kanji" / "kanjidic2.xml.gz"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download KANJIDIC2 XML dictionary")
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if file exists"
    )
    parser.add_argument(
        "--url", default=KANJIDIC_URL, help="KANJIDIC2 XML.gz URL"
    )
    args = parser.parse_args()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if OUT_FILE.exists() and not args.force:
        size = OUT_FILE.stat().st_size
        print(f"KANJIDIC2 already present: {OUT_FILE} ({size:,} bytes)")
        return 0

    print(f"Downloading {args.url} -> {OUT_FILE}")
    try:
        urllib.request.urlretrieve(args.url, str(OUT_FILE))
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return 1

    size = OUT_FILE.stat().st_size
    print(f"Downloaded {size:,} bytes to {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())