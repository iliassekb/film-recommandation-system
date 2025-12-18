"""
Data quality utilities - Helper functions for validation and reporting.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, when, isnan, isnull
from .config import Config
from .paths import get_reports_path, ensure_directory_exists


class QualityReport:
    """Data quality report generator."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.checks: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_check(self, check_name: str, passed: bool, details: Optional[Dict] = None):
        """Add a quality check result."""
        self.checks.append({
            "check_name": check_name,
            "passed": passed,
            "details": details or {}
        })
        if not passed:
            self.errors.append(f"{check_name}: {details}")
    
    def add_warning(self, message: str):
        """Add a warning."""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "table_name": self.table_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": {
                "total_checks": len(self.checks),
                "passed_checks": sum(1 for c in self.checks if c["passed"]),
                "failed_checks": sum(1 for c in self.checks if not c["passed"]),
                "has_errors": len(self.errors) > 0,
                "has_warnings": len(self.warnings) > 0
            }
        }
    
    def save(self, spark: SparkSession, layer: str = "silver") -> str:
        """Save report to JSON file."""
        reports_dir = get_reports_path(layer)
        ensure_directory_exists(reports_dir)
        
        report_path = f"{reports_dir}/quality_{self.table_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_dict = self.to_dict()
        
        # Write JSON (using Spark to write to distributed storage if needed)
        # For simplicity, we'll use Python's json module
        import os
        os.makedirs(reports_dir, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        return report_path


def check_null_percentage(
    df: DataFrame,
    columns: List[str],
    max_percentage: Optional[float] = None
) -> Dict[str, float]:
    """
    Check null percentage for specified columns.
    
    Args:
        df: DataFrame to check
        columns: List of column names to check
        max_percentage: Maximum allowed null percentage (from Config if None)
    
    Returns:
        Dictionary mapping column names to null percentages
    """
    max_pct = max_percentage or Config.MAX_NULL_PERCENTAGE
    total_rows = df.count()
    
    null_percentages = {}
    for col_name in columns:
        null_count = df.filter(col(col_name).isNull()).count()
        null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0.0
        null_percentages[col_name] = null_pct
    
    return null_percentages


def check_value_range(
    df: DataFrame,
    column: str,
    min_value: float,
    max_value: float
) -> Dict[str, Any]:
    """
    Check if values in a column are within specified range.
    
    Args:
        df: DataFrame to check
        column: Column name to check
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Dictionary with validation results
    """
    total_rows = df.count()
    out_of_range = df.filter(
        (col(column) < min_value) | (col(column) > max_value)
    ).count()
    
    return {
        "column": column,
        "min_value": min_value,
        "max_value": max_value,
        "total_rows": total_rows,
        "out_of_range_count": out_of_range,
        "out_of_range_percentage": (out_of_range / total_rows * 100) if total_rows > 0 else 0.0,
        "passed": out_of_range == 0
    }


def get_row_count(df: DataFrame) -> int:
    """Get row count of DataFrame."""
    return df.count()


def check_duplicates(
    df: DataFrame,
    key_columns: List[str]
) -> Dict[str, Any]:
    """
    Check for duplicate rows based on key columns.
    
    Args:
        df: DataFrame to check
        key_columns: List of column names that form the key
    
    Returns:
        Dictionary with duplicate check results
    """
    total_rows = df.count()
    distinct_rows = df.select(*key_columns).distinct().count()
    duplicates = total_rows - distinct_rows
    
    return {
        "key_columns": key_columns,
        "total_rows": total_rows,
        "distinct_keys": distinct_rows,
        "duplicate_count": duplicates,
        "duplicate_percentage": (duplicates / total_rows * 100) if total_rows > 0 else 0.0,
        "passed": duplicates == 0
    }


def validate_ratings(df: DataFrame, report: QualityReport) -> None:
    """Validate ratings DataFrame."""
    # Check nulls in required columns
    required_cols = ["user_id", "movie_id", "rating", "rating_ts"]
    null_pcts = check_null_percentage(df, required_cols)
    
    for col_name, pct in null_pcts.items():
        passed = pct == 0.0
        report.add_check(
            f"null_check_{col_name}",
            passed,
            {"null_percentage": pct, "max_allowed": 0.0}
        )
    
    # Check rating range
    range_check = check_value_range(df, "rating", Config.MIN_RATING, Config.MAX_RATING)
    report.add_check(
        "rating_range_check",
        range_check["passed"],
        range_check
    )
    
    # Check duplicates
    dup_check = check_duplicates(df, ["user_id", "movie_id", "rating_ts"])
    report.add_check(
        "duplicate_check",
        dup_check["passed"],
        dup_check
    )
    
    # Row count
    row_count = get_row_count(df)
    report.add_check(
        "row_count_check",
        row_count > 0,
        {"row_count": row_count}
    )


def validate_movies(df: DataFrame, report: QualityReport) -> None:
    """Validate movies DataFrame."""
    # Check nulls
    required_cols = ["movie_id", "title"]
    null_pcts = check_null_percentage(df, required_cols)
    
    for col_name, pct in null_pcts.items():
        passed = pct == 0.0
        report.add_check(
            f"null_check_{col_name}",
            passed,
            {"null_percentage": pct, "max_allowed": 0.0}
        )
    
    # Check duplicates on movie_id
    dup_check = check_duplicates(df, ["movie_id"])
    report.add_check(
        "duplicate_movie_id_check",
        dup_check["passed"],
        dup_check
    )
    
    # Row count
    row_count = get_row_count(df)
    report.add_check(
        "row_count_check",
        row_count > 0,
        {"row_count": row_count}
    )


def validate_tags(df: DataFrame, report: QualityReport) -> None:
    """Validate tags DataFrame."""
    # Check nulls
    required_cols = ["user_id", "movie_id", "tag", "tag_ts"]
    null_pcts = check_null_percentage(df, required_cols)
    
    for col_name, pct in null_pcts.items():
        passed = pct == 0.0
        report.add_check(
            f"null_check_{col_name}",
            passed,
            {"null_percentage": pct, "max_allowed": 0.0}
        )
    
    # Row count
    row_count = get_row_count(df)
    report.add_check(
        "row_count_check",
        row_count > 0,
        {"row_count": row_count}
    )







