"""Run the recovered Stage 20/22 scripts inside a fresh output tree."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "evidence/frozen"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage18_run", type=Path)
    args = parser.parse_args()
    inputs = args.stage18_run.resolve()
    bundle = FROZEN / "stage24/portable/Stage24_Portable_Reproduction"
    scripts = FROZEN / "stage22/portable/scripts"
    output = Path(tempfile.mkdtemp(prefix="stage22.", dir=ROOT / "results"))
    print(f"Run directory: {output}", flush=True)
    for name in ("stage13_guan_external", "stage18_34", "stage18_567", "stage18_recovery"):
        shutil.copytree(bundle / name, output / name)
    for name in ("Carbon footprint and nutrition estimation of Chinese cuisines.xlsx",
                 "Recipes_WWEIA_FCID_0510.csv"):
        shutil.copyfile(bundle / name, output / name)
    for path in (inputs / "generated").glob("Stage18_2_*_Action_Results.csv"):
        shutil.copyfile(path, output / "stage18_recovery" / path.name)
    for name in ("stage20_recovery", "stage22_recovery"):
        (output / name).mkdir()
    os.chdir(output)
    state = {"__name__": "__main__"}
    for path in sorted(scripts.glob("*.py")):
        print(f"Running {path.name}", flush=True)
        source = path.read_text(encoding="utf-8").replace(
            'Path("/mnt/data")', "Path.cwd()"
        ).replace('Path("/mnt/data/', 'Path("')
        state["__file__"] = str(path)
        exec(compile(source, str(path), "exec"), state)


if __name__ == "__main__":
    main()
