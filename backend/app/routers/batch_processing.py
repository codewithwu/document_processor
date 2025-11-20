from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import uuid
from datetime import datetime

from ..core.database import get_db
from ..models import Document
from ..schemas.document import DocumentResponse
from ..services.file_service import FileService
from ..celery_worker import extract_pdf_text_task

router = APIRouter(prefix="/batch", tags=["batch-processing"])

@router.post("/upload/pdfs", response_model=List[DocumentResponse])
async def upload_multiple_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    批量上传多个PDF文件
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个PDF文件")
    
    # 验证文件数量
    if len(files) > 20:  # 限制一次最多上传20个文件
        raise HTTPException(status_code=400, detail="一次最多上传20个PDF文件")
    
    uploaded_documents = []
    errors = []
    
    for file in files:
        try:
            # 验证文件类型
            if not file.filename.lower().endswith('.pdf'):
                errors.append(f"文件 {file.filename} 不是PDF格式")
                continue
            
            # 验证并保存文件
            file_path, unique_filename = await FileService.save_upload_file(file, "pdf")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 创建文档记录
            db_document = Document(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                mime_type="application/pdf",
                upload_type="pdf",
                extraction_status="pending"
            )
            
            db.add(db_document)
            uploaded_documents.append(db_document)
            
        except Exception as e:
            errors.append(f"文件 {file.filename} 上传失败: {str(e)}")
            continue
    
    # 提交所有文档到数据库
    if uploaded_documents:
        db.commit()
        
        # 刷新所有文档以获取ID
        for doc in uploaded_documents:
            db.refresh(doc)
            
        # 为每个文档启动文本提取任务
        for doc in uploaded_documents:
            extract_pdf_text_task.delay(doc.id)
    
    # 如果有错误，返回错误信息
    if errors:
        raise HTTPException(
            status_code=207,  # Multi-Status
            detail={
                "message": "部分文件处理完成，部分文件处理失败",
                "success_count": len(uploaded_documents),
                "error_count": len(errors),
                "errors": errors,
                "documents": uploaded_documents
            }
        )
    
    return uploaded_documents

@router.post("/process/documents")
async def batch_process_documents(
    document_ids: List[int] = None,
    db: Session = Depends(get_db)
):
    """
    批量处理已上传的文档
    """
    if not document_ids:
        raise HTTPException(status_code=400, detail="请提供文档ID列表")
    
    if len(document_ids) > 50:
        raise HTTPException(status_code=400, detail="一次最多处理50个文档")
    
    # 查询文档
    documents = db.query(Document).filter(
        Document.id.in_(document_ids),
        Document.upload_type == "pdf"
    ).all()
    
    if not documents:
        raise HTTPException(status_code=404, detail="未找到指定的PDF文档")
    
    # 检查文档状态
    processed_docs = []
    skipped_docs = []
    
    for doc in documents:
        if doc.extraction_status in ['pending', 'failed']:
            # 重置状态并启动任务
            doc.extraction_status = 'pending'
            doc.extraction_error = None
            extract_pdf_text_task.delay(doc.id)
            processed_docs.append({
                "id": doc.id,
                "filename": doc.original_filename,
                "status": "processing_started"
            })
        else:
            skipped_docs.append({
                "id": doc.id,
                "filename": doc.original_filename,
                "current_status": doc.extraction_status,
                "reason": "文档已在处理中或已完成"
            })
    
    db.commit()
    
    return {
        "message": "批量处理任务已启动",
        "total_documents": len(documents),
        "processed": len(processed_docs),
        "skipped": len(skipped_docs),
        "processed_documents": processed_docs,
        "skipped_documents": skipped_docs
    }

@router.get("/process/status")
async def get_batch_process_status(
    task_ids: List[str] = None,
    document_ids: List[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取批量处理状态
    """
    from ..models import ProcessingTask
    
    if not task_ids and not document_ids:
        raise HTTPException(status_code=400, detail="请提供任务ID列表或文档ID列表")
    
    result = {}
    
    # 通过文档ID查询任务状态
    if document_ids:
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        result["documents"] = []
        
        for doc in documents:
            # 获取文档的最新任务
            latest_task = db.query(ProcessingTask).filter(
                ProcessingTask.document_id == doc.id
            ).order_by(ProcessingTask.created_at.desc()).first()
            
            doc_info = {
                "document_id": doc.id,
                "filename": doc.original_filename,
                "document_status": doc.extraction_status,
                "text_length": doc.text_length,
                "page_count": doc.page_count,
                "error": doc.extraction_error
            }
            
            if latest_task:
                doc_info.update({
                    "task_id": latest_task.task_id,
                    "task_status": latest_task.status,
                    "task_type": latest_task.task_type,
                    "started_at": latest_task.started_at,
                    "completed_at": latest_task.completed_at
                })
            
            result["documents"].append(doc_info)
    
    # 通过任务ID查询状态
    if task_ids:
        tasks = db.query(ProcessingTask).filter(ProcessingTask.task_id.in_(task_ids)).all()
        result["tasks"] = []
        
        for task in tasks:
            # 获取关联的文档信息
            document = db.query(Document).filter(Document.id == task.document_id).first()
            
            task_info = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "task_status": task.status,
                "document_id": task.document_id,
                "document_filename": document.original_filename if document else "Unknown",
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message
            }
            
            result["tasks"].append(task_info)
    
    return result

@router.post("/process/all-pending")
async def process_all_pending_documents(
    db: Session = Depends(get_db)
):
    """
    处理所有状态为pending或failed的PDF文档
    """
    # 查询所有需要处理的文档
    pending_documents = db.query(Document).filter(
        Document.upload_type == "pdf",
        Document.extraction_status.in_(['pending', 'failed'])
    ).all()
    
    if not pending_documents:
        return {
            "message": "没有需要处理的文档",
            "processed_count": 0
        }
    
    processed_count = 0
    
    for doc in pending_documents:
        try:
            # 重置状态并启动任务
            doc.extraction_status = 'pending'
            doc.extraction_error = None
            extract_pdf_text_task.delay(doc.id)
            processed_count += 1
        except Exception as e:
            # 记录错误但继续处理其他文档
            doc.extraction_error = f"重新启动任务失败: {str(e)}"
            continue
    
    db.commit()
    
    return {
        "message": f"已启动 {processed_count} 个文档的处理任务",
        "total_pending": len(pending_documents),
        "processed_count": processed_count,
        "document_ids": [doc.id for doc in pending_documents]
    }