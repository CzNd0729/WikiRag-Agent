import os
from typing import List
from langchain_core.documents import Document
from vectorstore.query_rag import WikiVectorStore

class RAGEngine:
    """
    通用的 RAG 检索引擎，集成了查询改写、混合检索和重排序。
    直接封装了 WikiVectorStore 的高级检索能力。
    """
    def __init__(self, collection_name: str = "stardew_wiki"):
        # WikiVectorStore 内部已处理了 Embedding 和 Chroma 初始化
        self.vdb = WikiVectorStore()

    async def search(self, query: str, k: int = None) -> List[Document]:
        """
        混合检索入口。
        优先级：配置文件 > 调用参数。
        """
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 使用 hybrid_search_with_rerank 执行全链路检索
        # 注意：hybrid_search_with_rerank 内部已处理优先级
        return await loop.run_in_executor(
            None, 
            self.vdb.hybrid_search_with_rerank, 
            query, 
            k
        )

    def search_sync(self, query: str, k: int = None) -> List[Document]:
        """同步检索接口"""
        return self.vdb.hybrid_search_with_rerank(query, k=k)
