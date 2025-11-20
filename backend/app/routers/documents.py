from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import os

from ..core.database import get_db
from ..models import Document
from ..schemas.document import DocumentResponse
from ..services.file_service import FileService
from ..celery_worker import extract_pdf_text_task

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload/pdf", response_model=DocumentResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传PDF文件并启动文本提取"""
    
    # 验证并保存文件
    file_path, unique_filename = await FileService.save_upload_file(file, "pdf")
    
    # 获取文件大小
    file_size = os.path.getsize(file_path)
    
    # 创建文档记录 - 默认 is_used=False
    db_document = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        upload_type="pdf",
        extraction_status="pending",
        is_used=False  # 新增文档默认为未使用
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # 启动后台任务进行文本提取
    extract_pdf_text_task.delay(db_document.id)
    
    return db_document

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """获取文档信息"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document

@router.get("/{document_id}/text")
def get_document_text(document_id: int, db: Session = Depends(get_db)):
    """获取文档提取的文本内容"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.extraction_status == "pending":
        raise HTTPException(status_code=425, detail="文本提取中，请稍后重试")
    elif document.extraction_status == "processing":
        raise HTTPException(status_code=425, detail="文本提取处理中")
    elif document.extraction_status == "failed":
        raise HTTPException(
            status_code=500, 
            detail=f"文本提取失败: {document.extraction_error}"
        )
    elif document.extraction_status == "completed":
        return {
            "document_id": document_id,
            "text": document.extracted_text,
            "text_length": document.text_length,
            "page_count": document.page_count
        }
    
    raise HTTPException(status_code=500, detail="未知状态")

@router.get("/{document_id}/tasks")
def get_document_tasks(document_id: int, db: Session = Depends(get_db)):
    """获取文档相关的任务状态"""
    from ..models import ProcessingTask
    
    tasks = db.query(ProcessingTask).filter(
        ProcessingTask.document_id == document_id
    ).order_by(ProcessingTask.created_at.desc()).all()
    
    return tasks

# 新增：更新文档使用状态接口
@router.patch("/{document_id}/usage")
def update_document_usage(
    document_id: int,
    is_used: bool,
    db: Session = Depends(get_db)
):
    """更新文档使用状态"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document.is_used = is_used
    db.commit()
    db.refresh(document)
    
    return {
        "message": f"文档使用状态已更新为 {'已使用' if is_used else '未使用'}",
        "document_id": document_id,
        "is_used": is_used
    }

# 新增：批量更新文档使用状态
@router.post("/batch/update-usage")
def batch_update_document_usage(
    document_ids: list[int],
    is_used: bool,
    db: Session = Depends(get_db)
):
    """批量更新文档使用状态"""
    if not document_ids:
        raise HTTPException(status_code=400, detail="请提供文档ID列表")
    
    # 查询文档
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
    
    if not documents:
        raise HTTPException(status_code=404, detail="未找到指定的文档")
    
    updated_count = 0
    for document in documents:
        document.is_used = is_used
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"成功更新 {updated_count} 个文档的使用状态为 {'已使用' if is_used else '未使用'}",
        "updated_count": updated_count,
        "is_used": is_used
    }