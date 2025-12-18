"""
I/O utilities - Helper functions to read/write Delta/Parquet with Spark.
"""

from typing import Optional, List
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType
from .config import Config


def read_table(
    spark: SparkSession,
    path: str,
    format: Optional[str] = None,
    schema: Optional[StructType] = None
) -> DataFrame:
    """
    Read a table from lakehouse (Delta or Parquet).
    
    Args:
        spark: SparkSession
        path: Path to the table
        format: Storage format ('delta' or 'parquet'). If None, uses Config.STORAGE_FORMAT
        schema: Optional schema (for Parquet/CSV)
    
    Returns:
        DataFrame
    """
    storage_format = format or Config.STORAGE_FORMAT
    
    if storage_format == "delta":
        return spark.read.format("delta").load(path)
    elif storage_format == "parquet":
        reader = spark.read.format("parquet")
        if schema:
            reader = reader.schema(schema)
        return reader.load(path)
    else:
        raise ValueError(f"Unsupported storage format: {storage_format}")


def write_table(
    df: DataFrame,
    path: str,
    format: Optional[str] = None,
    mode: str = "overwrite",
    partition_by: Optional[List[str]] = None
) -> None:
    """
    Write a DataFrame to lakehouse (Delta or Parquet).
    
    Args:
        df: DataFrame to write
        path: Output path
        format: Storage format ('delta' or 'parquet'). If None, uses Config.STORAGE_FORMAT
        mode: Write mode ('overwrite', 'append', 'error', 'ignore')
        partition_by: List of column names to partition by
    """
    from datetime import datetime
    import time
    
    storage_format = format or Config.STORAGE_FORMAT
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] Preparing write operation...")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   Path: {path}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   Format: {storage_format}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   Mode: {mode}")
    if partition_by:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   Partitions: {', '.join(partition_by)}")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   Partitions: None")
    
    # Show DataFrame schema info
    num_partitions = df.rdd.getNumPartitions()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   DataFrame partitions: {num_partitions}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO]   DataFrame columns: {len(df.columns)}")
    
    write_start = time.time()
    writer = df.write.format(storage_format).mode(mode)
    
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] Starting write operation (this may take a while for large datasets)...")
    writer.save(path)
    write_elapsed = time.time() - write_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] Write operation completed in {write_elapsed:.2f}s")


def read_csv_with_schema(
    spark: SparkSession,
    path: str,
    schema: StructType,
    header: bool = True,
    delimiter: str = ","
) -> DataFrame:
    """
    Read CSV file with explicit schema.
    
    Args:
        spark: SparkSession
        path: Path to CSV file
        schema: Explicit schema
        header: Whether CSV has header row
        delimiter: CSV delimiter
    
    Returns:
        DataFrame
    """
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] Reading CSV: {path}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] Schema: {len(schema.fields)} fields, Header: {header}, Delimiter: '{delimiter}'")
    df = spark.read \
        .option("header", str(header).lower()) \
        .option("delimiter", delimiter) \
        .schema(schema) \
        .csv(path)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IO] CSV read initiated (lazy evaluation)")
    return df


def table_exists(spark: SparkSession, path: str, format: Optional[str] = None) -> bool:
    """
    Check if a table exists at the given path.
    
    Args:
        spark: SparkSession
        path: Path to check
        format: Storage format. If None, uses Config.STORAGE_FORMAT
    
    Returns:
        True if table exists, False otherwise
    """
    storage_format = format or Config.STORAGE_FORMAT
    
    try:
        if storage_format == "delta":
            # Delta tables can be checked via DeltaTable
            from delta.tables import DeltaTable
            delta_table = DeltaTable.forPath(spark, path)
            return True
        else:
            # For Parquet, check if path exists and has data
            from pyspark.sql import DataFrame
            df = spark.read.format("parquet").load(path)
            # Try to get one row to verify it's readable
            df.limit(1).collect()
            return True
    except Exception:
        return False


