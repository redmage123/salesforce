#!/usr/bin/env python3
"""
Artemis Output Storage Manager

Handles all pipeline outputs with support for local and remote storage:
- Local storage: Filesystem-based (default: repo_root/output)
- Remote storage: S3, GCS, Azure Blob Storage

All outputs (ADRs, developer work, test results, etc.) go through this manager.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List
from abc import ABC, abstractmethod
from datetime import datetime


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    def write_file(self, relative_path: str, content: str) -> str:
        """
        Write content to a file.

        Args:
            relative_path: Path relative to base storage location
            content: File content

        Returns:
            Full path or URI of written file
        """
        pass

    @abstractmethod
    def read_file(self, relative_path: str) -> str:
        """Read content from a file"""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List all files with given prefix"""
        pass

    @abstractmethod
    def delete_file(self, relative_path: str) -> bool:
        """Delete a file"""
        pass

    @abstractmethod
    def get_full_path(self, relative_path: str) -> str:
        """Get full path/URI for a relative path"""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: str = "../../outputs"):
        # Convert relative paths to absolute based on this file's location
        if not Path(base_path).is_absolute():
            # Resolve relative to the agile directory
            agile_dir = Path(__file__).parent
            base_path = (agile_dir / base_path).resolve()

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Try to set proper permissions
        try:
            os.chmod(self.base_path, 0o755)
        except PermissionError:
            pass

    def write_file(self, relative_path: str, content: str) -> str:
        """Write file to local storage"""
        full_path = self.base_path / relative_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        with open(full_path, 'w') as f:
            f.write(content)

        return str(full_path)

    def read_file(self, relative_path: str) -> str:
        """Read file from local storage"""
        full_path = self.base_path / relative_path
        with open(full_path, 'r') as f:
            return f.read()

    def list_files(self, prefix: str = "") -> List[str]:
        """List all files with given prefix"""
        search_path = self.base_path / prefix if prefix else self.base_path
        if not search_path.exists():
            return []

        files = []
        for path in search_path.rglob("*"):
            if path.is_file():
                relative = path.relative_to(self.base_path)
                files.append(str(relative))

        return sorted(files)

    def delete_file(self, relative_path: str) -> bool:
        """Delete file from local storage"""
        full_path = self.base_path / relative_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def get_full_path(self, relative_path: str) -> str:
        """Get full filesystem path"""
        return str(self.base_path / relative_path)


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend"""

    def __init__(self, bucket: str, region: str = "us-east-1", prefix: str = ""):
        self.bucket = bucket
        self.region = region
        self.prefix = prefix

        try:
            import boto3
            self.s3 = boto3.client('s3', region_name=region)
        except ImportError:
            raise RuntimeError("boto3 required for S3 storage. Install with: pip install boto3")

    def write_file(self, relative_path: str, content: str) -> str:
        """Write file to S3"""
        key = f"{self.prefix}/{relative_path}".lstrip("/")
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content.encode('utf-8')
        )
        return f"s3://{self.bucket}/{key}"

    def read_file(self, relative_path: str) -> str:
        """Read file from S3"""
        key = f"{self.prefix}/{relative_path}".lstrip("/")
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read().decode('utf-8')

    def list_files(self, prefix: str = "") -> List[str]:
        """List all files with given prefix"""
        full_prefix = f"{self.prefix}/{prefix}".lstrip("/")
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=full_prefix)

        files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if self.prefix:
                key = key[len(self.prefix):].lstrip("/")
            files.append(key)

        return sorted(files)

    def delete_file(self, relative_path: str) -> bool:
        """Delete file from S3"""
        key = f"{self.prefix}/{relative_path}".lstrip("/")
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        return True

    def get_full_path(self, relative_path: str) -> str:
        """Get S3 URI"""
        key = f"{self.prefix}/{relative_path}".lstrip("/")
        return f"s3://{self.bucket}/{key}"


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend"""

    def __init__(self, bucket: str, project: str, prefix: str = ""):
        self.bucket_name = bucket
        self.project = project
        self.prefix = prefix

        try:
            from google.cloud import storage
            self.storage_client = storage.Client(project=project)
            self.bucket = self.storage_client.bucket(bucket)
        except ImportError:
            raise RuntimeError("google-cloud-storage required for GCS. Install with: pip install google-cloud-storage")

    def write_file(self, relative_path: str, content: str) -> str:
        """Write file to GCS"""
        blob_name = f"{self.prefix}/{relative_path}".lstrip("/")
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(content)
        return f"gs://{self.bucket_name}/{blob_name}"

    def read_file(self, relative_path: str) -> str:
        """Read file from GCS"""
        blob_name = f"{self.prefix}/{relative_path}".lstrip("/")
        blob = self.bucket.blob(blob_name)
        return blob.download_as_text()

    def list_files(self, prefix: str = "") -> List[str]:
        """List all files with given prefix"""
        full_prefix = f"{self.prefix}/{prefix}".lstrip("/")
        blobs = self.storage_client.list_blobs(self.bucket_name, prefix=full_prefix)

        files = []
        for blob in blobs:
            name = blob.name
            if self.prefix:
                name = name[len(self.prefix):].lstrip("/")
            files.append(name)

        return sorted(files)

    def delete_file(self, relative_path: str) -> bool:
        """Delete file from GCS"""
        blob_name = f"{self.prefix}/{relative_path}".lstrip("/")
        blob = self.bucket.blob(blob_name)
        blob.delete()
        return True

    def get_full_path(self, relative_path: str) -> str:
        """Get GCS URI"""
        blob_name = f"{self.prefix}/{relative_path}".lstrip("/")
        return f"gs://{self.bucket_name}/{blob_name}"


class OutputStorageManager:
    """
    Manages all Artemis pipeline outputs with local or remote storage.

    Configuration via environment variables:
    - ARTEMIS_OUTPUT_STORAGE: "local" or "remote" (default: local)
    - ARTEMIS_OUTPUT_PATH: Local storage base path (default: repo_root/output)
    - ARTEMIS_REMOTE_STORAGE_PROVIDER: "s3", "gcs", or "azure"
    - Provider-specific configs (see .env.example)
    """

    def __init__(self):
        storage_type = os.getenv("ARTEMIS_OUTPUT_STORAGE", "local")

        if storage_type == "local":
            # Default to repo root/output (../../output from .agents/agile)
            default_path = "../../output"
            base_path = os.getenv("ARTEMIS_OUTPUT_PATH", default_path)

            # Convert relative path to absolute
            if not os.path.isabs(base_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                base_path = os.path.join(script_dir, base_path)

            self.backend = LocalStorageBackend(base_path)
        elif storage_type == "remote":
            provider = os.getenv("ARTEMIS_REMOTE_STORAGE_PROVIDER", "s3")

            if provider == "s3":
                self.backend = S3StorageBackend(
                    bucket=os.getenv("ARTEMIS_S3_BUCKET"),
                    region=os.getenv("ARTEMIS_S3_REGION", "us-east-1")
                )
            elif provider == "gcs":
                self.backend = GCSStorageBackend(
                    bucket=os.getenv("ARTEMIS_GCS_BUCKET"),
                    project=os.getenv("ARTEMIS_GCS_PROJECT")
                )
            else:
                raise ValueError(f"Unsupported remote storage provider: {provider}")
        else:
            raise ValueError(f"Invalid storage type: {storage_type}")

    def write_adr(self, card_id: str, adr_number: str, content: str) -> str:
        """Write ADR file"""
        path = f"adrs/{card_id}/ADR-{adr_number}.md"
        return self.backend.write_file(path, content)

    def write_developer_output(self, card_id: str, developer: str, filename: str, content: str) -> str:
        """Write developer output file"""
        path = f"developers/{card_id}/{developer}/{filename}"
        return self.backend.write_file(path, content)

    def write_test_results(self, card_id: str, test_type: str, content: str) -> str:
        """Write test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"tests/{card_id}/{test_type}_{timestamp}.json"
        return self.backend.write_file(path, content)

    def write_pipeline_report(self, card_id: str, content: str) -> str:
        """Write pipeline execution report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"reports/{card_id}/pipeline_{timestamp}.json"
        return self.backend.write_file(path, content)

    def read_file(self, relative_path: str) -> str:
        """Read any file"""
        return self.backend.read_file(relative_path)

    def list_card_outputs(self, card_id: str) -> Dict[str, List[str]]:
        """List all outputs for a card"""
        return {
            "adrs": self.backend.list_files(f"adrs/{card_id}"),
            "developers": self.backend.list_files(f"developers/{card_id}"),
            "tests": self.backend.list_files(f"tests/{card_id}"),
            "reports": self.backend.list_files(f"reports/{card_id}")
        }

    def get_storage_info(self) -> Dict:
        """Get information about storage configuration"""
        backend_type = self.backend.__class__.__name__
        if isinstance(self.backend, LocalStorageBackend):
            return {
                "type": "local",
                "backend": backend_type,
                "base_path": str(self.backend.base_path)
            }
        elif isinstance(self.backend, S3StorageBackend):
            return {
                "type": "remote",
                "backend": backend_type,
                "provider": "s3",
                "bucket": self.backend.bucket,
                "region": self.backend.region
            }
        elif isinstance(self.backend, GCSStorageBackend):
            return {
                "type": "remote",
                "backend": backend_type,
                "provider": "gcs",
                "bucket": self.backend.bucket_name,
                "project": self.backend.project
            }
        else:
            return {"type": "unknown", "backend": backend_type}


# Global storage instance
_storage: Optional[OutputStorageManager] = None


def get_storage() -> OutputStorageManager:
    """Get or create global storage manager"""
    global _storage
    if _storage is None:
        _storage = OutputStorageManager()
    return _storage


if __name__ == "__main__":
    # Test the storage manager
    storage = OutputStorageManager()

    print("Storage Info:")
    print(storage.get_storage_info())

    # Write a test file
    test_path = storage.write_adr("test-card-001", "001", "# Test ADR\n\nThis is a test ADR.")
    print(f"\nWrote test file: {test_path}")

    # Read it back
    content = storage.read_file("adrs/test-card-001/ADR-001.md")
    print(f"\nRead content: {content[:50]}...")

    # List files
    outputs = storage.list_card_outputs("test-card-001")
    print(f"\nCard outputs: {outputs}")
