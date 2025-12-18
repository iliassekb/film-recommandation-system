#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bootstrap MovieLens 25M dataset to Bronze layer.
Downloads and extracts the dataset to lakehouse/bronze/movielens/ml-25m/
"""

import os
import sys
import json
import zipfile
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from urllib.request import urlretrieve
from urllib.error import URLError

# Fix encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-25m.zip"
DATASET_NAME = "movielens"
DATASET_VERSION = "ml-25m"
BRONZE_BASE_DIR = Path("lakehouse/bronze")
DATASET_DIR = BRONZE_BASE_DIR / DATASET_NAME / DATASET_VERSION
ZIP_FILE = DATASET_DIR / "ml-25m.zip"
MANIFEST_FILE = DATASET_DIR / "_manifest.json"

# Colors for output (Windows compatible)
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_colored(text, color):
    """Print colored text (works on Windows 10+ with ANSI support)."""
    try:
        # Enable ANSI colors on Windows
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                pass
        print(f"{color}{text}{Colors.RESET}")
    except Exception:
        # Fallback to plain text if colors fail
        print(text)

def count_csv_rows_lightweight(file_path):
    """Count rows in CSV file without loading entire file into memory."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first line to verify it's a CSV
            first_line = f.readline()
            if not first_line:
                return 0
            # Count remaining lines
            row_count = sum(1 for _ in f)
            return row_count  # Header already consumed
    except Exception as e:
        print(f"  ERROR: Could not read {file_path.name}: {e}", file=sys.stderr)
        return -1

def get_file_size(file_path):
    """Get file size in bytes."""
    try:
        return file_path.stat().st_size
    except Exception:
        return 0

def calculate_md5(file_path):
    """Calculate MD5 checksum of a file."""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

def download_file(url, dest_path, force=False):
    """Download a file from URL to destination path."""
    if dest_path.exists() and not force:
        print_colored("Zip file already exists, skipping download", Colors.YELLOW)
        return True
    
    print("")
    print("Downloading MovieLens 25M dataset...")
    print(f"URL: {url}")
    print("This may take a few minutes (~250 MB)...")
    
    try:
        def reporthook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            sys.stdout.write(f"\rProgress: {percent}%")
            sys.stdout.flush()
        
        urlretrieve(url, dest_path, reporthook)
        print("")  # New line after progress
        print_colored("[OK] Download complete", Colors.GREEN)
        return True
    except URLError as e:
        print_colored(f"Error: Download failed - {e}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"Error: Download failed - {e}", Colors.RED)
        return False

def extract_zip(zip_path, extract_to):
    """Extract ZIP file to destination directory."""
    print("")
    print("Extracting dataset...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to temporary directory first
            import tempfile
            temp_dir = Path(tempfile.mkdtemp(prefix="movielens_extract_"))
            
            zip_ref.extractall(temp_dir)
            
            # The zip typically contains a ml-25m/ folder
            extracted_dir = temp_dir / "ml-25m"
            if extracted_dir.exists():
                # Move contents of ml-25m/ to dataset directory
                for item in extracted_dir.iterdir():
                    dest = extract_to / item.name
                    if item.is_dir():
                        import shutil
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        import shutil
                        shutil.copy2(item, dest)
            else:
                # If structure is different, move all files
                for item in temp_dir.iterdir():
                    if item.is_file():
                        import shutil
                        shutil.copy2(item, extract_to / item.name)
            
            # Cleanup temp directory
            import shutil
            shutil.rmtree(temp_dir)
            
            print_colored("[OK] Extraction complete", Colors.GREEN)
            return True
    except Exception as e:
        print_colored(f"Error: Extraction failed - {e}", Colors.RED)
        return False

def generate_manifest():
    """Generate manifest file with dataset metadata."""
    print("")
    print("Generating manifest file...")
    
    ingestion_ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    ingestion_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    files_array = []
    csv_files = list(DATASET_DIR.glob("*.csv"))
    
    for csv_file in csv_files:
        file_info = {
            "filename": csv_file.name,
            "size_bytes": get_file_size(csv_file),
            "row_count": count_csv_rows_lightweight(csv_file),
            "checksum_md5": calculate_md5(csv_file)
        }
        files_array.append(file_info)
    
    manifest = {
        "dataset_name": DATASET_NAME,
        "dataset_version": DATASET_VERSION,
        "source_url": DATASET_URL,
        "ingestion_ts": ingestion_ts,
        "ingestion_date": ingestion_date,
        "files": files_array
    }
    
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print_colored(f"[OK] Manifest file created: {MANIFEST_FILE}", Colors.GREEN)
    return True

def format_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Bootstrap MovieLens 25M dataset to Bronze layer')
    parser.add_argument('--force', action='store_true', help='Force re-download and extraction')
    args = parser.parse_args()
    
    print("=" * 60)
    print_colored("MovieLens 25M Bootstrap Script", Colors.CYAN)
    print("=" * 60)
    print("")
    
    # Check if dataset already exists
    if DATASET_DIR.exists() and MANIFEST_FILE.exists() and not args.force:
        print_colored(f"Dataset already exists at: {DATASET_DIR}", Colors.YELLOW)
        print("Use --force to re-download and extract.")
        print("")
        print("To validate the dataset, run:")
        print("  python scripts/validate_bronze_presence.py")
        return 0
    
    # Create directory structure
    print("Creating directory structure...")
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    print_colored(f"[OK] Directory created: {DATASET_DIR}", Colors.GREEN)
    
    # Download dataset
    if not download_file(DATASET_URL, ZIP_FILE, force=args.force):
        return 1
    
    # Extract dataset
    if not ZIP_FILE.exists():
        print_colored(f"Error: Zip file not found: {ZIP_FILE}", Colors.RED)
        return 1
    
    if not extract_zip(ZIP_FILE, DATASET_DIR):
        return 1
    
    # Generate manifest
    if not generate_manifest():
        return 1
    
    # Summary
    print("")
    print("=" * 60)
    print_colored("[OK] Bootstrap Complete!", Colors.GREEN)
    print("=" * 60)
    print("")
    print(f"Dataset location: {DATASET_DIR}")
    print(f"Manifest file: {MANIFEST_FILE}")
    print("")
    print("Files extracted:")
    
    csv_files = list(DATASET_DIR.glob("*.csv"))
    for csv_file in csv_files:
        size_bytes = get_file_size(csv_file)
        size_str = format_size(size_bytes)
        print(f"  - {csv_file.name} ({size_str})")
    
    print("")
    print("Next steps:")
    print("  1. Validate the dataset:")
    print("     python scripts/validate_bronze_presence.py")
    print("")
    print("  2. Verify files are accessible from containers:")
    print("     docker-compose exec spark-master ls -lh /lakehouse/bronze/movielens/ml-25m/")
    print("")
    print("  3. Proceed to Step 3: Implement ETL to Silver layer")
    print("")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

