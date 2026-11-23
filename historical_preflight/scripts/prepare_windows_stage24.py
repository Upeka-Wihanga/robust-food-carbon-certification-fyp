"""Port the frozen multiprocessing entry points in a verified run copy."""

from pathlib import Path
import sys
from textwrap import indent

from prepare_run import main as prepare_run


def replace_once(source: str, original: str, replacement: str) -> str:
    if source.count(original) != 1:
        raise ValueError(f"Unexpected frozen Stage 24 source around {original!r}")
    return source.replace(original, replacement)


def main() -> None:
    # Verify the untouched manifest before modifying any bytes in the run copy.
    prepare_run()
    archive, output = map(Path, sys.argv[1:])
    for name in ("stage24_targeted_scenario.py", "stage24_secondary_saturation_mp.py"):
        path = output / "scripts" / name
        source = replace_once(path.read_text(encoding="utf-8"), "'fork'", "'spawn'")
        if name == "stage24_targeted_scenario.py":
            imports, body = source.split("ap=argparse.ArgumentParser()", 1)
            source = imports + 'if __name__ == "__main__":\n' + indent(
                "ap=argparse.ArgumentParser()" + body, "    "
            )
        path.write_text(source, encoding="utf-8")
    driver = output / "reproduce.py"
    # Check the source archive again inside the driver without changing its manifest.
    source = driver.read_text(encoding="utf-8")
    driver.write_text(
        replace_once(source, "p=ROOT/rel", f"p=Path({str(archive.resolve())!r})/rel"),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
