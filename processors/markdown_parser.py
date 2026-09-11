"""Markdown document parser."""

import re
from typing import List, Dict, Optional


def parse_markdown_file(content: str) -> Dict:
    """解析 Markdown 文件内容。
    
    Args:
        content: Markdown 文件内容
        
    Returns:
        Dict: 包含解析后的内容、标题、章节等信息
    """
    lines = content.split('\n')
    
    # 提取标题
    title = extract_title(content)
    
    # 提取章节结构
    sections = extract_sections(content)
    
    # 计算文档统计信息
    stats = {
        "total_lines": len(lines),
        "total_characters": len(content),
        "section_count": len(sections),
    }
    
    return {
        "title": title,
        "content": content,
        "sections": sections,
        "stats": stats,
        "raw_lines": lines,
    }


def extract_title(content: str) -> str:
    """从 Markdown 内容中提取标题。
    
    Args:
        content: Markdown 内容
        
    Returns:
        str: 文档标题
    """
    # 查找第一个 H1 标题
    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return "未命名文档"


def extract_sections(content: str) -> List[Dict]:
    """提取 Markdown 文档的章节结构。
    
    Args:
        content: Markdown 内容
        
    Returns:
        List[Dict]: 章节列表，每个章节包含标题、内容、层级等信息
    """
    sections = []
    lines = content.split('\n')
    current_section = None
    current_level = 0
    
    for i, line in enumerate(lines):
        # 检查是否是标题行
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            # 保存上一个章节
            if current_section:
                current_section["content"] = '\n'.join(current_section["content"])
                sections.append(current_section)
            
            # 创建新章节
            level = len(match.group(1))
            title = match.group(2).strip()
            current_level = level
            current_section = {
                "level": level,
                "title": title,
                "content": [],
                "line_number": i,
            }
        elif current_section:
            current_section["content"].append(line)
    
    # 保存最后一个章节
    if current_section:
        current_section["content"] = '\n'.join(current_section["content"])
        sections.append(current_section)
    
    return sections


def extract_key_information(content: str) -> Dict:
    """从 Markdown 文档中提取关键信息。
    
    Args:
        content: Markdown 内容
        
    Returns:
        Dict: 提取的关键信息
    """
    info = {
        "tables": extract_tables(content),
        "lists": extract_lists(content),
        "code_blocks": extract_code_blocks(content),
        "headings": extract_all_headings(content),
    }
    return info


def extract_tables(content: str) -> List[str]:
    """提取 Markdown 表格。
    
    Args:
        content: Markdown 内容
        
    Returns:
        List[str]: 表格列表
    """
    tables = []
    in_table = False
    table_lines = []
    
    for line in content.split('\n'):
        if '|' in line and line.strip().startswith('|'):
            in_table = True
            table_lines.append(line)
        elif in_table:
            if line.strip() == '':
                tables.append('\n'.join(table_lines))
                table_lines = []
                in_table = False
            else:
                table_lines.append(line)
    
    # 处理未结束的表格
    if table_lines:
        tables.append('\n'.join(table_lines))
    
    return tables


def extract_lists(content: str) -> List[Dict]:
    """提取 Markdown 列表。
    
    Args:
        content: Markdown 内容
        
    Returns:
        List[Dict]: 列表信息
    """
    lists = []
    current_list = []
    list_type = None
    
    for line in content.split('\n'):
        # 有序列表
        match = re.match(r'^\d+\.\s+(.+)$', line)
        if match:
            if not current_list:
                list_type = "ordered"
                current_list = []
            current_list.append(match.group(1))
        # 无序列表
        elif re.match(r'^[-*+]\s+(.+)$', line):
            if not current_list:
                list_type = "unordered"
                current_list = []
            current_list.append(re.sub(r'^[-*+]\s+', '', line))
        else:
            if current_list:
                lists.append({
                    "type": list_type,
                    "items": current_list,
                })
                current_list = []
                list_type = None
    
    # 处理未结束的列表
    if current_list:
        lists.append({
            "type": list_type,
            "items": current_list,
        })
    
    return lists


def extract_code_blocks(content: str) -> List[Dict]:
    """提取 Markdown 代码块。
    
    Args:
        content: Markdown 内容
        
    Returns:
        List[Dict]: 代码块信息
    """
    blocks = []
    in_block = False
    language = ""
    code_lines = []
    
    for i, line in enumerate(content.split('\n')):
        if line.startswith('```'):
            if not in_block:
                in_block = True
                language = line[3:].strip()
                code_lines = []
            else:
                blocks.append({
                    "language": language,
                    "code": '\n'.join(code_lines),
                })
                in_block = False
                code_lines = []
        elif in_block:
            code_lines.append(line)
    
    return blocks


def extract_all_headings(content: str) -> List[Dict]:
    """提取所有标题。
    
    Args:
        content: Markdown 内容
        
    Returns:
        List[Dict]: 标题列表
    """
    headings = []
    
    for i, line in enumerate(content.split('\n')):
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            headings.append({
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
                "line_number": i,
            })
    
    return headings


def truncate_content(content: str, max_lines: int = 4000) -> str:
    """截断过长的文档内容。
    
    Args:
        content: Markdown 内容
        max_lines: 最大行数
        
    Returns:
        str: 截断后的内容
    """
    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content
    
    # 保留头部、中间和尾部内容
    header_lines = 500
    footer_lines = 500
    
    truncated = (
        '\n'.join(lines[:header_lines]) +
        f"\n\n... [内容已截断，共 {len(lines)} 行，显示前 {header_lines} 行和后 {footer_lines} 行] ...\n\n" +
        '\n'.join(lines[-footer_lines:])
    )
    
    return truncated