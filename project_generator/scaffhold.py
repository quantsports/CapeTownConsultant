"""
Low-level filesystem operations for creating files and dirs.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple, List


@dataclass
class WriteResult:
    path: Path
    created: bool
    skipped: bool
    reason: str = ""


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text_file(path: Path, content: str, overwrite: bool) -> WriteResult:
    ensure_parent(path)
    if path.exists() and not overwrite:
        return WriteResult(path=path, created=False, skipped=True, reason="exists")
    path.write_text(content)
    return WriteResult(path=path, created=True, skipped=False)


def create_init_dirs(dirs: Iterable[str], project_root: Path, overwrite: bool) -> List[WriteResult]:
    results: List[WriteResult] = []
    for d in dirs:
        init_file = project_root / d / "__init__.py"
        ensure_parent(init_file)
        if not init_file.exists() or overwrite:
            init_file.write_text('"""Package"""')
            results.append(WriteResult(path=init_file, created=True, skipped=False))
        else:
            results.append(WriteResult(path=init_file, created=False, skipped=True, reason="exists"))
    return results


def generate_from_specs(
    specs: Iterable[Tuple[Path, str]],
    overwrite: bool,
) -> List[WriteResult]:
    return [write_text_file(path, content, overwrite=overwrite) for path, content in specs]
