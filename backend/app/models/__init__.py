from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

class Document(Base):
    """文档模型"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # 文件大小（字节）
    mime_type = Column(String(100))
    
    # 文本提取相关字段
    extracted_text = Column(Text)  # 提取的文本内容
    text_length = Column(Integer, default=0)  # 文本长度
    extraction_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    extraction_error = Column(Text)  # 错误信息
    
    # 元数据
    upload_type = Column(String(10))  # 'pdf' 或 'image'
    page_count = Column(Integer, default=1)  # 页数（PDF）或图片数量

    # 新增：使用状态字段
    is_used = Column(Boolean, default=False, nullable=False)  # 是否已使用
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ProcessingTask(Base):
    """任务队列模型"""
    __tablename__ = "processing_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True)  # Celery任务ID
    task_type = Column(String(50))  # 'pdf_extraction', 'pdf_generation'
    status = Column(String(20), default='pending')  # pending, processing, success, failure
    document_id = Column(Integer)  # 关联的文档ID
    
    # 任务参数和结果
    parameters = Column(JSON)  # 任务参数
    result = Column(JSON)  # 任务结果
    error_message = Column(Text)  # 错误信息
    
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())