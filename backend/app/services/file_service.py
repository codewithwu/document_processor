import os
import uuid
from fastapi import UploadFile, HTTPException
import magic
from ..core.config import settings

class FileService:
    @staticmethod
    def validate_file(file: UploadFile):
        """验证上传文件"""
        # 检查文件大小
        if hasattr(file, 'size') and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"文件大小不能超过 {settings.MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        
        # 检查文件扩展名
        file_extension = os.path.splitext(file.filename.lower())[1]
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。允许的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        return file_extension
    
    @staticmethod
    async def save_upload_file(file: UploadFile, upload_type: str) -> tuple[str, str]:
        """保存上传文件并返回文件路径和唯一文件名"""
        
        file_extension = FileService.validate_file(file)
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # 创建类型特定的目录
        type_dir = os.path.join(settings.UPLOAD_DIR, upload_type)
        os.makedirs(type_dir, exist_ok=True)
        
        file_path = os.path.join(type_dir, unique_filename)
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path, unique_filename
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """检测文件真实类型"""
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        return file_type