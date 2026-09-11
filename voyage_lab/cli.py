"""CLI supports a complete offline comparison and verified import."""

import argparse
from pathlib import Path

from .core import KNOT
from .fixtures import FIXTURES, default_scenario, load_environment
from .models import ExportBundle, Scenario
from .replay import export_run, replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Compare three speeds against an offline fixture")
    demo.add_argument("--fixture", choices=list(FIXTURES), default="moving-storm")
    demo.add_argument("--speeds", nargs=3, type=float, default=[10, 12, 14], metavar="KNOTS")
    demo.add_argument("--output", type=Path, default=Path("artifacts/comparison.json"))
    run = commands.add_parser("simulate", help="Run a Scenario JSON document")
    run.add_argument("input", type=Path)
    run.add_argument("--output", type=Path, default=Path("artifacts/run.json"))
    check = commands.add_parser("replay", help="Verify a complete exported comparison")
    check.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "replay":
            bundle = replay(ExportBundle.model_validate_json(args.input.read_text(encoding="utf-8")))
            print(f"Verified {len(bundle.runs)} run(s), including every trajectory sample.")
        elif args.command == "demo":
            base = default_scenario().model_dump()
            base["environment"] = load_environment(args.fixture)
            bundle = ExportBundle(
                runs=[
                    export_run(Scenario.model_validate(base | {"speed_mps": s * KNOT})) for s in args.speeds
                ]
            )
        else:
            bundle = ExportBundle(
                runs=[export_run(Scenario.model_validate_json(args.input.read_text(encoding="utf-8")))]
            )
        if args.command != "replay":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(bundle.model_dump_json(), encoding="utf-8")
            print(f"Saved {args.output}")
        for run in bundle.runs:
            r = run.result
            print(
                f"{run.scenario.speed_mps / KNOT:4.1f} kn | {r['status']:18} | {r['elapsed_s'] / 3600:6.2f} h | "
                f"{r['fuel_kg'] / 1000:6.2f} t | USD {r['total_cost']:,.2f}"
            )
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
