import os
import json
from langchain_core.tools import tool
from core.rag_engine import RAGEngine
from mcp_servers.stardew_mcp import get_player_status, get_inventory

# 初始化 RAG
rag = RAGEngine()

@tool
async def search_wiki(query: str):
    """检索知识库。返回分块内容及其对应的原始文件路径(source)。结果将以列表形式返回，供 Reflector 筛选。"""
    docs = await rag.search(query, k=5)
    results = []
    for doc in docs:
        title = doc.metadata.get('title', 'Knowledge')
        source = doc.metadata.get('source', 'Unknown')
        results.append({
            "title": title,
            "source": source,
            "content": doc.page_content
        })
    # 返回 JSON 字符串，以便 tools_node 处理
    return json.dumps(results)

@tool
async def read_full_wiki(source_path: str):
    """读取完整的原始 Wiki Markdown 文本。source_path 应从 search_wiki 的结果中获取。"""
    try:
        # 安全检查：确保只能读取 data/processed 或 data/raw 目录下的文件
        normalized_path = os.path.normpath(source_path)
        if not (normalized_path.startswith("data" + os.sep + "processed") or 
                normalized_path.startswith("data" + os.sep + "raw")):
             return f"Error: Unauthorized path access: {source_path}"
             
        if not os.path.exists(normalized_path):
            return f"Error: File not found: {source_path}"
            
        with open(normalized_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {e}"

# @tool
# async def get_context_status():
#     """读取实时环境基础数据。"""
#     return get_player_status()

# @tool
# async def get_context_details():
#     """读取环境详细清单。"""
#     return get_inventory()

# 统一导出工具列表
# tools = [search_wiki, read_full_wiki, get_context_status, get_context_details]
tools = [search_wiki, read_full_wiki]