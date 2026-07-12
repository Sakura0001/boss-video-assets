#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path
from typing import Dict, List


EXCLUDED_DIRS = {"__pycache__", ".git"}
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db"}


def _included(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def _files(root: Path) -> Dict[Path, Path]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if _included(path, root)
    }


def compare_trees(source: Path, destination: Path) -> List[str]:
    source = source.resolve()
    destination = destination.resolve()
    source_files = _files(source)
    destination_files = _files(destination)
    differences: List[str] = []

    for relative in sorted(source_files.keys() - destination_files.keys()):
        differences.append(f"missing:{relative}")
    for relative in sorted(destination_files.keys() - source_files.keys()):
        differences.append(f"stale:{relative}")
    for relative in sorted(source_files.keys() & destination_files.keys()):
        if source_files[relative].read_bytes() != destination_files[relative].read_bytes():
            differences.append(f"changed:{relative}")
    return differences


def sync_tree(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or destination in source.parents or source in destination.parents:
        raise ValueError("source and destination must be separate trees")
    if not source.is_dir():
        raise FileNotFoundError(source)

    destination.mkdir(parents=True, exist_ok=True)
    source_files = _files(source)
    destination_files = _files(destination)

    for relative in sorted(destination_files.keys() - source_files.keys(), reverse=True):
        destination_files[relative].unlink()

    for relative, source_file in source_files.items():
        destination_file = destination / relative
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)

    for directory in sorted(
        (path for path in destination.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if directory.name in EXCLUDED_DIRS:
            shutil.rmtree(directory)
        elif not any(directory.iterdir()):
            directory.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the authoritative installed Boss skill")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        differences = compare_trees(args.source, args.destination)
        if differences:
            print("\n".join(differences))
            return 1
        print("Skill mirror is in sync.")
        return 0

    sync_tree(args.source, args.destination)
    print(f"Synced {args.source} -> {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
