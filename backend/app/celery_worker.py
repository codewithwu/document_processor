from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from .core.config import settings
from .core.database import SessionLocal

# 配置日志
logger = logging.getLogger(__name__)

# 创建Celery应用
celery_app = Celery(
    "document_processor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
)

@celery_app.task(bind=True, name="extract_pdf_text")
def extract_pdf_text_task(self, document_id: int):
    """提取PDF文本的Celery任务"""
    db = SessionLocal()
    try:
        from .models import Document, ProcessingTask
        
        logger.info(f"开始处理PDF文本提取任务，文档ID: {document_id}")
        
        # 更新任务状态
        task = ProcessingTask(
            task_id=self.request.id,
            task_type="pdf_extraction",
            status="processing",
            document_id=document_id,
            started_at=datetime.now()
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"文档 {document_id} 不存在")
        
        logger.info(f"找到文档: {document.filename}")
        
        # 更新文档状态
        document.extraction_status = "processing"
        db.commit()
        
        # 导入PDF服务
        from .services.pdf_service import pdf_service
        
        # 执行文本提取
        logger.info(f"开始提取PDF文本: {document.file_path}")
        result = pdf_service.extract_text_from_pdf(document.file_path)
        
        logger.info(f"文本提取完成: {result['text_length']} 字符, {result['page_count']} 页")
        
        # 更新文档内容
        document.extracted_text = result["text"]
        document.text_length = result["text_length"]
        document.page_count = result["page_count"]
        document.extraction_status = "completed"
        
        # 更新任务状态
        task.status = "success"
        task.result = {
            "text_length": result["text_length"],
            "page_count": result["page_count"],
            "extraction_method": result["method"]
        }
        task.completed_at = datetime.now()
        
        db.commit()
        
        logger.info(f"PDF文本提取任务完成: 文档 {document_id}")
        
        return {
            "document_id": document_id,
            "text_length": result["text_length"],
            "page_count": result["page_count"],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"PDF文本提取任务失败: {str(e)}")
        db.rollback()
        
        try:
            # 更新文档状态
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.extraction_status = "failed"
                document.extraction_error = str(e)
                db.commit()
            
            # 更新任务状态
            task = db.query(ProcessingTask).filter(ProcessingTask.task_id == self.request.id).first()
            if task:
                task.status = "failure"
                task.error_message = str(e)
                task.completed_at = datetime.now()
                db.commit()
        except Exception as update_error:
            logger.error(f"更新失败状态时出错: {str(update_error)}")
        
        # 重试逻辑：只有特定错误才重试
        if "文件不存在" in str(e) or "无法读取" in str(e):
            raise e  # 不重试文件错误
        
        # 其他错误重试
        retry_count = self.request.retries
        if retry_count < 3:
            wait_time = 60 * (retry_count + 1)  # 60s, 120s, 180s
            logger.info(f"任务将在 {wait_time} 秒后重试 (第 {retry_count + 1} 次)")
            raise self.retry(exc=e, countdown=wait_time, max_retries=3)
        else:
            logger.error(f"任务重试次数已达上限，最终失败: {str(e)}")
            raise e
    
    finally:
        db.close()

# 移除图片合成PDF的任务