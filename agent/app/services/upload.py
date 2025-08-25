"""
Upload management service
"""

from typing import List, Optional
from datetime import datetime
from supabase import Client
from fastapi import UploadFile, HTTPException
from app.models.upload import Upload, UploadCreate, UploadStatus, ParsedData
from app.services.storage import StorageService
from app.services.parser import CVParserService


class UploadService:
    """Service for managing file uploads and parsing"""
    
    def __init__(self, db: Client):
        self.db = db
        self.storage_service = StorageService(db)
        self.parser_service = CVParserService(db)
    
    async def create_upload_record(self, user_id: str, upload_data: UploadCreate, file_path: str) -> Upload:
        """Create upload record in database"""
        insert_data = {
            "user_id": user_id,
            "filename": upload_data.filename,
            "file_size": upload_data.file_size,
            "mime_type": upload_data.mime_type,
            "file_path": file_path,
            "status": UploadStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("uploads").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create upload record")
        
        return Upload(**result.data[0])
    
    async def get_upload(self, user_id: str, upload_id: str) -> Optional[Upload]:
        """Get upload record by ID"""
        result = self.db.table("uploads").select("*").eq("id", upload_id).eq("user_id", user_id).execute()
        if result.data:
            return Upload(**result.data[0])
        return None
    
    async def get_user_uploads(self, user_id: str) -> List[Upload]:
        """Get all uploads for a user"""
        result = self.db.table("uploads").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [Upload(**item) for item in result.data]
    
    async def update_upload_status(
        self, 
        upload_id: str, 
        status: UploadStatus, 
        parsed_data: Optional[ParsedData] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update upload status and parsed data"""
        update_data = {
            "status": status.value,
            "processed_at": datetime.utcnow().isoformat() if status in [UploadStatus.COMPLETED, UploadStatus.FAILED] else None
        }
        
        if parsed_data:
            update_data["parsed_data"] = parsed_data.dict()
        
        if error_message:
            update_data["error_message"] = error_message
        
        result = self.db.table("uploads").update(update_data).eq("id", upload_id).execute()
        return len(result.data) > 0
    
    async def upload_and_parse_cv(self, user_id: str, file: UploadFile) -> Upload:
        """Upload CV file and initiate parsing"""
        try:
            # Upload file to storage
            file_path, file_url = await self.storage_service.upload_file(user_id, file)
            
            # Create upload record
            upload_data = UploadCreate(
                filename=file.filename,
                file_size=len(await file.read()),
                mime_type=file.content_type
            )
            
            # Reset file pointer
            await file.seek(0)
            
            upload_record = await self.create_upload_record(user_id, upload_data, file_path)
            
            # Start parsing process
            await self._parse_upload_async(upload_record.id, user_id, file_path)
            
            return upload_record
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def _parse_upload_async(self, upload_id: str, user_id: str, file_path: str):
        """Parse uploaded CV asynchronously"""
        try:
            # Update status to processing
            await self.update_upload_status(upload_id, UploadStatus.PROCESSING)
            
            # Parse the CV
            parsed_data = await self.parser_service.parse_cv(file_path, user_id)
            
            # Update with parsed data
            await self.update_upload_status(upload_id, UploadStatus.COMPLETED, parsed_data)
            
        except Exception as e:
            # Update with error
            await self.update_upload_status(
                upload_id, 
                UploadStatus.FAILED, 
                error_message=str(e)
            )
    
    async def get_parsed_data(self, user_id: str, upload_id: str) -> Optional[ParsedData]:
        """Get parsed data for an upload"""
        upload = await self.get_upload(user_id, upload_id)
        if upload and upload.parsed_data:
            return upload.parsed_data
        return None
    
    async def delete_upload(self, user_id: str, upload_id: str) -> bool:
        """Delete upload record and associated file"""
        upload = await self.get_upload(user_id, upload_id)
        if not upload:
            return False
        
        try:
            # Delete file from storage
            await self.storage_service.delete_file(user_id, upload.file_path)
            
            # Delete database record
            result = self.db.table("uploads").delete().eq("id", upload_id).eq("user_id", user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete upload: {str(e)}")
    
    async def get_download_url(self, user_id: str, upload_id: str) -> str:
        """Get signed download URL for uploaded file"""
        upload = await self.get_upload(user_id, upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        return await self.storage_service.get_signed_url(user_id, upload.file_path)