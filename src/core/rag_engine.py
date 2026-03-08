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

    async def search(self, query: str, k: int = 5) -> List[Document]:
        """
        混合检索入口。
        封装了：
        1. Query 改写 (Rewrite)
        2. Hybrid Search (Vector + BM25)
        3. Rerank (BGE-Reranker)
        """
        # 由于 WikiVectorStore 的混合检索目前是同步实现（Reranker 使用 requests），
        # 在异步环境中使用 run_in_executor 或直接调用。
        # 这里为了保持一致性，先直接调用，未来可根据性能需求优化为全异步。
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 使用 hybrid_search_with_rerank 执行全链路检索
        return await loop.run_in_executor(
            None, 
            self.vdb.hybrid_search_with_rerank, 
            query, 
            k
        )

    def search_sync(self, query: str, k: int = 5) -> List[Document]:
        """同步检索接口"""
        return self.vdb.hybrid_search_with_rerank(query, k=k)
