"""LangGraph workflow nodes for document generation."""

import re
import json
from typing import Dict, Optional

from datetime import datetime

from templates.doc_templates import get_template, get_available_doc_types
from processors.markdown_parser import parse_markdown_file, truncate_content
from graph.states import DocumentState
from utils.llm import create_llm


def validate_and_collect_info(state: DocumentState) -> DocumentState:
    """验证用户输入，只检查源文档是否存在。
    
    其他信息（项目名称、文档类型）将由 LLM 从源文档中自动提取。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    missing_info = []
    
    # 只检查源文档是否存在
    if not state.get("source_document"):
        missing_info.append("source_document")
    
    state["missing_info"] = missing_info
    
    return state


def ask_if_missing(state: DocumentState) -> DocumentState:
    """如果 LLM 无法确定某些信息，询问用户。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    missing = state.get("missing_info", [])
    if not missing:
        return state
    
    available_types = get_available_doc_types()
    
    message_parts = ["⚠️ 我无法完全确定以下信息，请帮助确认：\n"]
    
    if "project_name" in missing:
        message_parts.append("- 请问项目名称是什么？\n")
    
    if "doc_type" in missing:
        message_parts.append(
            f"- 请指定文档类型，可选：{', '.join(available_types)}\n"
        )
    
    message_parts.append("\n请提供上述信息后，我将为您生成文档。")
    
    state["error"] = '\n'.join(message_parts)
    return state


def parse_source_document(state: DocumentState) -> DocumentState:
    """解析源文档。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("✅ 正在解析源文档...")
    state["progress_messages"] = progress_messages
    
    source_doc = state.get("source_document", "")
    
    # 解析文档
    parsed = parse_markdown_file(source_doc)
    
    # 如果文档过长，截断
    if parsed["stats"]["total_lines"] > 4000:
        state["source_document"] = truncate_content(source_doc)
        progress_messages.append(
            f"⚠️ 源文档较长 ({parsed['stats']['total_lines']} 行)，已截断"
        )
    else:
        state["source_document"] = source_doc
    
    progress_messages.append(
        f"📄 文档标题: {parsed['title']}"
    )
    progress_messages.append(
        f"📊 文档统计: {parsed['stats']['total_lines']} 行, "
        f"{parsed['stats']['total_characters']} 字符, "
        f"{parsed['stats']['section_count']} 个章节"
    )
    
    state["progress_messages"] = progress_messages
    return state


def extract_project_info(state: DocumentState) -> DocumentState:
    """使用 LLM 从源文档和用户指令中提取项目信息。
    
    提取的信息包括：
    - 项目名称 (project_name)
    - 文档类型 (doc_type)
    - 作者 (author)
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("🤖 正在分析文档，提取项目信息...")
    state["progress_messages"] = progress_messages
    
    source_doc = state.get("source_document", "")
    user_instruction = state.get("user_instruction", "")
    
    # 创建 LLM
    llm = create_llm(temperature=0.1)  # 低温度以获得更一致的结果
    
    # 构建提示词
    system_prompt = """你是一位专业的文档分析助手。你的任务是从用户提供的源文档和指令中提取项目信息。

请分析文档内容，提取以下信息并以 JSON 格式返回：
1. **project_name**: 项目名称（如果无法确定，根据文档内容推测一个合适的项目名称）
2. **doc_type**: 应该生成的文档类型，从以下选项中选择：SRS, BRD, TRS, TDD
   - SRS (软件需求规格说明书) - 当文档主要描述软件功能需求时
   - BRD (业务需求文档) - 当文档主要描述业务目标和范围时
   - TRS (技术需求规格说明书) - 当文档主要描述技术需求时
   - TDD (技术设计文档) - 当文档主要描述技术设计和架构时
3. **author**: 作者名称（如果未提及则为空字符串）

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
{"project_name": "项目名称", "doc_type": "SRS", "author": "作者"}"""

    user_prompt = f"""请分析以下文档，提取项目信息：

用户指令：{user_instruction or "(无特定指令)"}

源文档内容：
{source_doc[:8000]}

请提取项目信息（JSON 格式）："""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        response_content = response.content if isinstance(response.content, str) else str(response.content)
        
        # 解析 JSON 响应
        extracted_info = parse_json_response(response_content)
        
        if extracted_info:
            state["project_name"] = extracted_info.get("project_name", "未知项目")
            doc_type = extracted_info.get("doc_type")
            if doc_type and doc_type.upper() in get_available_doc_types():
                state["doc_type"] = doc_type.upper()
            state["author"] = extracted_info.get("author", "")
            
            progress_messages.append(
                f"📝 项目名称: {state['project_name']}"
            )
            progress_messages.append(
                f"📋 文档类型: {state.get('doc_type', '未确定')}"
            )
            if state.get("author"):
                progress_messages.append(f"✍️ 作者: {state['author']}")
        else:
            progress_messages.append("⚠️ 无法自动提取项目信息，将询问用户")
            state["missing_info"] = ["project_name", "doc_type"]
            
    except Exception as e:
        progress_messages.append(f"❌ 提取项目信息失败: {str(e)}")
        state["error"] = str(e)
        state["missing_info"] = ["project_name", "doc_type"]
    
    state["progress_messages"] = progress_messages
    return state


def parse_json_response(response: str) -> Optional[Dict]:
    """从 LLM 响应中解析 JSON。
    
    Args:
        response: LLM 的响应内容
        
    Returns:
        Optional[Dict]: 解析后的字典，如果失败则返回 None
    """
    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试从 Markdown 代码块中提取 JSON
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试找到第一个 JSON 对象
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass
    
    return None


def extract_key_points(state: DocumentState) -> DocumentState:
    """使用 LLM 从源文档中提取关键信息。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("🤖 正在提取关键信息...")
    state["progress_messages"] = progress_messages
    
    source_doc = state.get("source_document", "")
    project_name = state.get("project_name", "未知项目")
    
    # 创建 LLM
    llm = create_llm(temperature=0.3)
    
    # 构建提示词
    system_prompt = """你是一位经验丰富的技术分析师。你的任务是从用户提供的文档中提取关键信息。

请提取以下信息：
1. **核心功能/需求**：文档描述的主要功能和需求
2. **业务目标**：文档背后的业务目标和期望
3. **约束条件**：技术约束、业务约束、法规约束等
4. **用户角色**：涉及的用户类型和角色
5. **数据实体**：涉及的主要数据对象
6. **接口需求**：与外部系统的接口
7. **非功能需求**：性能、安全、可用性等需求

请以结构化的方式输出这些信息，使用 Markdown 格式。"""

    user_prompt = f"""请分析以下文档并提取关键信息：

项目名称：{project_name}

源文档内容：
{source_doc[:8000]}  # 限制长度避免超出上下文

请提取关键信息："""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        state["extracted_key_points"] = response.content if isinstance(response.content, str) else str(response.content)
        progress_messages.append("✅ 关键信息提取完成")
    except Exception as e:
        progress_messages.append(f"❌ 提取关键信息失败: {str(e)}")
        state["error"] = str(e)
    
    state["progress_messages"] = progress_messages
    return state


def generate_document(state: DocumentState) -> DocumentState:
    """使用 LLM 生成目标文档。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("🤖 正在生成目标文档...")
    state["progress_messages"] = progress_messages
    
    doc_type = state.get("doc_type", "SRS")
    project_name = state.get("project_name", "未知项目")
    source_doc = state.get("source_document", "")
    key_points = state.get("extracted_key_points", "")
    user_instruction = state.get("user_instruction", "")
    
    # 获取模板
    try:
        template = get_template(doc_type)
    except ValueError as e:
        progress_messages.append(f"❌ 获取模板失败: {str(e)}")
        state["error"] = str(e)
        state["progress_messages"] = progress_messages
        return state
    
    system_prompt = template["system_prompt"]
    structure = template["structure"]
    
    # 填充模板变量
    filled_structure = structure.format(
        project_name=project_name,
        date=datetime.now().strftime("%Y-%m-%d"),
        author=state.get("author", "GenSpec"),
    )
    
    # 构建用户提示词
    user_prompt = f"""请根据以下信息生成{template['name']}：

## 项目名称
{project_name}

## 用户指令
{user_instruction or '请生成完整的文档'}

## 源文档内容
{source_doc[:10000]}

## 提取的关键信息
{key_points}

## 文档结构
请按照以下结构生成文档：

{filled_structure}

请生成完整的{template['name']}，确保内容详实、结构清晰。
"""
    
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm = create_llm(temperature=0.7)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        generated_doc = response.content if isinstance(response.content, str) else str(response.content)
        state["generated_document"] = generated_doc
        
        # 生成输出文件名
        from graph.states import generate_output_filename
        state["output_filename"] = generate_output_filename(project_name, doc_type)
        
        progress_messages.append("✅ 目标文档生成完成")
    except Exception as e:
        progress_messages.append(f"❌ 生成文档失败: {str(e)}")
        state["error"] = str(e)
    
    state["progress_messages"] = progress_messages
    return state


def review_and_refine(state: DocumentState) -> DocumentState:
    """审查并优化生成的文档。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("🔍 正在审查和优化文档...")
    state["progress_messages"] = progress_messages
    
    generated_doc = state.get("generated_document", "")
    doc_type = state.get("doc_type", "SRS")
    project_name = state.get("project_name", "未知项目")
    
    # 如果没有生成文档，跳过审查
    if not generated_doc:
        progress_messages.append("⚠️ 没有生成的文档，跳过审查步骤")
        state["progress_messages"] = progress_messages
        return state
    
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm = create_llm(temperature=0.3)
        
        system_prompt = f"""你是一位专业的技术文档审查专家。你的任务是审查和优化一份{doc_type}文档。

请执行以下操作：
1. 检查文档的完整性和一致性
2. 改进语言表达，使其更清晰专业
3. 确保文档结构合理
4. 添加必要的连接和过渡
5. 保持原有结构和内容不变，只做优化

请直接输出优化后的完整文档。"""

        user_prompt = f"""请优化以下{doc_type}文档：

项目名称：{project_name}

待优化的文档：
{generated_doc[:10000]}

请输出优化后的完整文档："""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        refined_doc = response.content if isinstance(response.content, str) else str(response.content)
        state["generated_document"] = refined_doc
        
        progress_messages.append("✅ 文档审查和优化完成")
    except Exception as e:
        progress_messages.append(f"⚠️ 文档审查失败（不影响生成结果）: {str(e)}")
    
    state["progress_messages"] = progress_messages
    state["is_complete"] = True
    return state


def return_result(state: DocumentState) -> DocumentState:
    """准备返回结果。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        DocumentState: 更新后的状态
    """
    progress_messages = state.get("progress_messages", [])
    progress_messages.append("📤 准备返回结果...")
    state["progress_messages"] = progress_messages
    return state