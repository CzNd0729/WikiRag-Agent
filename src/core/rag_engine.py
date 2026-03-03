import os
from typing import List
from langchain_core.documents import Document
from core.llm_provider import get_chat_model, get_embedding_model
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
import requests

class RAGEngine:
    """
    通用的 RAG 检索引擎，集成了查询改写、混合检索和重排序。
    """
    def __init__(self, collection_name: str = "stardew_wiki"):
        self.embeddings = get_embedding_model()
        self.vector_db = Chroma(
            persist_directory=os.getenv("VECTOR_DB_DIR", "vectorstore/db"),
            embedding_function=self.embeddings,
            collection_name=collection_name
        )
        self.rewrite_llm = get_chat_model("RAG_REWRITE")

    async def rewrite_query(self, query: str) -> str:
        """
        利用 LLM 改写用户查询为精准检索词。
        """
        system_prompt = (
            "你是一个百科检索专家。请将用户的问题改写为一个最适合在知识库中进行语义检索的关键词或短句。"
            "请以 JSON 格式输出改写后的结果：{\"rewritten_query\": \"...\"}"
        )
        try:
            # 简化链调用，直接使用 LLM 的 JSON 输出能力
            response = await self.rewrite_llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ])
            import json
            data = json.loads(response.content)
            return data.get("rewritten_query", query)
        except Exception as e:
            print(f"RAG Rewrite failed: {e}")
            return query

    def rerank(self, query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
        """
        利用外部 Reranker API 进行重排序。
        """
        if not documents:
            return []

        api_key = os.getenv("RERANKER_API_KEY")
        api_base = os.getenv("RERANKER_API_BASE")
        model = os.getenv("RERANKER_MODEL")
        
        if not api_key or not api_base:
            return documents[:top_n]

        try:
            response = requests.post(
                f"{api_base}/rerank",
                json={
                    "model": model,
                    "query": query,
                    "documents": [doc.page_content for doc in documents],
                    "top_n": top_n
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )
            result = response.json()
            return [documents[item["index"]] for item in result.get("results", [])]
        except Exception as e:
            print(f"Rerank failed: {e}")
            return documents[:top_n]

    async def search(self, query: str, k: int = 5) -> List[Document]:
        """
        混合检索入口。
        """
        rewritten = await self.rewrite_query(query)
        
        # 简单混合检索示例 (实际可根据需要使用 EnsembleRetriever)
        # 这里为了演示，先只使用向量检索
        initial_docs = await self.vector_db.asimilarity_search(rewritten, k=20)
        
        return self.rerank(rewritten, initial_docs, top_n=k)
