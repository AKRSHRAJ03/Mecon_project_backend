import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# File Storage
STORAGE_PATH = os.path.join(BASE_DIR, os.getenv("STORAGE_PATH", "app/storage/encrypted_files"))
os.makedirs(STORAGE_PATH, exist_ok=True)

# Email Settings
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USERNAME = "adkdl1234@gmail.com"
EMAIL_PASSWORD = "qhlz stia xuhg jyha"
EMAIL_FROM = "adkdl1234@gmail.com"
# Use backend URL instead of frontend
FRONTEND_URL = "http://localhost:8002"  # Your FastAPI server URL
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_TLS = os.getenv("MAIL_TLS", "True").lower() == "true"
MAIL_SSL = os.getenv("MAIL_SSL", "False").lower() == "true"