"""
Document vault service for managing generated files
"""

import os
import hashlib
import mimetypes
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import logging

from supabase import Client
from app.core.config import settings
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class DocumentVaultService:
    """Service for managing document vault operations"""
    
    def __init__(self, db: Client):
        self.db = db
        self.storage = StorageService()
    
    async def store_document(
        self,
        user_id: str,
        file_path: str,
        document_type: str,
        title: str,
        description: Optional[str] = None,
        template_used: Optional[str] = None,
        job_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a document in the vault"""
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file information
            file_info = self._get_file_info(file_path)
            
            # Check for duplicates
            existing_doc = await self._check_duplicate(user_id, file_info["hash"])
            if existing_doc:
                return {
                    "success": False,
                    "error": "Duplicate document already exists",
                    "existing_document_id": existing_doc["id"]
                }
            
            # Upload to storage
            storage_result = await self.storage.upload_file(
                file_path=file_path,
                bucket="documents",
                folder=f"{user_id}/{document_type}"
            )
            
            if not storage_result.get("success"):
                raise Exception(f"Storage upload failed: {storage_result.get('error')}")
            
            # Store in database
            document_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "document_type": document_type,
                "title": title,
                "description": description,
                "file_name": file_info["name"],
                "file_path": storage_result["file_path"],
                "file_url": storage_result["public_url"],
                "file_size": file_info["size"],
                "mime_type": file_info["mime_type"],
                "file_hash": file_info["hash"],
                "template_used": template_used,
                "job_id": job_id,
                "folder_id": folder_id or await self._get_default_folder(user_id, document_type),
                "tags": tags or [],
                "generation_metadata": metadata or {}
            }
            
            result = self.db.table("document_vault").insert(document_data).execute()
            
            if result.data:
                document = result.data[0]
                
                # Log access
                await self._log_access(document["id"], "create", user_id)
                
                return {
                    "success": True,
                    "document": document,
                    "storage_info": storage_result
                }
            else:
                raise Exception("Failed to store document in database")
                
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_documents(
        self,
        user_id: str,
        document_type: Optional[str] = None,
        folder_id: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0,
        search_query: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get user's documents with filtering"""
        try:
            query = self.db.table("document_vault_dashboard").select("*").eq("user_id", user_id)
            
            # Apply filters
            if document_type:
                query = query.eq("document_type", document_type)
            
            if folder_id:
                query = query.eq("folder_id", folder_id)
            
            if status:
                query = query.eq("status", status)
            
            if search_query:
                query = query.or_(f"title.ilike.%{search_query}%,description.ilike.%{search_query}%")
            
            if tags:
                # PostgreSQL array contains query
                for tag in tags:
                    query = query.contains("tags", [tag])
            
            # Get total count
            count_result = query.execute()
            total_count = len(count_result.data) if count_result.data else 0
            
            # Apply pagination and ordering
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            return {
                "success": True,
                "documents": result.data or [],
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific document"""
        try:
            result = self.db.table("document_vault").select("*").eq("id", document_id).eq("user_id", user_id).execute()
            
            if result.data:
                document = result.data[0]
                
                # Log access
                await self._log_access(document_id, "view", user_id)
                
                return document
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    async def update_document(
        self,
        document_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update document metadata"""
        try:
            # Verify ownership
            existing = await self.get_document(document_id, user_id)
            if not existing:
                return {"success": False, "error": "Document not found"}
            
            # Update document
            updates["updated_at"] = datetime.utcnow().isoformat()
            result = self.db.table("document_vault").update(updates).eq("id", document_id).execute()
            
            if result.data:
                # Log access
                await self._log_access(document_id, "edit", user_id)
                
                return {"success": True, "document": result.data[0]}
            else:
                return {"success": False, "error": "Update failed"}
                
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_document(self, document_id: str, user_id: str, permanent: bool = False) -> Dict[str, Any]:
        """Delete or archive document"""
        try:
            # Verify ownership
            existing = await self.get_document(document_id, user_id)
            if not existing:
                return {"success": False, "error": "Document not found"}
            
            if permanent:
                # Delete from storage
                if existing.get("file_path"):
                    await self.storage.delete_file(existing["file_path"])
                
                # Delete from database
                self.db.table("document_vault").delete().eq("id", document_id).execute()
                
                # Log access
                await self._log_access(document_id, "delete", user_id)
                
                return {"success": True, "message": "Document permanently deleted"}
            else:
                # Archive document
                result = self.db.table("document_vault").update({
                    "status": "deleted",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", document_id).execute()
                
                if result.data:
                    return {"success": True, "message": "Document archived"}
                else:
                    return {"success": False, "error": "Archive failed"}
                    
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_share_link(
        self,
        document_id: str,
        user_id: str,
        permissions: List[str] = None,
        expires_in_days: Optional[int] = None,
        shared_with_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a shareable link for document"""
        try:
            # Verify ownership
            existing = await self.get_document(document_id, user_id)
            if not existing:
                return {"success": False, "error": "Document not found"}
            
            # Generate share token
            share_token = self._generate_share_token()
            
            # Calculate expiry
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            # Create share record
            share_data = {
                "id": str(uuid4()),
                "document_id": document_id,
                "shared_by_user_id": user_id,
                "shared_with_email": shared_with_email,
                "share_token": share_token,
                "permissions": permissions or ["view"],
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
            result = self.db.table("document_shares").insert(share_data).execute()
            
            if result.data:
                share_info = result.data[0]
                
                # Update document with share token
                self.db.table("document_vault").update({
                    "share_token": share_token,
                    "share_expires_at": expires_at.isoformat() if expires_at else None
                }).eq("id", document_id).execute()
                
                # Log access
                await self._log_access(document_id, "share", user_id)
                
                share_url = f"{settings.FRONTEND_URL}/shared/{share_token}"
                
                return {
                    "success": True,
                    "share_info": share_info,
                    "share_url": share_url,
                    "share_token": share_token
                }
            else:
                return {"success": False, "error": "Failed to create share"}
                
        except Exception as e:
            logger.error(f"Failed to create share link: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_shared_document(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Get document by share token"""
        try:
            # Get share info
            share_result = self.db.table("document_shares").select("*").eq("share_token", share_token).eq("is_active", True).execute()
            
            if not share_result.data:
                return None
            
            share_info = share_result.data[0]
            
            # Check expiry
            if share_info.get("expires_at"):
                expires_at = datetime.fromisoformat(share_info["expires_at"].replace('Z', '+00:00'))
                if expires_at < datetime.utcnow():
                    return None
            
            # Get document
            doc_result = self.db.table("document_vault").select("*").eq("id", share_info["document_id"]).execute()
            
            if doc_result.data:
                document = doc_result.data[0]
                document["share_permissions"] = share_info["permissions"]
                
                # Update access count
                self.db.table("document_shares").update({
                    "access_count": share_info["access_count"] + 1,
                    "last_accessed_at": datetime.utcnow().isoformat()
                }).eq("id", share_info["id"]).execute()
                
                # Log access
                await self._log_access(share_info["document_id"], "view")
                
                return document
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get shared document: {e}")
            return None
    
    async def get_folders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's document folders"""
        try:
            result = self.db.table("document_folders").select("*").eq("user_id", user_id).order("name").execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get folders: {e}")
            return []
    
    async def create_folder(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        color: str = "#3B82F6",
        icon: str = "folder"
    ) -> Dict[str, Any]:
        """Create a new folder"""
        try:
            folder_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": name,
                "description": description,
                "parent_folder_id": parent_folder_id,
                "color": color,
                "icon": icon
            }
            
            result = self.db.table("document_folders").insert(folder_data).execute()
            
            if result.data:
                return {"success": True, "folder": result.data[0]}
            else:
                return {"success": False, "error": "Failed to create folder"}
                
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_storage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's storage statistics"""
        try:
            result = self.db.rpc("get_user_storage_stats", {"user_id": user_id}).execute()
            
            if result.data:
                stats = result.data[0]
                return {
                    "success": True,
                    "stats": {
                        "total_documents": stats["total_documents"],
                        "total_size_bytes": stats["total_size_bytes"],
                        "storage_used_mb": float(stats["storage_used_mb"]),
                        "documents_by_type": stats["documents_by_type"],
                        "storage_limit_mb": 1000,  # 1GB limit
                        "storage_used_percentage": min(100, (float(stats["storage_used_mb"]) / 1000) * 100)
                    }
                }
            else:
                return {"success": False, "error": "Failed to get storage stats"}
                
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_system_folders(self, user_id: str) -> Dict[str, Any]:
        """Create system folders for new user"""
        try:
            self.db.rpc("create_system_folders_for_user", {"user_id": user_id}).execute()
            return {"success": True, "message": "System folders created"}
            
        except Exception as e:
            logger.error(f"Failed to create system folders: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        path = Path(file_path)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return {
            "name": path.name,
            "size": path.stat().st_size,
            "hash": file_hash,
            "mime_type": mime_type or "application/octet-stream"
        }
    
    async def _check_duplicate(self, user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check for duplicate files"""
        try:
            result = self.db.table("document_vault").select("id, title").eq("user_id", user_id).eq("file_hash", file_hash).eq("status", "active").execute()
            
            return result.data[0] if result.data else None
            
        except Exception:
            return None
    
    async def _get_default_folder(self, user_id: str, document_type: str) -> Optional[str]:
        """Get default folder for document type"""
        try:
            folder_mapping = {
                "cv": "CVs",
                "cover_letter": "Cover Letters",
                "certificate": "Certificates",
                "portfolio": "Portfolio"
            }
            
            folder_name = folder_mapping.get(document_type, "CVs")
            
            result = self.db.table("document_folders").select("id").eq("user_id", user_id).eq("name", folder_name).eq("is_system_folder", True).execute()
            
            return result.data[0]["id"] if result.data else None
            
        except Exception:
            return None
    
    async def _log_access(self, document_id: str, access_type: str, user_id: Optional[str] = None):
        """Log document access"""
        try:
            self.db.rpc("log_document_access", {
                "doc_id": document_id,
                "access_type": access_type,
                "user_id": user_id
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log access: {e}")
    
    def _generate_share_token(self) -> str:
        """Generate secure share token"""
        return hashlib.sha256(str(uuid4()).encode()).hexdigest()[:32]


# Global service instance
def get_document_vault_service(db: Client) -> DocumentVaultService:
    return DocumentVaultService(db)