"""Check bundle file hashes and create a clean run tree without archived outputs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def verify_manifest(root, entries):
    for path, info in entries.items():
        file = root / path
        if not file.is_file() or file.stat().st_size != info["bytes"]:
            raise ValueError(f"Missing or wrong-size frozen file: {file}")
        with file.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != info["sha256"]:
                raise ValueError(f"Hash differs for frozen file: {file}")


def main():
    source, output = map(Path, sys.argv[1:])
    entries = json.loads((source / "MANIFEST.json").read_text())["files"]
    verify_manifest(source, entries)
    print(f"Verified {len(entries)} frozen file hashes and byte lengths")
    shutil.copytree(source, output, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("generated", "*.log", "*.err"))
    (output / "generated").mkdir()


if __name__ == "__main__":
    main()
