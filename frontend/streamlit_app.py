import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
from typing import List, Dict, Any

# 页面配置
st.set_page_config(
    page_title="PDF文本提取工具",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API配置
API_BASE_URL = "http://localhost:8000"

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #4F4F4F;
        margin-bottom: 1rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .success-card {
        border-left: 4px solid #28a745;
    }
    .processing-card {
        border-left: 4px solid #ffc107;
    }
    .error-card {
        border-left: 4px solid #dc3545;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-completed {
        background-color: #d4edda;
        color: #155724;
    }
    .status-processing {
        background-color: #fff3cd;
        color: #856404;
    }
    .status-failed {
        background-color: #f8d7da;
        color: #721c24;
    }
    .status-pending {
        background-color: #e2e3e5;
        color: #383d41;
    }
    .text-content {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #dee2e6;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: 'Courier New', monospace;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class DocumentProcessorAPI:
    """API客户端类"""
    
    @staticmethod
    def health_check():
        """健康检查"""
        try:
            response = requests.get(f"{API_BASE_URL}/health")
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def upload_pdf(file) -> Dict[str, Any]:
        """上传PDF文件"""
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        response = requests.post(f"{API_BASE_URL}/documents/upload/pdf", files=files)
        return response.json()
    
    @staticmethod
    def upload_multiple_pdfs(files: List) -> Dict[str, Any]:
        """批量上传多个PDF文件"""
        file_list = [("files", (file.name, file.getvalue(), "application/pdf")) for file in files]
        response = requests.post(f"{API_BASE_URL}/batch/upload/pdfs", files=file_list)
        return response.json()
    
    @staticmethod
    def batch_process_documents(document_ids: List[int]) -> Dict[str, Any]:
        """批量处理文档"""
        response = requests.post(
            f"{API_BASE_URL}/batch/process/documents", 
            json={"document_ids": document_ids}
        )
        return response.json()
    
    @staticmethod
    def process_all_pending() -> Dict[str, Any]:
        """处理所有待处理文档"""
        response = requests.post(f"{API_BASE_URL}/batch/process/all-pending")
        return response.json()
    
    @staticmethod
    def get_document(document_id: int) -> Dict[str, Any]:
        """获取文档信息"""
        try:
            response = requests.get(f"{API_BASE_URL}/documents/{document_id}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_document_text(document_id: int) -> Dict[str, Any]:
        """获取文档文本"""
        try:
            response = requests.get(f"{API_BASE_URL}/documents/{document_id}/text")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API返回错误: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_document_tasks(document_id: int) -> List[Dict[str, Any]]:
        """获取文档任务"""
        try:
            response = requests.get(f"{API_BASE_URL}/documents/{document_id}/tasks")
            return response.json()
        except:
            return []
    
    @staticmethod
    def update_document_usage(document_id: int, is_used: bool) -> Dict[str, Any]:
        """更新文档使用状态"""
        response = requests.patch(
            f"{API_BASE_URL}/documents/{document_id}/usage",
            params={"is_used": is_used}
        )
        return response.json()
    
    @staticmethod
    def batch_update_document_usage(document_ids: List[int], is_used: bool) -> Dict[str, Any]:
        """批量更新文档使用状态"""
        response = requests.post(
            f"{API_BASE_URL}/documents/batch/update-usage",
            json={"document_ids": document_ids, "is_used": is_used}
        )
        return response.json()

def init_session_state():
    """初始化会话状态"""
    if 'documents' not in st.session_state:
        st.session_state.documents = []
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

def refresh_documents_status():
    """刷新文档状态"""
    try:
        for i, doc in enumerate(st.session_state.documents):
            if doc.get('extraction_status') in ['pending', 'processing']:
                updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                if 'error' not in updated_doc:
                    st.session_state.documents[i] = updated_doc
        
        st.session_state.last_refresh = datetime.now()
    except Exception as e:
        st.error(f"刷新状态时出错: {str(e)}")

def render_header():
    """渲染页面头部"""
    st.markdown('<h1 class="main-header">📄 PDF文本提取工具</h1>', unsafe_allow_html=True)
    
    # 状态指示器
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if DocumentProcessorAPI.health_check():
            st.success("✅ API服务正常")
        else:
            st.error("❌ API服务异常")
    
    with col2:
        st.info(f"📊 总文档数: {len(st.session_state.documents)}")
    
    with col3:
        completed_count = len([d for d in st.session_state.documents if d.get('extraction_status') == 'completed'])
        st.info(f"✅ 已完成: {completed_count}")
    
    with col4:
        # 自动刷新开关
        auto_refresh = st.checkbox("🔄 自动刷新", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            st.rerun()

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🎯 功能导航")
        
        selected_tab = st.radio(
            "选择功能",
            ["单文件提取", "批量处理", "文档管理", "使用说明"]
        )
        
        st.markdown("---")
        st.markdown("## 📊 系统信息")
        st.markdown("**版本**: v1.2.0")  # 更新版本号
        st.markdown("**后端**: FastAPI + Celery")
        st.markdown("**数据库**: PostgreSQL")
        st.markdown("**功能**: PDF文本提取 + 使用状态管理")
        
        # 手动刷新按钮
        if st.button("🔄 手动刷新状态"):
            refresh_documents_status()
            st.success("状态已刷新！")
        
        # 显示最后刷新时间
        if st.session_state.last_refresh:
            st.markdown(f"**最后刷新**: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        return selected_tab

def render_single_file_tab():
    """渲染单文件提取标签页"""
    st.markdown('<div class="sub-header">📄 单文件文本提取</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 上传PDF文件")
        uploaded_file = st.file_uploader(
            "选择PDF文件",
            type=['pdf'],
            key="pdf_uploader"
        )
        
        if uploaded_file is not None:
            # 显示文件信息
            file_size = len(uploaded_file.getvalue()) / 1024  # KB
            st.info(f"**文件信息**: {uploaded_file.name} ({file_size:.1f} KB)")
            
            if st.button("🚀 开始文本提取", type="primary", use_container_width=True):
                with st.spinner("正在上传并处理PDF文件..."):
                    try:
                        result = DocumentProcessorAPI.upload_pdf(uploaded_file)
                        st.session_state.documents.append(result)
                        
                        # 显示成功信息
                        st.success("✅ PDF上传成功！文本提取任务已启动")
                        
                        # 立即显示文档卡片
                        render_document_card(result)
                        
                        # 启动状态监控
                        monitor_pdf_task_status(result['id'])
                        
                    except Exception as e:
                        st.error(f"❌ 上传失败: {str(e)}")
    
    with col2:
        st.markdown("### 使用说明")
        st.markdown("""
        **功能说明**:
        - 上传单个PDF文件自动提取文本内容
        - 支持文字版和扫描版PDF
        - 文本提取在后台异步进行
        
        **支持格式**:
        - 📄 PDF文档 (.pdf)
        
        **限制**:
        - 文件大小: ≤ 50MB
        - 支持中文和英文文本提取
        - 自动处理多页文档
        """)

def render_batch_processing_tab():
    """渲染批量处理标签页"""
    st.markdown('<div class="sub-header">📚 批量PDF处理</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📤 批量上传", "🔄 批量处理"])
    
    with tab1:
        render_batch_upload_tab()
    
    with tab2:
        render_batch_process_tab()

def render_batch_upload_tab():
    """批量上传标签页"""
    st.markdown("### 批量上传PDF文件")
    
    uploaded_files = st.file_uploader(
        "选择多个PDF文件（最多20个）",
        type=['pdf'],
        accept_multiple_files=True,
        key="batch_pdf_uploader"
    )
    
    if uploaded_files:
        st.success(f"✅ 已选择 {len(uploaded_files)} 个PDF文件")
        
        # 显示文件列表
        for i, file in enumerate(uploaded_files):
            file_size = len(file.getvalue()) / 1024
            st.info(f"**文件 {i+1}**: {file.name} ({file_size:.1f} KB)")
        
        if st.button("🚀 开始批量上传和处理", type="primary", use_container_width=True):
            with st.spinner("正在批量上传和处理PDF文件..."):
                try:
                    result = DocumentProcessorAPI.upload_multiple_pdfs(uploaded_files)
                    
                    if 'documents' in result:
                        # 正常响应
                        st.session_state.documents.extend(result['documents'])
                        st.success(f"✅ 成功上传 {len(result['documents'])} 个PDF文件！文本提取任务已启动")
                        
                        # 显示处理中的文档
                        for doc in result['documents']:
                            render_document_card(doc)
                            
                    elif 'detail' in result and result['detail'].get('documents'):
                        # 部分成功响应
                        detail = result['detail']
                        st.warning(f"⚠️ 部分文件处理完成: 成功 {detail['success_count']} 个, 失败 {detail['error_count']} 个")
                        
                        st.session_state.documents.extend(detail['documents'])
                        for doc in detail['documents']:
                            render_document_card(doc)
                        
                        # 显示错误信息
                        if detail['errors']:
                            st.error("处理失败的文件:")
                            for error in detail['errors']:
                                st.error(f"❌ {error}")
                    else:
                        # 直接返回文档列表
                        st.session_state.documents.extend(result)
                        st.success(f"✅ 成功上传 {len(result)} 个PDF文件！文本提取任务已启动")
                        for doc in result:
                            render_document_card(doc)
                    
                except Exception as e:
                    st.error(f"❌ 批量上传失败: {str(e)}")

def render_batch_process_tab():
    """批量处理标签页"""
    st.markdown("### 批量处理已上传的PDF文档")
    
    # 获取所有PDF文档
    pdf_documents = st.session_state.documents
    
    if not pdf_documents:
        st.info("📝 暂无PDF文档，请先上传PDF文件")
        return
    
    # 显示统计信息
    st.markdown("#### 文档统计")
    status_count = {}
    for doc in pdf_documents:
        status = doc.get('extraction_status', 'unknown')
        status_count[status] = status_count.get(status, 0) + 1
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总文档数", len(pdf_documents))
    with col2:
        st.metric("已完成", status_count.get('completed', 0))
    with col3:
        st.metric("处理中", status_count.get('processing', 0) + status_count.get('pending', 0))
    with col4:
        st.metric("失败", status_count.get('failed', 0))
    
    # 文档选择
    st.markdown("#### 选择要处理的文档")
    
    selected_docs = []
    for doc in pdf_documents:
        col1, col2, col3 = st.columns([1, 3, 2])
        with col1:
            # 默认选择待处理和失败的文档
            default_value = doc.get('extraction_status') in ['pending', 'failed']
            selected = st.checkbox("选择文档", key=f"batch_{doc['id']}", value=default_value)
        with col2:
            st.text(f"{doc['original_filename']}")
        with col3:
            status = doc.get('extraction_status', 'unknown')
            status_text = {
                'completed': '✅ 已完成',
                'processing': '🔄 处理中', 
                'failed': '❌ 失败',
                'pending': '⏳ 等待中'
            }.get(status, status)
            st.text(f"状态: {status_text}")
        
        if selected:
            selected_docs.append(doc['id'])
    
    if selected_docs:
        st.info(f"已选择 {len(selected_docs)} 个文档进行处理")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 开始批量处理", type="primary", use_container_width=True):
                with st.spinner("正在启动批量处理任务..."):
                    try:
                        result = DocumentProcessorAPI.batch_process_documents(selected_docs)
                        st.success(f"✅ {result['message']}")
                        st.info(f"处理中: {result['processed']} 个, 跳过: {result['skipped']} 个")
                        
                    except Exception as e:
                        st.error(f"❌ 批量处理失败: {str(e)}")
        
        with col2:
            if st.button("🔄 处理所有待处理文档", use_container_width=True):
                with st.spinner("正在处理所有待处理文档..."):
                    try:
                        result = DocumentProcessorAPI.process_all_pending()
                        st.success(f"✅ {result['message']}")
                    except Exception as e:
                        st.error(f"❌ 处理失败: {str(e)}")
    else:
        st.warning("请选择要处理的文档")

def render_document_management_tab():
    """渲染文档管理标签页"""
    st.markdown('<div class="sub-header">📊 文档管理</div>', unsafe_allow_html=True)
    
    # 自动刷新逻辑
    if st.session_state.auto_refresh:
        refresh_documents_status()
    
    if not st.session_state.documents:
        st.info("📝 暂无文档记录")
        return
    
    # 文档筛选 - 添加使用状态筛选
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox("处理状态", ["全部", "已完成", "处理中", "等待中", "失败"])
    with col2:
        filter_usage = st.selectbox("使用状态", ["全部", "未使用", "已使用"])
    with col3:
        # 批量操作
        st.markdown("### ")
        if st.button("🔄 批量标记为已使用", use_container_width=True):
            st.session_state.show_batch_mark = True
    
    # 批量标记界面
    if st.session_state.get('show_batch_mark', False):
        render_batch_mark_interface()
    
    # 过滤文档
    filtered_docs = st.session_state.documents
    if filter_status != "全部":
        status_map = {"已完成": "completed", "处理中": "processing", "等待中": "pending", "失败": "failed"}
        filtered_docs = [d for d in filtered_docs if d.get('extraction_status') == status_map[filter_status]]
    
    if filter_usage != "全部":
        usage_map = {"未使用": False, "已使用": True}
        filtered_docs = [d for d in filtered_docs if d.get('is_used') == usage_map[filter_usage]]
    
    # 显示统计信息
    st.markdown("### 📈 文档统计")
    total_count = len(filtered_docs)
    completed_count = len([d for d in filtered_docs if d.get('extraction_status') == 'completed'])
    used_count = len([d for d in filtered_docs if d.get('is_used') == True])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总文档数", total_count)
    with col2:
        st.metric("已完成", completed_count)
    with col3:
        st.metric("已使用", used_count)
    with col4:
        unused_count = total_count - used_count
        st.metric("未使用", unused_count)
    
    st.markdown(f"### 文档列表 ({len(filtered_docs)} 个)")
    
    for doc in filtered_docs:
        render_document_card(doc)


def render_batch_mark_interface():
    """渲染批量标记界面"""
    st.markdown("---")
    st.markdown("### 🎯 批量标记文档")
    
    # 获取所有已完成且未使用的文档
    available_docs = [
        doc for doc in st.session_state.documents 
        if doc.get('extraction_status') == 'completed' and not doc.get('is_used')
    ]
    
    if not available_docs:
        st.info("暂无可以标记的文档（需要状态为已完成且未使用）")
        if st.button("关闭批量标记"):
            st.session_state.show_batch_mark = False
            st.rerun()
        return
    
    st.info(f"找到 {len(available_docs)} 个可以标记的文档")
    
    selected_docs = []
    for doc in available_docs:
        col1, col2, col3 = st.columns([1, 3, 2])
        with col1:
            selected = st.checkbox("", key=f"batch_mark_{doc['id']}", value=True)
        with col2:
            st.text(f"{doc['original_filename']}")
        with col3:
            text_length = doc.get('text_length', 0)
            st.text(f"{text_length} 字符")
        
        if selected:
            selected_docs.append(doc['id'])
    
    if selected_docs:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认标记为已使用", type="primary", use_container_width=True):
                with st.spinner("正在批量标记..."):
                    try:
                        result = DocumentProcessorAPI.batch_update_document_usage(selected_docs, True)
                        st.success(result['message'])
                        # 刷新文档状态
                        refresh_documents_status()
                        st.session_state.show_batch_mark = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"标记失败: {str(e)}")
        
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.show_batch_mark = False
                st.rerun()
    else:
        st.warning("请选择要标记的文档")

def render_document_card(doc: Dict[str, Any]):
    """渲染文档信息卡片"""
    status = doc.get('extraction_status', 'pending')
    is_used = doc.get('is_used', False)
    
    # 状态徽章
    status_class = {
        'completed': 'status-completed',
        'processing': 'status-processing', 
        'failed': 'status-failed',
        'pending': 'status-pending'
    }.get(status, 'status-pending')
    
    card_class = {
        'completed': 'success-card',
        'processing': 'processing-card',
        'failed': 'error-card',
        'pending': 'card'
    }.get(status, 'card')
    
    with st.container():
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        
        with col1:
            # 使用状态图标
            usage_icon = "✅" if is_used else "⭕"
            usage_text = "已使用" if is_used else "未使用"
            
            st.markdown(f"**{usage_icon} 📄 {doc.get('original_filename', '未知文件')}**")
            
            # 文件信息
            file_size = doc.get('file_size', 0) / 1024
            page_count = doc.get('page_count', 1)
            st.markdown(f"大小: {file_size:.1f} KB | 页数: {page_count} | 状态: {usage_text}")
            
            # 处理结果
            if status == 'completed':
                text_length = doc.get('text_length', 0)
                st.markdown(f"提取文本: {text_length} 字符")
        
        with col2:
            status_text = {
                'completed': '已完成',
                'processing': '处理中', 
                'failed': '失败',
                'pending': '等待中'
            }.get(status, status)
            st.markdown(f'<span class="status-badge {status_class}">{status_text}</span>', unsafe_allow_html=True)
        
        with col3:
            if st.button("查看详情", key=f"view_{doc['id']}"):
                st.session_state[f"show_detail_{doc['id']}"] = True
        
        with col4:
            if st.button("刷新状态", key=f"refresh_{doc['id']}"):
                updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                if 'error' not in updated_doc:
                    for i, d in enumerate(st.session_state.documents):
                        if d['id'] == doc['id']:
                            st.session_state.documents[i] = updated_doc
                    st.rerun()
        
        with col5:
            # 使用状态切换按钮
            if status == 'completed':  # 只有已完成的文档可以切换使用状态
                if is_used:
                    if st.button("标记未使用", key=f"unuse_{doc['id']}"):
                        with st.spinner("更新使用状态..."):
                            try:
                                result = DocumentProcessorAPI.update_document_usage(doc['id'], False)
                                st.success(result['message'])
                                # 刷新文档状态
                                updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                                if 'error' not in updated_doc:
                                    for i, d in enumerate(st.session_state.documents):
                                        if d['id'] == doc['id']:
                                            st.session_state.documents[i] = updated_doc
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新失败: {str(e)}")
                else:
                    if st.button("标记已使用", key=f"use_{doc['id']}"):
                        with st.spinner("更新使用状态..."):
                            try:
                                result = DocumentProcessorAPI.update_document_usage(doc['id'], True)
                                st.success(result['message'])
                                # 刷新文档状态
                                updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                                if 'error' not in updated_doc:
                                    for i, d in enumerate(st.session_state.documents):
                                        if d['id'] == doc['id']:
                                            st.session_state.documents[i] = updated_doc
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新失败: {str(e)}")
            else:
                st.button("标记使用", key=f"use_{doc['id']}", disabled=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 显示详情
        if st.session_state.get(f"show_detail_{doc['id']}", False):
            show_document_detail(doc)


def show_document_detail(doc: Dict[str, Any]):
    """显示文档详情"""
    st.markdown("---")
    st.markdown("### 📋 文档详情")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**基本信息**")
        is_used = doc.get('is_used', False)
        usage_text = "已使用" if is_used else "未使用"
        usage_icon = "✅" if is_used else "⭕"
        
        info_data = {
            "文档ID": doc['id'],
            "文件名": doc.get('original_filename', '未知'),
            "文件大小": f"{doc.get('file_size', 0) / 1024:.1f} KB",
            "页数": doc.get('page_count', 1),
            "处理状态": doc.get('extraction_status', '未知'),
            "使用状态": f"{usage_icon} {usage_text}",
            "上传时间": doc.get('created_at', '未知')
        }
        st.json(info_data)
    
    with col2:
        st.markdown("**处理信息**")
        process_info = {
            "文本长度": doc.get('text_length', 0),
            "错误信息": doc.get('extraction_error', '无')
        }
        st.json(process_info)
    
    # 使用状态快速切换
    if doc.get('extraction_status') == 'completed':
        st.markdown("### 🎯 使用状态管理")
        is_used = doc.get('is_used', False)
        current_status = "✅ 已使用" if is_used else "⭕ 未使用"
        
        st.info(f"当前状态: {current_status}")
        
        col1, col2 = st.columns(2)
        with col1:
            if not is_used:
                if st.button("✅ 标记为已使用", type="primary", use_container_width=True):
                    with st.spinner("更新状态..."):
                        try:
                            result = DocumentProcessorAPI.update_document_usage(doc['id'], True)
                            st.success(result['message'])
                            # 刷新文档状态
                            updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                            if 'error' not in updated_doc:
                                for i, d in enumerate(st.session_state.documents):
                                    if d['id'] == doc['id']:
                                        st.session_state.documents[i] = updated_doc
                            st.rerun()
                        except Exception as e:
                            st.error(f"更新失败: {str(e)}")
            else:
                st.button("✅ 已使用", disabled=True, use_container_width=True)
        
        with col2:
            if is_used:
                if st.button("⭕ 标记为未使用", use_container_width=True):
                    with st.spinner("更新状态..."):
                        try:
                            result = DocumentProcessorAPI.update_document_usage(doc['id'], False)
                            st.success(result['message'])
                            # 刷新文档状态
                            updated_doc = DocumentProcessorAPI.get_document(doc['id'])
                            if 'error' not in updated_doc:
                                for i, d in enumerate(st.session_state.documents):
                                    if d['id'] == doc['id']:
                                        st.session_state.documents[i] = updated_doc
                            st.rerun()
                        except Exception as e:
                            st.error(f"更新失败: {str(e)}")
            else:
                st.button("⭕ 未使用", disabled=True, use_container_width=True)
    
    # 显示提取的文本
    st.markdown("### 📝 提取的文本内容")
    
    if doc.get('extraction_status') == 'completed':
        try:
            text_data = DocumentProcessorAPI.get_document_text(doc['id'])
            if 'text' in text_data and text_data['text']:
                st.markdown(f'<div class="text-content">{text_data["text"]}</div>', unsafe_allow_html=True)
                
                # 添加文本统计
                text_length = len(text_data['text'])
                st.info(f"文本统计: {text_length} 字符")
                
                # 添加复制按钮
                if st.button("📋 复制文本", key=f"copy_{doc['id']}"):
                    st.code(text_data['text'], language='text')
                    st.success("文本已复制到代码块中，可以手动复制")
            else:
                st.warning("未提取到文本内容或文本为空")
        except Exception as e:
            st.error(f"获取文本内容失败: {str(e)}")
    
    elif doc.get('extraction_status') in ['pending', 'processing']:
        st.info("⏳ 文本提取进行中，请稍后查看...")
        if st.button("🔄 刷新文本内容", key=f"refresh_text_{doc['id']}"):
            updated_doc = DocumentProcessorAPI.get_document(doc['id'])
            if 'error' not in updated_doc:
                for i, d in enumerate(st.session_state.documents):
                    if d['id'] == doc['id']:
                        st.session_state.documents[i] = updated_doc
                st.rerun()
    
    elif doc.get('extraction_status') == 'failed':
        st.error(f"❌ 文本提取失败: {doc.get('extraction_error', '未知错误')}")
    
    # 显示任务历史
    st.markdown("### 📊 任务历史")
    try:
        tasks = DocumentProcessorAPI.get_document_tasks(doc['id'])
        if tasks:
            for task in tasks:
                st.json(task)
        else:
            st.info("暂无任务记录")
    except Exception as e:
        st.warning(f"无法获取任务记录: {str(e)}")
    
   # 关闭详情按钮
    if st.button("关闭详情", key=f"close_{doc['id']}"):
        st.session_state[f"show_detail_{doc['id']}"] = False
        st.rerun()

def monitor_pdf_task_status(document_id: int):
    """监控PDF任务状态"""
    status_placeholder = st.empty()
    progress_placeholder = st.empty()
    
    with status_placeholder:
        st.info("🔄 开始监控任务状态...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            doc = DocumentProcessorAPI.get_document(document_id)
            if 'error' in doc:
                continue
                
            status = doc.get('extraction_status')
            
            # 更新进度条
            # with progress_placeholder:
            #     progress = min((attempt + 1) / max_attempts * 100, 95)
            #     st.progress(progress)
            
            if status == 'completed':
                with status_placeholder:
                    st.success("✅ 文本提取完成！")
                break
            elif status == 'failed':
                with status_placeholder:
                    error_msg = doc.get('extraction_error', '未知错误')
                    st.error(f"❌ 文本提取失败: {error_msg}")
                break
            elif status == 'processing':
                with status_placeholder:
                    st.info(f"🔧 正在提取文本... ({attempt + 1}/{max_attempts})")
            else:  # pending
                with status_placeholder:
                    st.info(f"⏳ 任务排队中... ({attempt + 1}/{max_attempts})")
            
            time.sleep(2)
            
        except Exception as e:
            with status_placeholder:
                st.warning(f"⚠️ 获取状态时出错: {str(e)}")
            time.sleep(2)
    
    # 最终刷新文档列表
    refresh_documents_status()

def render_instructions_tab():
    """渲染使用说明标签页"""
    st.markdown('<div class="sub-header">📖 使用说明</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 功能概述")
        st.markdown("""
        **PDF文本提取工具** 提供以下核心功能：
        
        #### 📄 单文件提取
        - 上传单个PDF文件自动提取文本内容
        - 实时监控处理状态
        - 直接查看提取的文本内容
        
        #### 📚 批量处理
        - 一次上传多个PDF文件
        - 批量处理待处理文档
        - 实时进度监控和统计
        
        #### 📊 文档管理
        - 查看所有文档处理状态
        - 按状态筛选文档
        - 查看详细处理信息
        """)
    
    with col2:
        st.markdown("### ⚙️ 技术架构")
        st.markdown("""
        **后端技术栈**:
        - FastAPI - 高性能Web框架
        - Celery - 异步任务队列
        - PostgreSQL - 数据存储
        - Redis - 缓存和消息代理
        
        **PDF处理引擎**:
        - PyMuPDF - 高性能PDF文本提取
        - pdfplumber - 辅助PDF解析
        
        **文本提取能力**:
        - 支持文字版PDF直接提取
        - 智能处理复杂版面
        - 保持文本格式和顺序
        """)
        
        st.markdown("### 🔄 状态说明")
        st.markdown("""
        - **等待中** ⏳ - 任务在队列中等待处理
        - **处理中** 🔧 - 任务正在执行文本提取
        - **已完成** ✅ - 文本提取成功完成
        - **失败** ❌ - 文本提取过程出现错误
        """)

def main():
    """主函数"""
    init_session_state()
    render_header()
    
    selected_tab = render_sidebar()
    
    # 根据选择的标签页渲染内容
    if selected_tab == "单文件提取":
        render_single_file_tab()
    elif selected_tab == "批量处理":
        render_batch_processing_tab()
    elif selected_tab == "文档管理":
        render_document_management_tab()
    elif selected_tab == "使用说明":
        render_instructions_tab()
    
    # 自动刷新逻辑
    if st.session_state.auto_refresh:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()