from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import uuid

from database import get_db
from models.user import User, RefreshToken
from schemas.user import UserCreate, UserResponse, Token, TokenData, PasswordReset, PasswordResetRequest
from utils.auth import (
    get_password_hash, verify_password, create_access_token, 
    create_refresh_token, get_current_user, get_user_by_email
)
from utils.email import send_password_reset_email
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Find user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(user_id=user.id, db=db)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Revoke all refresh tokens for the user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    
    db.commit()
    
    return {"message": "Successfully logged out"}

@router.post("/refresh-token", response_model=Token)
def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    # Find the refresh token in the database
    token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.is_revoked == False
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is expired - fix the datetime comparison
    current_time = datetime.utcnow()
    if token.expires_at.replace(tzinfo=None) < current_time:
        # Revoke the token
        token.is_revoked = True
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the user
    user = db.query(User).filter(User.id == token.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    # Create new refresh token
    new_refresh_token = create_refresh_token(user_id=user.id, db=db)
    
    # Revoke the old refresh token
    token.is_revoked = True
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Find user by email
    user = get_user_by_email(db, email=request.email)
    
    if not user:
        # Don't reveal that the email doesn't exist
        return {"message": "If the email exists, a password reset link will be sent"}
    
    # Generate reset token
    reset_token = str(uuid.uuid4())
    
    # Set token expiry (24 hours)
    token_expires = datetime.utcnow() + timedelta(hours=24)
    
    # Update user with reset token
    user.reset_token = reset_token
    user.reset_token_expires = token_expires
    
    db.commit()
    
    # Try to send email but don't fail if it doesn't work
    try:
        background_tasks.add_task(
            send_password_reset_email,
            email=user.email,
            token=reset_token,
            username=user.username
        )
    except Exception as e:
        print(f"Failed to send email: {e}")
    
    # Always return the token for testing
    return {
        "message": "Password reset initiated",
        "reset_token": reset_token,
        "note": "Email sending may have failed, but you can use this token directly"
    }

@router.post("/reset-password")
def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    # Find user by reset token
    user = db.query(User).filter(User.reset_token == reset_data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    
    # Check if token is expired - fix the datetime comparison
    if user.reset_token_expires.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token expired")
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    
    # Clear reset token
    user.reset_token = None
    user.reset_token_expires = None
    
    db.commit()
    
    return {"message": "Password has been reset successfully"}