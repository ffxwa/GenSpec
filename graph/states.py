"""LangGraph State definition for document generation workflow."""

from typing import TypedDict, Optional, List
from dataclasses import dataclass, field


class DocumentState(TypedDict):
    """文档生成工作流的状态定义。"""
    
    # === 用户输入 ===
    # 项目名称（可选，缺失时会询问用户）
    project_name: Optional[str]
    
    # 文档类型：SRS/BRD/TRS/TDD/自定义
    doc_type: Optional[str]
    
    # 源文档的 Markdown 内容
    source_document: Optional[str]
    
    # 源文档文件名
    source_filename: Optional[str]
    
    # 用户原始指令
    user_instruction: Optional[str]
    
    # === 处理结果 ===
    # 从源文档提取的关键信息
    extracted_key_points: Optional[str]
    
    # 生成的目标文档内容
    generated_document: Optional[str]
    
    # 生成的文档文件名
    output_filename: Optional[str]
    
    # === 控制流 ===
    # 缺失的信息列表
    missing_info: List[str]
    
    # 是否已完成生成
    is_complete: bool
    
    # 处理进度消息
    progress_messages: List[str]
    
    # 错误信息
    error: Optional[str]


def create_initial_state(
    source_document: Optional[str] = None,
    source_filename: Optional[str] = None,
    user_instruction: Optional[str] = None,
) -> DocumentState:
    """创建工作流初始状态。
    
    Args:
        source_document: 源文档的 Markdown 内容
        source_filename: 源文档文件名
        user_instruction: 用户原始指令
        
    Returns:
        DocumentState: 初始状态
    """
    return DocumentState(
        project_name=None,
        doc_type=None,
        source_document=source_document,
        source_filename=source_filename,
        user_instruction=user_instruction,
        extracted_key_points=None,
        generated_document=None,
        output_filename=None,
        missing_info=[],
        is_complete=False,
        progress_messages=[],
        error=None,
    )


def generate_output_filename(project_name: str, doc_type: str) -> str:
    """生成输出文件名。
    
    Args:
        project_name: 项目名称
        doc_type: 文档类型
        
    Returns:
        str: 输出文件名
    """
    import re
    from datetime import datetime
    
    # 清理项目名称，移除非法字符
    safe_name = re.sub(r'[^\w\s-]', '', project_name).strip().replace(' ', '-')
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"{safe_name}_{doc_type.upper()}_{timestamp}.md"