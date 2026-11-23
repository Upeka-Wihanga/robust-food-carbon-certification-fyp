"""Unpack standalone research packets into the independent WSL project."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKETS = {
    "handoff": "Codex_Research_Handoff_v1.zip",
    "stage11": "Stage11BA6_Blind_Reviewer_Packet_FROZEN.zip",
    "stage14": "Stage14_QUID_Disclosure_Precision_Blind_Review_FROZEN.zip",
    "stage16": "Stage17_Corrected_Disclosure_Sufficiency_Blind_Review_FROZEN.zip",
    "stage18": "Stage19_Strengthened_Contribution_Blind_Review_FROZEN.zip",
    "stage20": "Final_PreImplementation_Blind_Review_FROZEN.zip",
    "stage22": "Stage22_Information_Frontier_Blind_Review_FROZEN.zip",
    "stage24": "Stage24_Targeted_Acquisition_Blind_Review_FROZEN.zip",
}
NESTED = {
    "stage18": "reviewer_packet/16_Portable_Reproduction_Bundle.zip",
    "stage22": "reviewer_packet/09_Stage22_Evidence_Package.zip",
    "stage24": "reviewer_packet/11_Portable_Reproduction.zip",
}
DOCUMENTS = (
    "FYP_Proposal_Robust_Food_Carbon_Certification_2026_27.pdf",
    "Stage26_Frozen_Protocol_v1.md",
    "MASTER_Progress_Tracker_Stage26_After_Preflight.md",
)


def unpack(archive, destination):
    for entry in archive.infolist():
        path = PurePosixPath(entry.filename)
        if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                or (entry.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError(f"Unsafe ZIP entry: {entry.filename}")
        if entry.is_dir():
            continue
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(entry) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory with the supplied ZIPs and proposal")
    args = parser.parse_args()
    frozen = ROOT / "evidence/frozen"
    for name in (*PACKETS.values(), *DOCUMENTS):
        if not (args.input_dir / name).is_file():
            parser.error(f"Missing standalone input: {name}")
    for label, filename in PACKETS.items():
        with zipfile.ZipFile(args.input_dir / filename) as archive:
            unpack(archive, frozen / label)
            if label in NESTED:
                with zipfile.ZipFile(io.BytesIO(archive.read(NESTED[label]))) as nested:
                    unpack(nested, frozen / label / "portable")
    for filename in DOCUMENTS:
        shutil.copyfile(args.input_dir / filename, frozen / filename)
    sources = {}
    for filename in (*PACKETS.values(), *DOCUMENTS):
        source = args.input_dir / filename
        sources[filename] = {
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    (frozen / "source_hashes.json").write_text(json.dumps(sources, indent=2) + "\n")
    print(f"Imported {len(sources)} standalone inputs into {frozen.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
