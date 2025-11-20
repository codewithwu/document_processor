import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DATABASE_User = os.getenv("DATABASE_User")
DATABASE_Password = os.getenv("DATABASE_Password")
DATABASE_Host = os.getenv("DATABASE_Host")
DATABASE_Port = os.getenv("DATABASE_Port")
DATABASE_Name = os.getenv("DATABASE_Name")

RedisHost = os.getenv("RedisHost")
RedisPassword = os.getenv("RedisPassword")
RedisPort = os.getenv("RedisPort")
RedisDB = os.getenv("RedisDB")

class Settings:
    """应用配置"""
    
    # 数据库配置
    DATABASE_URL: str = f"postgresql://{DATABASE_User}:{DATABASE_Password}@{DATABASE_Host}:{int(DATABASE_Port)}/{DATABASE_Name}"
    
    # Redis配置
    REDIS_URL: str = f"redis://:{RedisPassword}@{RedisHost}:{RedisPort}/{RedisDB}"
    
    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    
    # Celery配置
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

settings = Settings()