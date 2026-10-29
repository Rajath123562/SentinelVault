"""Packages the complete HOTFIX project for hackathon submission into a clean, optimized ZIP archive.

Excludes:
- node_modules/
- __pycache__/ and *.pyc
- .pytest_cache/
- .git/
- temporary build files

Includes:
- Complete backend codebase (Python, FastAPI, schemas, services, tests, database)
- Complete frontend codebase (React 19, TypeScript, components, tests, configuration)
- /screenshots folder with live browser captures, terminal output, and ASCII wireframes
- Complete documentation (README.md, docs/ architecture, RTM matrix, benchmark reports)
- Automation scripts (PowerShell startup, verification scripts)
- Configuration files (config/app.yaml, spec.yaml)
"""

import os
import sys
import zipfile
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
output_zip_path = repo_root / "SentinelVault_UG59_Hackathon_Submission.zip"

EXCLUDE_DIRS = {
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".zip",
    ".db-shm",
    ".db-wal",
}

def should_exclude(rel_path_parts):
    for part in rel_path_parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith(".git"):
            return True
        if "test_isolated" in part:
            return True
    return False

def package_project():
    print(f"Creating optimized hackathon submission ZIP: {output_zip_path.name}...")
    
    # Remove existing zip if present
    if output_zip_path.exists():
        output_zip_path.unlink()

    included_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(repo_root):
            rel_root = Path(root).relative_to(repo_root)
            parts = rel_root.parts

            if should_exclude(parts):
                continue

            # Filter dirs in-place to prevent walking into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".git")]

            for file in files:
                file_path = Path(root) / file
                rel_file_path = rel_root / file

                # Do not zip the output archive itself or temporary files
                if file_path == output_zip_path:
                    continue
                if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
                    continue
                if should_exclude(rel_file_path.parts):
                    continue

                zipf.write(file_path, arcname=str(rel_file_path))
                included_count += 1
                total_uncompressed_bytes += file_path.stat().st_size

    compressed_size = output_zip_path.stat().st_size
    ratio = (1.0 - (compressed_size / total_uncompressed_bytes)) * 100 if total_uncompressed_bytes > 0 else 0

    print("=" * 60)
    print("SUBMISSION ARCHIVE CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Output File:         {output_zip_path}")
    print(f"Files Packaged:      {included_count} files")
    print(f"Uncompressed Size:   {total_uncompressed_bytes / (1024*1024):.2f} MB")
    print(f"Compressed Size:     {compressed_size / (1024*1024):.2f} MB")
    print(f"Compression Ratio:   {ratio:.1f}% space saved")
    print("=" * 60)

    # Verify screenshots are in the archive
    with zipfile.ZipFile(output_zip_path, "r") as zipf:
        names = zipf.namelist()
        screenshots = [n for n in names if n.startswith("screenshots/")]
        print(f"Screenshots in ZIP:  {len(screenshots)} items")
        for s in screenshots:
            print(f"  [x] {s}")

    return output_zip_path

if __name__ == "__main__":
    package_project()
