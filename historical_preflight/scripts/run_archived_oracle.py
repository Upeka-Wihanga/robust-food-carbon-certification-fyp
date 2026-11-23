"""Run the recoverable Stage 16 randomized LP gate separately from its A4 gate."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evidence/frozen/stage16/reviewer_packet"


def main():
    # The archived A4 comparison requires an unavailable standalone A4 module.
    oracle = next(PACKET.glob("20_*.py"))
    validator = next(PACKET.glob("21_*.py"))
    source = validator.read_text().split("# Exact-point compatibility", maxsplit=1)[0]
    source = source.replace("sys.path.insert(0,'/mnt/data/stage16_corrected_validation')\n", "")
    oracle_source = oracle.read_text()
    from types import ModuleType

    module = ModuleType("stage16_corrected_oracle")
    sys.modules[module.__name__] = module
    exec(compile(oracle_source, str(oracle), "exec"), module.__dict__)
    state = {}
    exec(compile(source, str(validator), "exec"), state)
    report = {"cases": len(state["records"]), "direction_mismatches": state["mism"],
              "maximum_lower_error": state["maxL"], "maximum_upper_error": state["maxU"]}
    print(json.dumps(report, indent=2))
    if report["cases"] != 220 or report["direction_mismatches"] or max(
        report["maximum_lower_error"], report["maximum_upper_error"]
    ) > 1e-9:
        raise SystemExit("Archived randomized oracle gate failed")


if __name__ == "__main__":
    main()
