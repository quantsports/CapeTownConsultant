"""
User-facing CLI with helpful flags.
"""
import argparse
from pathlib import Path
from .generate import generate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="project-generator",
        description="Generate the Multi-Agent Research System scaffold."
    )
    p.add_argument(
        "-r", "--root", type=Path, default=Path.cwd(),
        help="Target project root directory (default: current working directory)"
    )
    p.add_argument(
        "-f", "--force", action="store_true",
        help="Overwrite files if they already exist"
    )
    p.add_argument(
        "-q", "--quiet", action="store_true",
        help="Minimal output"
    )
    return p


def main(argv: list[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    generate(project_root=args.root, overwrite=args.force, quiet=args.quiet)


if __name__ == "__main__":
    main()
