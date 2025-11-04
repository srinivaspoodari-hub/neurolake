"""
File Upload Handler for Migration Module
Supports all ETL tools, SQL procedures, and mainframe code
"""

import os
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from .config import SUPPORTED_PLATFORMS, UPLOAD_DIR, MIGRATION_SETTINGS


class UploadHandler:
    """Handles file uploads for migration"""

    def __init__(self):
        self.upload_dir = UPLOAD_DIR
        self.max_size = MIGRATION_SETTINGS['max_file_size_mb'] * 1024 * 1024

    def detect_platform(self, filename: str, content: str) -> Optional[str]:
        """
        Detect the source platform from file extension and content
        """
        ext = Path(filename).suffix.lower()

        # Check each platform
        for platform, config in SUPPORTED_PLATFORMS.items():
            if ext in config['extensions']:
                # Additional content validation
                if self._validate_content(platform, content):
                    return platform

        # Content-based detection if extension doesn't match
        return self._detect_from_content(content)

    def _validate_content(self, platform: str, content: str) -> bool:
        """Validate content matches platform"""
        validators = {
            'sql': lambda c: any(kw in c.upper() for kw in ['SELECT', 'CREATE', 'PROCEDURE', 'FUNCTION']),
            'talend': lambda c: '<talend' in c.lower() or 'talend.component' in c.lower(),
            'datastage': lambda c: '<DSExport' in c or 'DataStage' in c,
            'informatica': lambda c: '<PowerMart' in c or '<REPOSITORY' in c,
            'mainframe': lambda c: 'IDENTIFICATION DIVISION' in c or '//JOB' in c or '//EXEC PGM=' in c,
            'ssis': lambda c: '<DTS:Executable' in c or 'Microsoft.SqlServer.Dts' in c,
            'abinitio': lambda c: '.component' in c or 'abinitio' in c.lower(),
            'pentaho': lambda c: '<transformation>' in c or '<job>' in c,
            'obiee': lambda c: '<Repository' in c or 'BusinessModel' in c
        }

        validator = validators.get(platform)
        return validator(content) if validator else True

    def _detect_from_content(self, content: str) -> Optional[str]:
        """Detect platform from content patterns"""
        content_upper = content.upper()
        content_lower = content.lower()

        # SQL patterns
        if any(kw in content_upper for kw in ['CREATE PROCEDURE', 'CREATE FUNCTION', 'BEGIN', 'DECLARE']):
            return 'sql'

        # Mainframe patterns
        if 'IDENTIFICATION DIVISION' in content or '//JOB' in content or 'EXEC PGM=' in content:
            return 'mainframe'

        # XML-based ETL tools
        if '<talend' in content_lower:
            return 'talend'
        if 'datastage' in content_lower or '<DSExport' in content:
            return 'datastage'
        if '<PowerMart' in content or 'informatica' in content_lower:
            return 'informatica'
        if '<DTS:' in content or 'SqlServer.Dts' in content:
            return 'ssis'
        if '<transformation>' in content_lower or 'pentaho' in content_lower:
            return 'pentaho'

        return None

    def validate_file(self, filename: str, content: bytes) -> Tuple[bool, str]:
        """
        Validate uploaded file
        Returns: (is_valid, message)
        """
        # Check file size
        if len(content) > self.max_size:
            return False, f"File size exceeds maximum of {MIGRATION_SETTINGS['max_file_size_mb']}MB"

        # Check if empty
        if len(content) == 0:
            return False, "File is empty"

        # Try to decode content
        try:
            decoded_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                decoded_content = content.decode('latin-1')
            except:
                return False, "Unable to decode file content"

        # Detect platform
        platform = self.detect_platform(filename, decoded_content)
        if not platform:
            return False, f"Unsupported file type. Supported platforms: {', '.join(SUPPORTED_PLATFORMS.keys())}"

        return True, f"Valid {SUPPORTED_PLATFORMS[platform]['name']} file detected"

    def save_upload(self, filename: str, content: bytes, metadata: Optional[Dict] = None) -> Dict:
        """
        Save uploaded file and return metadata
        """
        # Validate first
        is_valid, message = self.validate_file(filename, content)
        if not is_valid:
            raise ValueError(message)

        # Decode content
        try:
            decoded_content = content.decode('utf-8')
        except UnicodeDecodeError:
            decoded_content = content.decode('latin-1')

        # Generate unique ID
        file_hash = hashlib.md5(content).hexdigest()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = f"{timestamp}_{file_hash[:8]}"

        # Detect platform
        platform = self.detect_platform(filename, decoded_content)

        # Create directory structure
        platform_dir = os.path.join(self.upload_dir, platform, unique_id)
        os.makedirs(platform_dir, exist_ok=True)

        # Save original file
        original_path = os.path.join(platform_dir, filename)
        with open(original_path, 'wb') as f:
            f.write(content)

        # Create metadata
        file_metadata = {
            'id': unique_id,
            'filename': filename,
            'platform': platform,
            'platform_name': SUPPORTED_PLATFORMS[platform]['name'],
            'size_bytes': len(content),
            'upload_timestamp': datetime.now().isoformat(),
            'file_path': original_path,
            'hash': file_hash,
            'status': 'uploaded',
            'user_metadata': metadata or {}
        }

        # Save metadata
        metadata_path = os.path.join(platform_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(file_metadata, f, indent=2)

        return file_metadata

    def get_upload_info(self, upload_id: str) -> Optional[Dict]:
        """Get metadata for an upload"""
        # Search all platform directories
        for platform in SUPPORTED_PLATFORMS.keys():
            metadata_path = os.path.join(self.upload_dir, platform, upload_id, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        return None

    def list_uploads(self, platform: Optional[str] = None) -> List[Dict]:
        """List all uploads, optionally filtered by platform"""
        uploads = []

        platforms = [platform] if platform else SUPPORTED_PLATFORMS.keys()

        for plat in platforms:
            platform_dir = os.path.join(self.upload_dir, plat)
            if not os.path.exists(platform_dir):
                continue

            for upload_id in os.listdir(platform_dir):
                metadata_path = os.path.join(platform_dir, upload_id, 'metadata.json')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        uploads.append(json.load(f))

        return sorted(uploads, key=lambda x: x['upload_timestamp'], reverse=True)


# Example usage
if __name__ == '__main__':
    handler = UploadHandler()
    print("Upload handler initialized")
    print(f"Supported platforms: {list(SUPPORTED_PLATFORMS.keys())}")
