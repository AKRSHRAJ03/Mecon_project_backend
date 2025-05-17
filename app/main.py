from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Create a fresh FastAPI instance
app = FastAPI(
    title="File Encryption API",
    description="API for secure file storage with encryption",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import all models first to ensure they're registered with SQLAlchemy
from models.user import User, RefreshToken
from models.file import File, FileAccessLink

# Now import database components and create tables
from database import engine, Base
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")

# Create storage directory if it doesn't exist
os.makedirs("storage/encrypted_files", exist_ok=True)

# Import routers directly
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.files import router as files_router
from routers import download

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)
app.include_router(download.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the File Encryption API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)