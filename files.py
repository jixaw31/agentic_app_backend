import os, uuid, shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
from models import FileMeta
from datetime import datetime

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

# in memory DB
files_db: Dict[str, FileMeta] = {}

@router.post("/{conversation_id}/upload", response_model=FileMeta, description="To upload files")
async def upload_file(conversation_id: str, uploaded_file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{uploaded_file.filename}")
    
    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    meta = FileMeta(
        id=file_id,
        conversation_id=conversation_id,
        filename=uploaded_file.filename,
        content_type=uploaded_file.content_type,
        size=os.path.getsize(file_path)
    )
    files_db[file_id] = meta
    return meta

@router.get("/{conversation_id}/files", response_model=List[FileMeta],
            description="To get all files associated with a conversation.")
def list_files_for_conversation(conversation_id: str):
    return [f for f in files_db.values() if f.conversation_id == conversation_id]

@router.get("/file/{file_id}", response_model=FileMeta,
            description="To grab a file by its ID.")
def get_file_metadata(file_id: str):
    meta = files_db.get(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    return meta
