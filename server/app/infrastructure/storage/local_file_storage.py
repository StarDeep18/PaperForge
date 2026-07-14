"""
Local File Storage.

Stores uploaded documents on the local filesystem.
Designed to be replaced with S3/GCS in production.
"""

import os
import uuid
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import logger


class LocalFileStorage:
    """
    Local filesystem storage for uploaded documents.

    Files are stored with UUID-based names to prevent
    path traversal attacks and filename collisions.
    """

    def __init__(self):
        settings = get_settings()
        self._upload_dir = Path(settings.upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(
        self,
        content: bytes,
        original_filename: str,
        user_id: str,
    ) -> tuple[str, str]:
        """
        Save uploaded file content to disk.

        Args:
            content: Raw file bytes.
            original_filename: The user's original filename.
            user_id: User ID for directory scoping.

        Returns:
            Tuple of (stored_filename, full_file_path).
        """
        # Create user-specific directory
        user_dir = self._upload_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        ext = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4()}{ext}"
        file_path = user_dir / stored_filename

        # Write file
        file_path.write_bytes(content)

        logger.info(
            f"Saved file: {original_filename} -> {file_path} "
            f"({len(content)} bytes)"
        )

        return stored_filename, str(file_path)

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk.

        Args:
            file_path: Full path to the file.

        Returns:
            True if deleted, False if not found.
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        return False

    async def get_file_path(self, file_path: str) -> Path | None:
        """
        Verify a file exists and return its Path.

        Args:
            file_path: Full path to the file.

        Returns:
            Path object if exists, None otherwise.
        """
        path = Path(file_path)
        return path if path.exists() else None
