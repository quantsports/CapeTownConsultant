"""
High-level generation flow and pretty printing.
"""
from pathlib import Path
from typing import Iterable, List, Tuple
from .files_catalog import iter_file_specs, INIT_DIRS, NEXT_STEPS
from .scaffold import generate_from_specs, create_init_dirs, WriteResult


def _print_header():
    print("🚀 Generating Multi-Agent Research System...\n")


def _print_result(results: List[WriteResult], label: str):
    created = sum(1 for r in results if r.created)
    skipped = sum(1 for r in results if r.skipped)
    print(f"{label}: {created} created, {skipped} skipped")


def _print_each(results: List[WriteResult]):
    for r in results:
        if r.created:
            print(f"✅ Created: {r.path}")
        elif r.skipped:
            print(f"⏭️  Skipped (exists): {r.path}")


def _print_next_steps():
    print("\nNext steps:")
    for i, step in enumerate(NEXT_STEPS, 1):
        print(f"{i}. {step}")


def generate(project_root: str | Path, overwrite: bool = False, quiet: bool = False) -> None:
    root = Path(project_root).resolve()
    if not quiet:
        _print_header()

    file_results = generate_from_specs(iter_file_specs(root), overwrite=overwrite)
    init_results = create_init_dirs(INIT_DIRS, root, overwrite=overwrite)

    if not quiet:
        _print_each(file_results + init_results)
        print()
        _print_result(file_results, "Files")
        _print_result(init_results, "Init dirs")
        print("\n✅ Project generated successfully!\n")
        _print_next_steps()
