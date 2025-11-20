import fitz  # PyMuPDF
import pdfplumber
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PDFService:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
        """
        从PDF文件中提取文本
        
        策略：
        1. 首先使用PyMuPDF（快速，适合大部分PDF）
        2. 如果提取的文本很少，尝试使用pdfplumber（更适合复杂布局）
        3. 如果还是失败，考虑使用OCR（后续实现）
        """
        file_path = f"{file_path}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF文件不存在: {file_path}")
        
        # 方法1: 使用PyMuPDF提取文本
        text_pymupdf, page_count_pymupdf = PDFService._extract_with_pymupdf(file_path)
        
        # 如果PyMuPDF提取的文本质量较好（超过100字符），直接返回
        if len(text_pymupdf.strip()) > 100:
            return {
                "text": text_pymupdf,
                "text_length": len(text_pymupdf),
                "page_count": page_count_pymupdf,
                "method": "pymupdf"
            }
        
        # 方法2: 使用pdfplumber提取文本（更适合复杂布局）
        text_pdfplumber, page_count_pdfplumber = PDFService._extract_with_pdfplumber(file_path)
        
        # 选择文本内容更多的结果
        if len(text_pdfplumber) > len(text_pymupdf):
            return {
                "text": text_pdfplumber,
                "text_length": len(text_pdfplumber),
                "page_count": page_count_pdfplumber,
                "method": "pdfplumber"
            }
        else:
            return {
                "text": text_pymupdf,
                "text_length": len(text_pymupdf),
                "page_count": page_count_pymupdf,
                "method": "pymupdf"
            }
    
    @staticmethod
    def _extract_with_pymupdf(file_path: str) -> tuple[str, int]:
        """使用PyMuPDF提取文本"""
        text = ""
        page_count = 0
        
        try:
            with fitz.open(file_path) as doc:
                page_count = len(doc)
                for page_num in range(page_count):
                    page = doc[page_num]
                    page_text = page.get_text()
                    text += f"\n--- 第 {page_num + 1} 页 ---\n{page_text}"
            
            logger.info(f"PyMuPDF提取完成: {len(text)} 字符, {page_count} 页")
            return text, page_count
            
        except Exception as e:
            logger.error(f"PyMuPDF提取失败: {str(e)}")
            return "", 0
    
    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> tuple[str, int]:
        """使用pdfplumber提取文本"""
        text = ""
        page_count = 0
        
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    text += f"\n--- 第 {page_num + 1} 页 ---\n{page_text}"
            
            logger.info(f"pdfplumber提取完成: {len(text)} 字符, {page_count} 页")
            return text, page_count
            
        except Exception as e:
            logger.error(f"pdfplumber提取失败: {str(e)}")
            return "", 0
    
    @staticmethod
    def get_pdf_info(file_path: str) -> Dict[str, Any]:
        """获取PDF文件基本信息"""
        try:
            with fitz.open(file_path) as doc:
                return {
                    "page_count": len(doc),
                    "is_encrypted": doc.is_encrypted,
                    "metadata": doc.metadata
                }
        except Exception as e:
            logger.error(f"获取PDF信息失败: {str(e)}")
            return {}

# 创建服务实例
pdf_service = PDFService()