"""Chainlit app for document generation."""

import os
import tempfile
import chainlit as cl
from chainlit.types import ThreadDict
from typing import Optional

from graph.builder import compiled_graph
from graph.states import create_initial_state, generate_output_filename
from templates.doc_templates import get_available_doc_types, DOC_TYPES
from processors.markdown_parser import parse_markdown_file

from langchain_community.document_loaders import TextLoader

# === 会话状态管理 ===
class GenerationState:
    """文档生成会话状态。"""
    
    def __init__(self):
        self.project_name: Optional[str] = None
        self.doc_type: Optional[str] = None
        self.source_document: Optional[str] = None
        self.source_filename: Optional[str] = None
        self.user_instruction: Optional[str] = None
        self.author: Optional[str] = None
        self.is_complete: bool = False


# === 欢迎消息 ===
@cl.on_chat_start
async def start():
    """聊天开始时的初始化。"""
    # 显示欢迎消息
    await cl.Message(
        content="""👋 你好！我是 **GenSpec** - 智能文档生成助手。

我可以帮您根据源文档生成项目特定的文档。

## 📋 支持的文档类型
- **SRS** - 软件需求规格说明书
- **BRD** - 业务需求文档  
- **TRS** - 技术需求规格说明书
- **TDD** - 技术设计文档

## 🚀 使用方式
1. 上传一个 Markdown 格式的源文档
2. 告诉我您需要生成什么类型的文档
3. 我会自动分析并生成专业文档

请上传您的源文档开始吧！""",
    ).send()
    
    # 发送文档类型列表
    types_list = "\n".join([f"- **{k}** - {v['name']}" for k, v in DOC_TYPES.items()])
    await cl.Message(content=f"## 支持的文档类型\n{types_list}").send()


# === 文件上传处理 ===
# @cl.on_file_upload
async def on_file_upload(file: cl.File):
    """处理文件上传。"""
    # 检查文件类型
    if not file.name.endswith(('.md', '.markdown')):
        await cl.Message(
            content="⚠️ 请上传 Markdown 格式的文件（.md 或 .markdown）",
        ).send()
        return
    
    # 读取文件内容
    try:
        loader = TextLoader(file.path, encoding="utf-8")
        docs = loader.load()
        content = "\n".join([d.page_content for d in docs])#file.content.decode('utf-8') if isinstance(file.content, bytes) else file.content
        
        # 限制文件大小（100KB）
        if len(content) > 100000:
            await cl.Message(
                content="⚠️ 文件过大，请上传 100KB 以内的文件",
            ).send()
            return
        
        # 存储到会话上下文
        cl.user_session.set("source_content", content)
        cl.user_session.set("source_filename", file.name)
        
        # 解析文档获取标题
        parsed = parse_markdown_file(content)
        
        await cl.Message(
            content=f"✅ 文件上传成功！\n\n"
                    f"**文件名**: {file.name}\n"
                    f"**标题**: {parsed['title']}\n"
                    f"**统计**: {parsed['stats']['total_lines']} 行, {parsed['stats']['total_characters']} 字符",
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ 文件读取失败: {str(e)}",
        ).send()


# === 消息处理 ===
@cl.on_message
async def main(msg: cl.Message):
    """处理用户消息。"""
    # 收集本次消息附带的上传文件路径
    file_paths = []
    for elem in msg.elements:
        if isinstance(elem, cl.File):
            file_paths.append(elem.path)
            await cl.Message(content=f"已收到文件：{elem.name}").send()
            await on_file_upload(elem)
    
    # 获取源文档内容
    source_content = cl.user_session.get("source_content")
    source_filename = cl.user_session.get("source_filename")

    # 检查是否有源文档
    if not source_content:
        await cl.Message(
            content="⚠️ 请先上传一个 Markdown 格式的源文档，然后再告诉我您需要生成什么文档。"
        ).send()
        return
    
    # 存储用户指令
    user_instruction = msg.content
    
    # # 尝试从指令中推断文档类型
    # doc_type = None
    # instruction_lower = user_instruction.lower()
    
    # doc_type_keywords = {
    #     "SRS": ["srs", "软件需求", "需求规格", "software requirements"],
    #     "BRD": ["brd", "业务需求", "业务需求文档", "business requirements"],
    #     "TRS": ["trs", "技术需求", "技术规格", "technical requirements"],
    #     "TDD": ["tdd", "技术设计", "设计文档", "technical design", "架构设计"],
    # }
    
    # for dt, keywords in doc_type_keywords.items():
    #     for keyword in keywords:
    #         if keyword in instruction_lower:
    #             doc_type = dt
    #             break
    #     if doc_type:
    #         break
    
    # # 尝试提取项目名称
    # project_name = None
    # import re
    # match = re.search(r'(?:项目[名称]?)[:：]\s*(.+?)(?:\s|$)', user_instruction)
    # if match:
    #     project_name = match.group(1).strip()
    
    # 显示处理开始消息
    processing_msg = await cl.Message(
        content="🔄 正在开始文档生成流程..."
    ).send()
    
    # 创建工作流状态
    initial_state = create_initial_state(
        source_document=source_content,
        source_filename=source_filename,
        user_instruction=user_instruction,
    )
    
    # if doc_type:
    #     initial_state["doc_type"] = doc_type
    
    # if project_name:
    #     initial_state["project_name"] = project_name
    
    # # 存储到会话
    # cl.user_session.set("doc_type", doc_type)
    # cl.user_session.set("project_name", project_name)
    
    # 运行工作流
    try:
        # 使用 stream 模式获取进度
        result = await run_workflow(initial_state)
        
        # 更新处理消息
        progress_messages = result.get("progress_messages", [])
        
        if result.get("is_complete") and result.get("generated_document"):
            # 生成成功
            generated_doc = result["generated_document"]
            output_filename = result.get("output_filename", "output.md")
            
            # 更新处理消息
            processing_msg.content = "✅ 文档生成完成！\n\n" + "\n".join(progress_messages)
            await processing_msg.update()
            
            # 显示生成的文档（前 4000 字符）
            doc_preview = generated_doc[:4000]
            if len(generated_doc) > 4000:
                doc_preview += f"\n\n... (内容过长，共 {len(generated_doc)} 字符，请下载完整文件)"
            
            await cl.Message(
                content=f"## 生成的文档预览\n\n```markdown\n{doc_preview}\n```",
            ).send()
            
            # 提供下载
            # 创建临时文件用于下载
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, output_filename)
            
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(generated_doc)
            
            await cl.File(
                name=output_filename,
                path=temp_file_path,
                content=generated_doc,
            ).send()
            
            await cl.Message(
                content=f"📥 **下载**: [{output_filename}](files/{output_filename})"
            ).send()
            
        elif result.get("missing_info"):
            # 需要补充信息
            missing = result["missing_info"]
            available_types = get_available_doc_types()
            
            message_parts = ["⚠️ 我需要一些补充信息才能继续：\n"]
            
            if "source_document" in missing:
                message_parts.append("- 请上传一个 Markdown 源文档\n")
            
            if "doc_type" in missing:
                message_parts.append(
                    f"- 请指定文档类型，可选：{', '.join(available_types)}\n"
                )
            
            if "project_name" in missing:
                message_parts.append("- 请提供项目名称\n")
            
            message_parts.append("\n请补充上述信息后，我将为您生成文档。")
            
            processing_msg.content = '\n'.join(message_parts)
            await processing_msg.update()
            
        else:
            # 其他错误
            error = result.get("error", "未知错误")
            processing_msg.content = f"❌ 生成失败: {error}"
            await processing_msg.update()
            
    except Exception as e:
        processing_msg.content = f"❌ 工作流执行失败: {str(e)}"
        await processing_msg.update()


async def run_workflow(initial_state: dict) -> dict:
    """运行 LangGraph 工作流。
    
    Args:
        initial_state: 初始状态
        
    Returns:
        dict: 工作流执行结果
    """
    from graph.builder import compiled_graph
    
    # 使用 astream 获取流式输出
    result = await compiled_graph.ainvoke(initial_state)
    
    return result


# === 聊天重置 ===
@cl.on_chat_end
async def on_chat_end():
    """聊天结束时的清理。"""
    cl.user_session.set("source_content", None)
    cl.user_session.set("source_filename", None)
    cl.user_session.set("doc_type", None)
    cl.user_session.set("project_name", None)


@cl.action_callback(name="download_doc")
async def download_doc(action):
    """下载文档的回调。"""
    # 这个函数用于处理下载按钮点击
    pass