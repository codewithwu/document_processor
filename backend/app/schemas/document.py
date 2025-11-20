from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    upload_type: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    extraction_status: str
    text_length: Optional[int] = 0
    page_count: int = 1
    is_used: bool = False  # 新增使用状态字段
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    task_id: str
    status: str
    document_id: int
    task_type: str
    
    class Config:
        from_attributes = True

# 新增：更新使用状态的请求模型
class DocumentUsageUpdate(BaseModel):
    is_used: bool

# 新增：批量更新使用状态的请求模型
class BatchDocumentUsageUpdate(BaseModel):
    document_ids: list[int]
    is_used: bool