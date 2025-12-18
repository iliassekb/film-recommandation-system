#!/usr/bin/env python3
"""
Validate Bronze layer presence for MovieLens 25M dataset.

This script verifies that:
1. Required files exist in the Bronze directory
2. Files are readable
3. Quick row count estimation (without loading entire CSV)
4. Manifest file is present and valid

Exit code: 0 if validation passes, non-zero if validation fails.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
BRONZE_BASE_DIR = Path("lakehouse/bronze")
DATASET_NAME = "movielens"
DATASET_VERSION = "ml-25m"
DATASET_DIR = BRONZE_BASE_DIR / DATASET_NAME / DATASET_VERSION
MANIFEST_FILE = DATASET_DIR / "_manifest.json"

# Required files (minimum set)
REQUIRED_FILES = [
    "ratings.csv",
    "movies.csv",
    "tags.csv",
    "links.csv"
]

# Optional files
OPTIONAL_FILES = [
    "genome-scores.csv",
    "genome-tags.csv"
]


def count_csv_rows_lightweight(file_path: Path) -> int:
    """
    Count rows in CSV file without loading entire file into memory.
    Uses line counting (subtracts header).
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first line to verify it's a CSV
            first_line = f.readline()
            if not first_line:
                return 0
            
            # Count remaining lines
            row_count = sum(1 for _ in f)
            return row_count  # Header already consumed, so this is data rows
    except Exception as e:
        print(f"  ERROR: Could not read {file_path.name}: {e}", file=sys.stderr)
        return -1


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    try:
        return file_path.stat().st_size
    except Exception:
        return 0


def validate_manifest():
    """Validate manifest file exists and is valid JSON."""
    if not MANIFEST_FILE.exists():
        return False, None
    
    try:
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Basic validation
        required_keys = ["dataset_name", "dataset_version", "source_url", 
                        "ingestion_ts", "ingestion_date", "files"]
        for key in required_keys:
            if key not in manifest:
                print(f"  ERROR: Manifest missing required key: {key}", file=sys.stderr)
                return False, None
        
        return True, manifest
    except json.JSONDecodeError as e:
        print(f"  ERROR: Manifest file is not valid JSON: {e}", file=sys.stderr)
        return False, None
    except Exception as e:
        print(f"  ERROR: Could not read manifest: {e}", file=sys.stderr)
        return False, None


def validate_files():
    """Validate that required files exist and are readable."""
    errors = []
    all_files_present = True
    
    print("\nValidating required files:")
    for filename in REQUIRED_FILES:
        file_path = DATASET_DIR / filename
        if not file_path.exists():
            print(f"  ✗ {filename} - MISSING", file=sys.stderr)
            errors.append(f"Required file missing: {filename}")
            all_files_present = False
        elif not file_path.is_file():
            print(f"  ✗ {filename} - Not a file", file=sys.stderr)
            errors.append(f"Not a file: {filename}")
            all_files_present = False
        else:
            size = get_file_size(file_path)
            size_mb = size / (1024 * 1024)
            print(f"  ✓ {filename} - {size_mb:.2f} MB")
    
    print("\nChecking optional files:")
    for filename in OPTIONAL_FILES:
        file_path = DATASET_DIR / filename
        if file_path.exists():
            size = get_file_size(file_path)
            size_mb = size / (1024 * 1024)
            print(f"  ✓ {filename} - {size_mb:.2f} MB")
        else:
            print(f"  - {filename} - Not present (optional)")
    
    return all_files_present, errors


def validate_row_counts():
    """Quick validation of row counts (lightweight method)."""
    errors = []
    all_valid = True
    
    print("\nEstimating row counts (lightweight method):")
    
    # Expected minimum row counts (approximate)
    expected_minimums = {
        "ratings.csv": 20_000_000,  # ~25M ratings
        "movies.csv": 60_000,        # ~62K movies
        "tags.csv": 1_000_000,       # ~1M tags
        "links.csv": 60_000          # ~62K links
    }
    
    for filename in REQUIRED_FILES:
        file_path = DATASET_DIR / filename
        if not file_path.exists():
            continue
        
        row_count = count_csv_rows_lightweight(file_path)
        if row_count < 0:
            errors.append(f"Could not count rows in {filename}")
            all_valid = False
        else:
            expected_min = expected_minimums.get(filename, 0)
            status = "✓" if row_count >= expected_min * 0.8 else "⚠"
            print(f"  {status} {filename}: {row_count:,} rows (expected ~{expected_min:,})")
            
            if row_count < expected_min * 0.5:  # Allow 50% tolerance
                errors.append(f"Suspiciously low row count in {filename}: {row_count}")
                all_valid = False
    
    return all_valid, errors


def main():
    """Main validation function."""
    print("=" * 60)
    print("Bronze Layer Validation - MovieLens 25M")
    print("=" * 60)
    print(f"\nDataset directory: {DATASET_DIR}")
    
    # Check if dataset directory exists
    if not DATASET_DIR.exists():
        print(f"\n✗ ERROR: Dataset directory does not exist: {DATASET_DIR}", file=sys.stderr)
        print("\nPlease run the bootstrap script first:", file=sys.stderr)
        print("  All platforms: python scripts/bootstrap_bronze_movielens_25m.py", file=sys.stderr)
        print("  Or use Makefile: make bootstrap_bronze", file=sys.stderr)
        print("  Linux/Mac (alternative): ./scripts/bootstrap_bronze_movielens_25m.sh", file=sys.stderr)
        sys.exit(1)
    
    if not DATASET_DIR.is_dir():
        print(f"\n✗ ERROR: Dataset path is not a directory: {DATASET_DIR}", file=sys.stderr)
        sys.exit(1)
    
    all_checks_passed = True
    all_errors = []
    
    # Validate manifest
    print("\nValidating manifest file:")
    manifest_valid, manifest = validate_manifest()
    if manifest_valid:
        print(f"  ✓ Manifest file found and valid")
        print(f"    Dataset: {manifest['dataset_name']} v{manifest['dataset_version']}")
        print(f"    Ingestion date: {manifest['ingestion_date']}")
        print(f"    Files in manifest: {len(manifest.get('files', []))}")
    else:
        print(f"  ✗ Manifest file missing or invalid", file=sys.stderr)
        all_checks_passed = False
        all_errors.append("Manifest file validation failed")
    
    # Validate files
    files_valid, file_errors = validate_files()
    if not files_valid:
        all_checks_passed = False
        all_errors.extend(file_errors)
    
    # Validate row counts
    rows_valid, row_errors = validate_row_counts()
    if not rows_valid:
        all_checks_passed = False
        all_errors.extend(row_errors)
    
    # Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✓ VALIDATION PASSED")
        print("=" * 60)
        print("\nBronze layer is ready for Step 3 (ETL to Silver).")
        sys.exit(0)
    else:
        print("✗ VALIDATION FAILED")
        print("=" * 60)
        print("\nErrors found:")
        for error in all_errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nPlease fix the issues above and re-run validation.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

