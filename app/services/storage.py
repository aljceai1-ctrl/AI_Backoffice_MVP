"""Storage service — persists uploaded invoice files to the local filesystem.

Binary files are NEVER stored in the database; only the path is recorded.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def save_upload(file: UploadFile) -> Tuple[str, str]:
    """Write an uploaded file to the configured uploads directory.

    The file is saved under a UUID-prefixed name to prevent collisions.

    Args:
        file: Incoming multipart file from FastAPI.

    Returns:
        Tuple of (original_filename, absolute_storage_path).
    """
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or "unknown"
    suffix = Path(original_name).suffix or ".bin"
    unique_name = f"{uuid.uuid4()}{suffix}"
    dest_path = upload_dir / unique_name

    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    logger.info(
        "Saved upload '%s' → %s (%d bytes)",
        original_name,
        dest_path,
        dest_path.stat().st_size,
    )
    return original_name, str(dest_path)
