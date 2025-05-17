from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FileBase(BaseModel):
    filename: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_public: Optional[bool] = False

class FileCreate(FileBase):
    pass

class FileUpdate(FileBase):
    pass

class FileResponse(FileBase):
    id: str
    original_filename: str
    file_size: int
    file_type: str
    is_public: bool
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class FileList(BaseModel):
    total: int
    page: int
    page_size: int
    files: List[FileResponse]

class FileVisibilityUpdate(BaseModel):
    is_public: bool

# Find the FileAccessLinkCreate class and update it to include a password field

class FileAccessLinkCreate(BaseModel):
    expires_in_hours: Optional[int] = None
    is_view_only: bool = False
    password: Optional[str] = None  # Add this line for password protection

class FileAccessLinkResponse(BaseModel):
    id: str
    file_id: str
    token: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    is_view_only: bool
    is_password_protected: bool  # Make sure this field exists
    download_url: str
    
    class Config:
        orm_mode = True