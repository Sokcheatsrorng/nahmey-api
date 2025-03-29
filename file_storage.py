import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the base directory for file storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Maximum file size from environment variable (default 10MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # Default 10MB in bytes

# Create the upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create subdirectories for different file types
FOOD_IMAGES_DIR = os.path.join(UPLOAD_DIR, "food_images")
RESTAURANT_IMAGES_DIR = os.path.join(UPLOAD_DIR, "restaurant_images")
USER_IMAGES_DIR = os.path.join(UPLOAD_DIR, "user_images")
MENU_IMAGES_DIR = os.path.join(UPLOAD_DIR, "menu_images")
OTHER_FILES_DIR = os.path.join(UPLOAD_DIR, "other")

# Create all subdirectories
for directory in [FOOD_IMAGES_DIR, RESTAURANT_IMAGES_DIR, USER_IMAGES_DIR, MENU_IMAGES_DIR, OTHER_FILES_DIR]:
    os.makedirs(directory, exist_ok=True)

# Define models for file metadata
class FileMetadata(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    path: str
    url: str
    uploaded_by: str
    uploaded_at: datetime
    category: str
    related_id: Optional[str] = None
    description: Optional[str] = None

# In-memory database for file metadata
files_db: Dict[str, FileMetadata] = {}

# Allowed file extensions by category
ALLOWED_EXTENSIONS = {
    "food_images": [".jpg", ".jpeg", ".png", ".webp"],
    "restaurant_images": [".jpg", ".jpeg", ".png", ".webp"],
    "user_images": [".jpg", ".jpeg", ".png", ".webp"],
    "menu_images": [".jpg", ".jpeg", ".png", ".webp", ".pdf"],
    "other": [".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"]
}

# Maximum file size from environment variable
# Already defined above, so we can remove this line

async def save_upload_file(
    upload_file: UploadFile, 
    category: str, 
    user_id: str,
    related_id: Optional[str] = None,
    description: Optional[str] = None
) -> FileMetadata:
    """
    Save an uploaded file to the appropriate directory and return its metadata
    """
    # Validate file size
    file_size = 0
    content = await upload_file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Reset file position after reading
    await upload_file.seek(0)
    
    # Validate file extension
    _, file_ext = os.path.splitext(upload_file.filename)
    file_ext = file_ext.lower()
    
    if category not in ALLOWED_EXTENSIONS or file_ext not in ALLOWED_EXTENSIONS[category]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file_ext} not allowed for category {category}"
        )
    
    # Generate a unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Determine the directory based on category
    if category == "food_images":
        directory = FOOD_IMAGES_DIR
    elif category == "restaurant_images":
        directory = RESTAURANT_IMAGES_DIR
    elif category == "user_images":
        directory = USER_IMAGES_DIR
    elif category == "menu_images":
        directory = MENU_IMAGES_DIR
    else:
        directory = OTHER_FILES_DIR
    
    # Create the full file path
    file_path = os.path.join(directory, unique_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Generate a URL for the file
    file_url = f"/files/{category}/{unique_filename}"
    
    # Create and store file metadata
    file_id = str(uuid.uuid4())
    file_metadata = FileMetadata(
        id=file_id,
        filename=upload_file.filename,
        content_type=upload_file.content_type,
        size=file_size,
        path=file_path,
        url=file_url,
        uploaded_by=user_id,
        uploaded_at=datetime.now(),
        category=category,
        related_id=related_id,
        description=description
    )
    
    files_db[file_id] = file_metadata
    
    return file_metadata

async def delete_file(file_id: str, user_id: str, is_admin: bool = False) -> bool:
    """
    Delete a file and its metadata
    """
    if file_id not in files_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_metadata = files_db[file_id]
    
    # Check if the user is authorized to delete the file
    if file_metadata.uploaded_by != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this file"
        )
    
    # Delete the file from the filesystem
    try:
        os.remove(file_metadata.path)
    except OSError:
        # If the file doesn't exist, just continue
        pass
    
    # Delete the metadata
    del files_db[file_id]
    
    return True

def get_file_metadata(file_id: str) -> FileMetadata:
    """
    Get metadata for a specific file
    """
    if file_id not in files_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return files_db[file_id]

def get_files_by_category(category: str) -> List[FileMetadata]:
    """
    Get all files in a specific category
    """
    return [file for file in files_db.values() if file.category == category]

def get_files_by_related_id(related_id: str) -> List[FileMetadata]:
    """
    Get all files related to a specific entity (food item, restaurant, etc.)
    """
    return [file for file in files_db.values() if file.related_id == related_id]

def get_files_by_user(user_id: str) -> List[FileMetadata]:
    """
    Get all files uploaded by a specific user
    """
    return [file for file in files_db.values() if file.uploaded_by == user_id]

