"""LangGraph Graph builder for document generation workflow."""

from langgraph.graph import StateGraph, END, START

from graph.states import DocumentState
from graph.nodes import (
    validate_and_collect_info,
    ask_if_missing,
    parse_source_document,
    extract_project_info,
    extract_key_points,
    generate_document,
    review_and_refine,
    return_result,
)


def route_after_validation(state: DocumentState) -> str:
    """验证后的路由逻辑。
    
    如果缺少源文档，询问用户；否则继续处理。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        str: 下一个节点名称
    """
    missing = state.get("missing_info", [])
    if "source_document" in missing:
        return "ask_if_missing"
    return "parse_source_document"


def route_after_extract_info(state: DocumentState) -> str:
    """提取项目信息后的路由逻辑。
    
    如果 LLM 无法确定某些信息，询问用户；否则继续处理。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        str: 下一个节点名称
    """
    missing = state.get("missing_info", [])
    if missing:
        return "ask_if_missing"
    return "extract_key_points"


def route_after_generation(state: DocumentState) -> str:
    """生成后的路由逻辑。
    
    如果生成成功，进行审查优化；否则结束。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        str: 下一个节点名称
    """
    if state.get("generated_document"):
        return "review_and_refine"
    return "return_result"


def build_graph() -> StateGraph:
    """构建 LangGraph 工作流图。
    
    Returns:
        StateGraph: 构建好的工作流图
    """
    # 创建状态图
    graph = StateGraph(DocumentState)
    
    # 添加节点
    graph.add_node("validate_and_collect_info", validate_and_collect_info)
    graph.add_node("ask_if_missing", ask_if_missing)
    graph.add_node("parse_source_document", parse_source_document)
    graph.add_node("extract_project_info", extract_project_info)
    graph.add_node("extract_key_points", extract_key_points)
    graph.add_node("generate_document", generate_document)
    graph.add_node("review_and_refine", review_and_refine)
    graph.add_node("return_result", return_result)
    
    # 设置入口点
    graph.add_edge(START, "validate_and_collect_info")
    
    # 添加条件路由：验证后
    graph.add_conditional_edges(
        "validate_and_collect_info",
        route_after_validation,
        {
            "ask_if_missing": "ask_if_missing",
            "parse_source_document": "parse_source_document",
        }
    )
    
    # 添加边：询问后直接结束（等待用户补充信息）
    graph.add_edge("ask_if_missing", END)
    
    # 添加边：解析 -> 提取项目信息 -> 提取关键点 -> 生成
    graph.add_edge("parse_source_document", "extract_project_info")
    
    # 添加条件路由：提取项目信息后
    graph.add_conditional_edges(
        "extract_project_info",
        route_after_extract_info,
        {
            "ask_if_missing": "ask_if_missing",
            "extract_key_points": "extract_key_points",
        }
    )
    
    graph.add_edge("extract_key_points", "generate_document")
    
    # 添加条件路由：生成后
    graph.add_conditional_edges(
        "generate_document",
        route_after_generation,
        {
            "review_and_refine": "review_and_refine",
            "return_result": "return_result",
        }
    )
    
    # 添加边：审查后返回结果
    graph.add_edge("review_and_refine", "return_result")
    graph.add_edge("return_result", END)
    
    return graph


def compile_graph() -> StateGraph:
    """编译 LangGraph 工作流图。
    
    Returns:
        StateGraph: 编译后的工作流图
    """
    graph = build_graph()
    return graph.compile()


# 全局编译后的图实例
compiled_graph = compile_graph()