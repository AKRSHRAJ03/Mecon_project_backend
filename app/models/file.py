from sqlalchemy import Boolean, Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base
import uuid

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    original_filename = Column(String)
    file_path = Column(String)  # Path to the encrypted file
    file_size = Column(Integer)
    file_type = Column(String)
    encryption_key = Column(String)  # Encrypted key stored in DB
    is_public = Column(Boolean, default=False)
    user_id = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    description = Column(Text, nullable=True)
    tags = Column(String, nullable=True)  # Comma-separated tags

class FileAccessLink(Base):
    __tablename__ = "file_access_links"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, ForeignKey("files.id", ondelete="CASCADE"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_view_only = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)