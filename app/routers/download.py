from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime

from database import get_db
from models.file import File as FileModel, FileAccessLink
from utils.encryption import decrypt_file, decrypt_key, get_master_key
from config import STORAGE_PATH

router = APIRouter(
    prefix="/api/v1/download",
    tags=["Download"]
)

@router.get("/{token}")
def download_file_by_token(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Get link from database
    link = db.query(FileAccessLink).filter(FileAccessLink.token == token).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or expired")
    
    # Check if link is active
    if not link.is_active:
        raise HTTPException(status_code=403, detail="This link has been deactivated")
    
    # Check if link has expired
    if link.expires_at and link.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=403, detail="This link has expired")
    
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == link.file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Decrypt the encryption key
    master_key = get_master_key()
    encrypted_key = file.encryption_key.encode()
    decryption_key = decrypt_key(encrypted_key, master_key)
    
    # Create temporary file for decrypted content
    temp_file_path = os.path.join(STORAGE_PATH, f"temp_{uuid.uuid4()}{os.path.splitext(file.original_filename)[1]}")
    
    # Decrypt file
    decrypt_file(file.file_path, temp_file_path, decryption_key)
    
    # Schedule cleanup of temporary file
    background_tasks.add_task(os.remove, temp_file_path)
    
    # Use FastAPI's FileResponse correctly
    from starlette.responses import FileResponse as StarletteFileResponse
    return StarletteFileResponse(
        path=temp_file_path,
        filename=file.original_filename,
        media_type=file.file_type,
        headers={"Content-Disposition": f"attachment; filename={file.original_filename}"}
    )