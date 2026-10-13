from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
MAX_FILES = 2000


def package_static_directory(source: Path, output: Path, *, overwrite: bool = False) -> dict[str, int | str]:
    source = Path(source)
    output = Path(output)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("H5_SOURCE_INVALID: provide a real static directory")
    source = source.resolve(strict=True)
    output_absolute = output.resolve(strict=False)
    if output.is_symlink():
        raise ValueError("H5_OUTPUT_SYMLINK_NOT_ALLOWED: choose a regular output path")
    if output_absolute == source or source in output_absolute.parents:
        raise ValueError("H5_OUTPUT_INSIDE_SOURCE: write the ZIP outside the static directory")
    if output.exists() and not overwrite:
        raise ValueError("H5_OUTPUT_EXISTS: choose another output or pass --overwrite")

    entries: list[Path] = []
    expanded_size = 0
    for root, directories, filenames in os.walk(source, followlinks=False):
        current = Path(root)
        for name in list(directories):
            child = current / name
            if child.is_symlink():
                raise ValueError("H5_SYMLINK_NOT_ALLOWED: static packages cannot contain symlinks")
        for name in filenames:
            child = current / name
            if child.is_symlink() or not child.is_file():
                raise ValueError("H5_SYMLINK_NOT_ALLOWED: static packages cannot contain symlinks")
            entries.append(child)
            expanded_size += child.stat().st_size
            if len(entries) > MAX_FILES:
                raise ValueError("H5_FILE_COUNT_LIMIT: package exceeds 2000 files")
            if expanded_size > MAX_EXPANDED_BYTES:
                raise ValueError("H5_EXPANDED_SIZE_LIMIT: package exceeds 200 MiB")
    names = {path.relative_to(source).as_posix() for path in entries}
    if "index.html" not in names and "dist/index.html" not in names:
        raise ValueError("H5_INDEX_REQUIRED: package needs index.html or dist/index.html")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(entries):
                archive.write(path, path.relative_to(source).as_posix())
        archive_size = temporary.stat().st_size
        if archive_size > MAX_ARCHIVE_BYTES:
            raise ValueError("H5_ARCHIVE_SIZE_LIMIT: ZIP exceeds 50 MiB")
        if output.exists() and not overwrite:
            raise ValueError("H5_OUTPUT_EXISTS: choose another output or pass --overwrite")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"output": str(output), "file_count": len(entries), "expanded_bytes": expanded_size, "archive_bytes": archive_size}
