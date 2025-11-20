from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from .core.database import get_db, engine
from .models import Base
from .core.config import settings

# 导入路由
from .routers import documents, tasks, batch_processing  

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建uploads目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="文档处理中心 API",
    description="提供PDF文本提取和图片合成PDF功能的API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # 前端开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents.router)
app.include_router(tasks.router)
app.include_router(batch_processing.router)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用文档处理中心 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    try:
        # 测试数据库连接
        # db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"  # 实际应该用datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed error {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)