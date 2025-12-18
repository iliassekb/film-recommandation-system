#!/bin/bash
# Bootstrap MovieLens 25M dataset to Bronze layer
# Downloads and extracts the dataset to lakehouse/bronze/movielens/ml-25m/

set -e  # Exit on error

# Configuration
DATASET_URL="https://files.grouplens.org/datasets/movielens/ml-25m.zip"
DATASET_NAME="movielens"
DATASET_VERSION="ml-25m"
BRONZE_BASE_DIR="lakehouse/bronze"
DATASET_DIR="${BRONZE_BASE_DIR}/${DATASET_NAME}/${DATASET_VERSION}"
ZIP_FILE="${DATASET_DIR}/ml-25m.zip"
MANIFEST_FILE="${DATASET_DIR}/_manifest.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
FORCE=false
if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

echo "=========================================="
echo "MovieLens 25M Bootstrap Script"
echo "=========================================="
echo ""

# Check if dataset already exists
if [ -d "$DATASET_DIR" ] && [ -f "$MANIFEST_FILE" ] && [ "$FORCE" = false ]; then
    echo -e "${YELLOW}Dataset already exists at: ${DATASET_DIR}${NC}"
    echo "Use --force to re-download and extract."
    echo ""
    echo "To validate the dataset, run:"
    echo "  python scripts/validate_bronze_presence.py"
    exit 0
fi

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$DATASET_DIR"
echo -e "${GREEN}✓${NC} Directory created: $DATASET_DIR"

# Download dataset
if [ "$FORCE" = true ] || [ ! -f "$ZIP_FILE" ]; then
    echo ""
    echo "Downloading MovieLens 25M dataset..."
    echo "URL: $DATASET_URL"
    echo "This may take a few minutes (~250 MB)..."
    
    if command -v curl &> /dev/null; then
        curl -L -o "$ZIP_FILE" "$DATASET_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$ZIP_FILE" "$DATASET_URL"
    else
        echo -e "${RED}Error: Neither curl nor wget found. Please install one of them.${NC}"
        exit 1
    fi
    
    if [ ! -f "$ZIP_FILE" ]; then
        echo -e "${RED}Error: Download failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Download complete"
else
    echo -e "${YELLOW}Zip file already exists, skipping download${NC}"
fi

# Extract dataset
echo ""
echo "Extracting dataset..."
if [ -f "$ZIP_FILE" ]; then
    # Extract to temporary directory first, then move files
    TEMP_DIR=$(mktemp -d)
    unzip -q "$ZIP_FILE" -d "$TEMP_DIR"
    
    # Move extracted files to dataset directory
    # The zip contains a ml-25m/ folder, so we need to move its contents
    if [ -d "$TEMP_DIR/ml-25m" ]; then
        mv "$TEMP_DIR/ml-25m"/* "$DATASET_DIR/"
        rm -rf "$TEMP_DIR"
    else
        # If structure is different, move all files
        mv "$TEMP_DIR"/* "$DATASET_DIR/" 2>/dev/null || true
        rm -rf "$TEMP_DIR"
    fi
    
    echo -e "${GREEN}✓${NC} Extraction complete"
else
    echo -e "${RED}Error: Zip file not found${NC}"
    exit 1
fi

# Generate manifest file
echo ""
echo "Generating manifest file..."

INGESTION_TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
INGESTION_DATE=$(date -u +"%Y-%m-%d")

# Count rows in CSV files (quick method - count lines minus header)
count_rows() {
    local file="$1"
    if [ -f "$file" ]; then
        # Count lines minus header (assumes header exists)
        local lines=$(wc -l < "$file" 2>/dev/null || echo "0")
        if [ "$lines" -gt 0 ]; then
            echo $((lines - 1))
        else
            echo "0"
        fi
    else
        echo "0"
    fi
}

# Get file size
get_file_size() {
    local file="$1"
    if [ -f "$file" ]; then
        stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Calculate MD5 checksum if available
get_checksum() {
    local file="$1"
    if command -v md5sum &> /dev/null; then
        md5sum "$file" | cut -d' ' -f1
    elif command -v md5 &> /dev/null; then
        md5 -q "$file"
    else
        echo ""
    fi
}

# Build files array
FILES_JSON=""
for csv_file in "$DATASET_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        filename=$(basename "$csv_file")
        size=$(get_file_size "$csv_file")
        row_count=$(count_rows "$csv_file")
        checksum=$(get_checksum "$csv_file")
        
        if [ -n "$FILES_JSON" ]; then
            FILES_JSON="$FILES_JSON,"
        fi
        
        FILES_JSON="$FILES_JSON
    {
      \"filename\": \"$filename\",
      \"size_bytes\": $size,
      \"row_count\": $row_count,
      \"checksum_md5\": \"$checksum\"
    }"
    fi
done

# Write manifest
cat > "$MANIFEST_FILE" << EOF
{
  "dataset_name": "$DATASET_NAME",
  "dataset_version": "$DATASET_VERSION",
  "source_url": "$DATASET_URL",
  "ingestion_ts": "$INGESTION_TS",
  "ingestion_date": "$INGESTION_DATE",
  "files": [$FILES_JSON
  ]
}
EOF

echo -e "${GREEN}✓${NC} Manifest file created: $MANIFEST_FILE"

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✓ Bootstrap Complete!${NC}"
echo "=========================================="
echo ""
echo "Dataset location: $DATASET_DIR"
echo "Manifest file: $MANIFEST_FILE"
echo ""
echo "Files extracted:"
for csv_file in "$DATASET_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        filename=$(basename "$csv_file")
        size=$(get_file_size "$csv_file")
        size_mb=$(awk "BEGIN {printf \"%.2f\", $size / 1024 / 1024}")
        echo "  - $filename ($size_mb MB)"
    fi
done
echo ""
echo "Next steps:"
echo "  1. Validate the dataset:"
echo "     python scripts/validate_bronze_presence.py"
echo ""
echo "  2. Verify files are accessible from containers:"
echo "     docker-compose exec spark-master ls -lh /lakehouse/bronze/movielens/ml-25m/"
echo ""
echo "  3. Proceed to Step 3: Implement ETL to Silver layer"
echo ""

