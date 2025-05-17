from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.file import File as FileModel, FileAccessLink
from schemas.file import (
    FileResponse, FileCreate, FileUpdate, FileList, 
    FileVisibilityUpdate, FileAccessLinkCreate, FileAccessLinkResponse
)
from utils.auth import get_current_user
from utils.encryption import (
    generate_key, encrypt_file, decrypt_file, encrypt_key, 
    decrypt_key, get_master_key, generate_temp_file_path
)
from config import STORAGE_PATH

router = APIRouter(
    prefix="/api/v1/files",
    tags=["Files"]
)

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create directory if it doesn't exist
    os.makedirs(STORAGE_PATH, exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    encrypted_filename = f"{file_id}{file_extension}.enc"
    file_path = os.path.join(STORAGE_PATH, encrypted_filename)
    
    # Save uploaded file temporarily
    temp_file_path = os.path.join(STORAGE_PATH, f"temp_{file_id}{file_extension}")
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generate encryption key
    encryption_key, _ = generate_key()
    
    # Encrypt file
    encrypt_file(temp_file_path, file_path, encryption_key)
    
    # Remove temporary file
    os.remove(temp_file_path)
    
    # Encrypt the encryption key with master key
    master_key = get_master_key()
    encrypted_key = encrypt_key(encryption_key, master_key)
    
    # Create file record in database
    db_file = FileModel(
        id=file_id,
        filename=encrypted_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_type=file.content_type,
        encryption_key=encrypted_key.decode(),
        is_public=is_public,
        user_id=current_user.id,
        description=description,
        tags=tags
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file

@router.get("", response_model=FileList)
def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Base query
    query = db.query(FileModel).filter(FileModel.user_id == current_user.id)
    
    # Apply filters
    if file_type:
        query = query.filter(FileModel.file_type.contains(file_type))
    
    if search:
        query = query.filter(
            (FileModel.original_filename.contains(search)) |
            (FileModel.description.contains(search)) |
            (FileModel.tags.contains(search))
        )
    
    # Count total before pagination
    total = query.count()
    
    # Apply sorting
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(FileModel, sort_by)))
    else:
        query = query.order_by(getattr(FileModel, sort_by))
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    files = query.all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "files": files
    }

@router.get("/{file_id}", response_model=FileResponse)
def get_file_metadata(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access
    if file.user_id != current_user.id and not file.is_public:
        raise HTTPException(status_code=403, detail="You don't have permission to access this file")
    
    return file

@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.user_id == current_user.id
    ).first()
    
    if not file:
        # Check if file exists and is public
        public_file = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.is_public == True
        ).first()
        
        if not public_file:
            raise HTTPException(status_code=404, detail="File not found")
        file = public_file
    
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

@router.put("/{file_id}", response_model=FileResponse)
def update_file_metadata(
    file_id: str,
    file_update: FileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access
    if file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to update this file")
    
    # Update fields
    if file_update.filename is not None:
        file.original_filename = file_update.filename
    
    if file_update.description is not None:
        file.description = file_update.description
    
    if file_update.tags is not None:
        file.tags = file_update.tags
    
    if file_update.is_public is not None:
        file.is_public = file_update.is_public
    
    db.commit()
    db.refresh(file)
    
    return file

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access
    if file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this file")
    
    # Delete file from storage
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # Delete file from database
    db.delete(file)
    db.commit()
    
    return None

@router.put("/{file_id}/replace", response_model=FileResponse)
async def replace_file(
    file_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access
    if db_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to replace this file")
    
    # Save uploaded file temporarily
    temp_file_path = os.path.join(STORAGE_PATH, f"temp_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}")
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generate new encryption key
    encryption_key, _ = generate_key()
    
    # Delete old file
    if os.path.exists(db_file.file_path):
        os.remove(db_file.file_path)
    
    # Encrypt new file
    encrypt_file(temp_file_path, db_file.file_path, encryption_key)
    
    # Remove temporary file
    os.remove(temp_file_path)
    
    # Encrypt the encryption key with master key
    master_key = get_master_key()
    encrypted_key = encrypt_key(encryption_key, master_key)
    
    # Update file record
    db_file.original_filename = file.filename
    db_file.file_size = os.path.getsize(db_file.file_path)
    db_file.file_type = file.content_type
    db_file.encryption_key = encrypted_key.decode()
    db_file.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_file)
    
    return db_file

@router.post("/{file_id}/link", response_model=FileAccessLinkResponse)
def create_file_link(
    file_id: str,
    link_params: FileAccessLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.user_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate a unique token
    token = str(uuid.uuid4())
    
    # Calculate expiration time if provided
    expires_at = None
    if link_params.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=link_params.expires_in_hours)
    
    # Create link record - removed password and created_by fields
    link = FileAccessLink(
        token=token,
        file_id=file_id,
        is_active=True,
        is_view_only=link_params.is_view_only,
        expires_at=expires_at
    )
    
    db.add(link)
    db.commit()
    db.refresh(link)
    
    # Return link with full URL
    base_url = "http://localhost:8002"  # This should be configurable
    download_url = f"{base_url}/api/v1/download/{token}"
    
    return {
        "id": str(link.id),
        "file_id": file_id,
        "token": token,
        "expires_at": expires_at,
        "created_at": link.created_at,
        "is_view_only": link.is_view_only,
        "is_password_protected": False,  # Always false since we're not using passwords
        "download_url": download_url
    }

@router.put("/{file_id}/visibility", response_model=FileResponse)
def update_file_visibility(
    file_id: str,
    visibility: FileVisibilityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access
    if file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to update this file")
    
    # Update visibility
    file.is_public = visibility.is_public
    db.commit()
    db.refresh(file)
    
    return file