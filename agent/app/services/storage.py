"""
File storage service using Supabase Storage
"""

import os
import uuid
from typing import Optional, Tuple
from supabase import Client
from fastapi import UploadFile, HTTPException
from app.core.config import settings


class StorageService:
    """Service for file storage operations"""
    
    def __init__(self, db: Client):
        self.db = db
        self.uploads_bucket = "uploads"
        self.documents_bucket = "documents"
    
    async def upload_file(
        self, 
        user_id: str, 
        file: UploadFile, 
        bucket: str = None
    ) -> Tuple[str, str]:
        """
        Upload file to Supabase Storage
        Returns (file_path, file_url)
        """
        if bucket is None:
            bucket = self.uploads_bucket
        
        # Validate file type
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 50MB limit"
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"{user_id}/{unique_filename}"
        
        try:
            # Upload to Supabase Storage
            result = self.db.storage.from_(bucket).upload(
                file_path,
                file_content,
                file_options={
                    "content-type": file.content_type,
                    "cache-control": "3600"
                }
            )
            
            if result.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload file to storage"
                )
            
            # Get public URL
            file_url = self.db.storage.from_(bucket).get_public_url(file_path)
            
            return file_path, file_url
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )
    
    async def get_signed_url(
        self, 
        user_id: str, 
        file_path: str, 
        bucket: str = None,
        expires_in: int = 3600
    ) -> str:
        """
        Generate signed URL for file access
        """
        if bucket is None:
            bucket = self.uploads_bucket
        
        # Verify user owns the file
        if not file_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to file"
            )
        
        try:
            signed_url = self.db.storage.from_(bucket).create_signed_url(
                file_path, 
                expires_in
            )
            return signed_url["signedURL"]
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate signed URL: {str(e)}"
            )
    
    async def delete_file(
        self, 
        user_id: str, 
        file_path: str, 
        bucket: str = None
    ) -> bool:
        """
        Delete file from storage
        """
        if bucket is None:
            bucket = self.uploads_bucket
        
        # Verify user owns the file
        if not file_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to file"
            )
        
        try:
            result = self.db.storage.from_(bucket).remove([file_path])
            return len(result) > 0
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete file: {str(e)}"
            )
    
    async def move_file(
        self, 
        user_id: str, 
        source_path: str, 
        dest_path: str,
        source_bucket: str = None,
        dest_bucket: str = None
    ) -> str:
        """
        Move file between buckets or paths
        """
        if source_bucket is None:
            source_bucket = self.uploads_bucket
        if dest_bucket is None:
            dest_bucket = self.documents_bucket
        
        # Verify user owns the file
        if not source_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to source file"
            )
        
        if not dest_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=403,
                detail="Access denied to destination path"
            )
        
        try:
            # Move file
            result = self.db.storage.from_(source_bucket).move(
                source_path, 
                dest_path,
                dest_bucket
            )
            
            if result.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to move file"
                )
            
            return dest_path
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to move file: {str(e)}"
            )