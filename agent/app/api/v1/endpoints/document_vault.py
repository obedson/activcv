 """
Document vault API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse, RedirectResponse
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.document_vault import get_document_vault_service, DocumentVaultService

router = APIRouter()


@router.get("/")
async def get_documents(
    current_user: str = Depends(get_current_user),
    document_type: Optional[str] = Query(None),
    folder_id: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Get user's documents with filtering"""
    try:
        result = await vault_service.get_documents(
            user_id=current_user,
            document_type=document_type,
            folder_id=folder_id,
            search_query=search_query,
            limit=limit,
            offset=offset
        )
        
        if result["success"]:
            return result["documents"]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Get specific document"""
    try:
        document = await vault_service.get_document(document_id, current_user)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Download document file"""
    try:
        document = await vault_service.get_document(document_id, current_user)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Log download access
        await vault_service._log_access(document_id, "download", current_user)
        
        # Return file or redirect to signed URL
        if document.get("file_url"):
            return RedirectResponse(url=document["file_url"])
        elif document.get("file_path"):
            return FileResponse(
                path=document["file_path"],
                filename=document["file_name"],
                media_type=document.get("mime_type", "application/octet-stream")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download document: {str(e)}"
        )


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    updates: dict,
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Update document metadata"""
    try:
        result = await vault_service.update_document(document_id, current_user, updates)
        
        if result["success"]:
            return result["document"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    permanent: bool = Query(False),
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Delete or archive document"""
    try:
        result = await vault_service.delete_document(document_id, current_user, permanent)
        
        if result["success"]:
            return {"message": result["message"]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/{document_id}/share")
async def create_share_link(
    document_id: str,
    share_request: dict,
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Create shareable link for document"""
    try:
        result = await vault_service.create_share_link(
            document_id=document_id,
            user_id=current_user,
            permissions=share_request.get("permissions", ["view"]),
            expires_in_days=share_request.get("expires_in_days"),
            shared_with_email=share_request.get("shared_with_email")
        )
        
        if result["success"]:
            return {
                "share_url": result["share_url"],
                "share_token": result["share_token"],
                "expires_at": result["share_info"].get("expires_at")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}"
        )


@router.get("/shared/{share_token}")
async def get_shared_document(
    share_token: str,
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Access shared document"""
    try:
        document = await vault_service.get_shared_document(share_token)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared document not found or expired"
            )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to access shared document: {str(e)}"
        )


@router.get("/shared/{share_token}/download")
async def download_shared_document(
    share_token: str,
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Download shared document"""
    try:
        document = await vault_service.get_shared_document(share_token)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared document not found or expired"
            )
        
        # Check download permission
        permissions = document.get("share_permissions", [])
        if "download" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download not permitted for this share"
            )
        
        # Log download access
        await vault_service._log_access(document["id"], "download")
        
        # Return file or redirect to signed URL
        if document.get("file_url"):
            return RedirectResponse(url=document["file_url"])
        elif document.get("file_path"):
            return FileResponse(
                path=document["file_path"],
                filename=document["file_name"],
                media_type=document.get("mime_type", "application/octet-stream")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download shared document: {str(e)}"
        )


@router.get("/folders/")
async def get_folders(
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Get user's document folders"""
    try:
        folders = await vault_service.get_folders(current_user)
        return folders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve folders: {str(e)}"
        )


@router.post("/folders/")
async def create_folder(
    folder_data: dict,
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Create new folder"""
    try:
        result = await vault_service.create_folder(
            user_id=current_user,
            name=folder_data["name"],
            description=folder_data.get("description"),
            parent_folder_id=folder_data.get("parent_folder_id"),
            color=folder_data.get("color", "#3B82F6"),
            icon=folder_data.get("icon", "folder")
        )
        
        if result["success"]:
            return result["folder"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create folder: {str(e)}"
        )


@router.get("/storage-stats")
async def get_storage_stats(
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Get user's storage statistics"""
    try:
        result = await vault_service.get_storage_stats(current_user)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage stats: {str(e)}"
        )


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query(...),
    title: str = Query(...),
    description: Optional[str] = Query(None),
    folder_id: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user),
    vault_service: DocumentVaultService = Depends(get_document_vault_service)
):
    """Upload document directly to vault"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Store in vault
            result = await vault_service.store_document(
                user_id=current_user,
                file_path=temp_file_path,
                document_type=document_type,
                title=title,
                description=description,
                folder_id=folder_id
            )
            
            if result["success"]:
                return result["document"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
        
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )