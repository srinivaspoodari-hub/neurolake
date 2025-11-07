"""
NeuroLake File Handler
Handles various file formats with intelligent parsing
"""

import pandas as pd
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json


class FileHandler:
    """Intelligent file handling with format detection"""

    SUPPORTED_FORMATS = {
        '.csv': 'csv',
        '.json': 'json',
        '.jsonl': 'jsonlines',
        '.parquet': 'parquet',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.tsv': 'tsv',
        '.txt': 'text'
    }

    def __init__(self):
        """Initialize file handler"""
        self.files_processed = 0

    def read_file(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Read file with automatic format detection

        Args:
            file_path: Path to file
            **kwargs: Additional parameters for pandas readers

        Returns:
            DataFrame
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect format
        file_format = self._detect_format(path)

        # Read based on format
        if file_format == 'csv':
            df = pd.read_csv(file_path, **kwargs)
        elif file_format == 'tsv':
            df = pd.read_csv(file_path, sep='\t', **kwargs)
        elif file_format == 'json':
            df = pd.read_json(file_path, **kwargs)
        elif file_format == 'jsonlines':
            df = pd.read_json(file_path, lines=True, **kwargs)
        elif file_format == 'parquet':
            df = pd.read_parquet(file_path, **kwargs)
        elif file_format == 'excel':
            df = pd.read_excel(file_path, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        self.files_processed += 1
        return df

    def write_file(self,
                   df: pd.DataFrame,
                   file_path: str,
                   format: Optional[str] = None,
                   **kwargs) -> str:
        """
        Write DataFrame to file

        Args:
            df: DataFrame to write
            file_path: Output path
            format: Format override (optional)
            **kwargs: Additional parameters

        Returns:
            Path to written file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine format
        if format:
            file_format = format
        else:
            file_format = self._detect_format(path)

        # Write based on format
        if file_format == 'csv':
            df.to_csv(file_path, index=False, **kwargs)
        elif file_format == 'json':
            df.to_json(file_path, orient='records', **kwargs)
        elif file_format == 'parquet':
            df.to_parquet(file_path, index=False, **kwargs)
        elif file_format == 'excel':
            df.to_excel(file_path, index=False, **kwargs)
        else:
            raise ValueError(f"Unsupported output format: {file_format}")

        return str(path)

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension"""
        suffix = path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix, 'unknown')

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return {
            'name': path.name,
            'size_bytes': path.stat().st_size,
            'size_mb': path.stat().st_size / (1024 * 1024),
            'format': self._detect_format(path),
            'extension': path.suffix,
            'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        }