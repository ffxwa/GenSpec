"""LLM client wrapper for LangChain."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import settings


def create_llm(
    model: str = None,
    temperature: float = 0.7,
    base_url: str = None,
    api_key: str = None,
) -> ChatOpenAI:
    """创建 LLM 客户端实例。
    
    Args:
        model: 模型名称，默认使用配置文件中的值
        temperature: 温度参数，控制输出的随机性
        base_url: API 基础 URL，默认使用配置文件中的值
        api_key: API 密钥，默认使用配置文件中的值
        
    Returns:
        ChatOpenAI: LLM 实例
    """
    return ChatOpenAI(
        model=model or settings.model,
        temperature=temperature,
        base_url=base_url or settings.base_url,
        api_key=api_key or settings.api_key,
    )


async def chat_completion(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
) -> str:
    """发送聊天请求并获取回复。
    
    Args:
        messages: 消息列表，每条消息包含 role 和 content
        model: 模型名称
        temperature: 温度参数
        
    Returns:
        str: LLM 的回复内容
    """
    llm = create_llm(model=model, temperature=temperature)
    
    # 转换消息格式
    formatted_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            formatted_messages.append(SystemMessage(content=content))
        elif role == "user":
            formatted_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            formatted_messages.append(AIMessage(content=content))
    
    response = await llm.ainvoke(formatted_messages)
    return response.content


def chat_completion_sync(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
) -> str:
    """发送聊天请求并获取回复（同步版本）。
    
    Args:
        messages: 消息列表，每条消息包含 role 和 content
        model: 模型名称
        temperature: 温度参数
        
    Returns:
        str: LLM 的回复内容
    """
    llm = create_llm(model=model, temperature=temperature)
    
    # 转换消息格式
    formatted_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            formatted_messages.append(SystemMessage(content=content))
        elif role == "user":
            formatted_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            formatted_messages.append(AIMessage(content=content))
    
    response = llm.invoke(formatted_messages)
    return response.content