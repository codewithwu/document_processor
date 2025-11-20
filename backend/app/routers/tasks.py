from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import ProcessingTask
from ..schemas.document import TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态"""
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task

@router.get("/")
def list_tasks(
    skip: int = 0,
    limit: int = 20,
    task_type: str = None,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    query = db.query(ProcessingTask)
    
    if task_type:
        query = query.filter(ProcessingTask.task_type == task_type)
    
    tasks = query.order_by(ProcessingTask.created_at.desc()).offset(skip).limit(limit).all()
    return tasks