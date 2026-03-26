"""
File Upload API Routes - For product image management
Supports image uploads with automatic storage to /uploads folder
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Will be set by main app
db = None

# Upload directory - stored in a persistent location
UPLOAD_DIR = Path("/app/frontend/public/uploads")

def set_database(database):
    """Set the database connection"""
    global db
    db = database

def ensure_upload_dir():
    """Ensure upload directory exists"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory ready: {UPLOAD_DIR}")

# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    product_id: Optional[str] = Form(None),
    image_type: str = Form("gallery")  # "main" or "gallery"
):
    """
    Upload a product image
    - Stores file in /uploads folder
    - Returns the public URL path
    - Optionally associates with a product
    """
    ensure_upload_dir()
    
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
        
        if product_id:
            safe_filename = f"product_{product_id}_{image_type}_{timestamp}_{unique_id}{file_ext}"
        else:
            safe_filename = f"upload_{timestamp}_{unique_id}{file_ext}"
        
        # Save file
        file_path = UPLOAD_DIR / safe_filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Public URL path (relative to frontend)
        public_url = f"/uploads/{safe_filename}"
        
        logger.info(f"Image uploaded: {safe_filename} ({len(content)} bytes)")
        
        # Store upload record in database
        if db is not None:
            upload_record = {
                "id": str(uuid.uuid4()),
                "filename": safe_filename,
                "original_filename": file.filename,
                "url": public_url,
                "product_id": product_id,
                "image_type": image_type,
                "file_size": len(content),
                "content_type": file.content_type,
                "created_at": datetime.now(timezone.utc)
            }
            await db.uploads.insert_one(upload_record)
        
        return {
            "success": True,
            "url": public_url,
            "filename": safe_filename,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/image/{filename}")
async def delete_image(filename: str):
    """Delete an uploaded image"""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Security check - ensure we're only deleting from uploads folder
        if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file
        file_path.unlink()
        
        # Remove from database
        if db is not None:
            await db.uploads.delete_one({"filename": filename})
        
        logger.info(f"Image deleted: {filename}")
        
        return {"success": True, "message": "File deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_uploads(product_id: Optional[str] = None):
    """List all uploaded images, optionally filtered by product"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = {}
        if product_id is not None:
            query["product_id"] = product_id
        
        uploads = await db.uploads.find(query, {"_id": 0}).sort("created_at", -1).to_list(length=100)
        
        return {
            "success": True,
            "uploads": uploads,
            "count": len(uploads)
        }
        
    except Exception as e:
        logger.error(f"List uploads error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
