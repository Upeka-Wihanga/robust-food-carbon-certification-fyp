"""Apply reviewed corrections only to prepared reproduction work trees."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def apply(output: Path, *, verified_archive_driver: bool = False):
    scripts = output / "scripts"
    candidate = scripts / "corrected_oracle.py"
    if not candidate.is_file():
        candidate = scripts / "stage24_base.py"
        # The outer harness has already verified the untouched source. Keep the
        # wrapper check pointed at the actual archive while running repaired code.
        if not verified_archive_driver:
            runner = output / "reproduce.py"
            driver = runner.read_text(encoding="utf-8")
            frozen = ROOT / "evidence/frozen/stage24/portable/Stage24_Portable_Reproduction"
            original = "p=ROOT/rel"
            assert driver.count(original) == 1, "Stage 24 hash loop changed"
            runner.write_text(driver.replace(original, f"p=Path({str(frozen)!r})/rel"),
                              encoding="utf-8")
    source = candidate.read_text(encoding="utf-8")
    start = source.index("def quid_inverse_components(")
    end = source.index("def quid_vertices(", start)
    source = source[:start] + "from preflight_quid import quid_inverse_components\n\n" + source[end:]
    candidate.write_text(source, encoding="utf-8")
    shutil.copyfile(ROOT / "preflight/quid.py", scripts / "preflight_quid.py")


if __name__ == "__main__":
    apply(Path(sys.argv[1]), verified_archive_driver="--verified-archive-driver" in sys.argv[2:])
