import os
import re
import time
from typing import List
from langchain_chroma import Chroma  
from core.llm_provider import get_embedding_model
from langchain_core.documents import Document
from vectorstore import get_markdown_splitter, MAX_BATCH_SIZE
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from core.config import DEFAULT_RAG_CONFIG

load_dotenv()

class WikiVectorStore:
    """
    Wiki 知识向量库管理器。
    """
    def __init__(self, persist_directory: str = "vectorstore/db"):
        self.persist_directory = persist_directory
        
        # 使用全局统一的 Embedding 配置
        self.embeddings = get_embedding_model()
        
        self.vector_db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="stardew_wiki",
            collection_metadata={"hnsw:space": "cosine"} # 显式指定使用余弦相似度
        )
        # 使用统一配置的 Markdown 文本分割器
        self.text_splitter = get_markdown_splitter()

    def add_prechunked_documents(self, chunks: List[str], metadata: dict):
        """
        直接将预分块的内容（已清洗）存入向量库。
        增加单次上传的分块数量限制 (MAX_BATCH_SIZE)。
        """
        title = metadata.get("title", "未知标题")
        final_docs = []
        
        for chunk_clean in chunks:
            # 使用统一的注入格式 [页面标题: {title}]
            content_for_vector = f"[页面标题: {title}]\n内容: {chunk_clean}"
            final_docs.append(Document(
                page_content=content_for_vector,
                metadata={
                    **metadata,
                    "title": title
                }
            ))
        
        if final_docs:
            # 分批提交以满足 batch size 限制
            for i in range(0, len(final_docs), MAX_BATCH_SIZE):
                batch = final_docs[i:i + MAX_BATCH_SIZE]
                self.vector_db.add_documents(batch)
                print(f"Added batch of {len(batch)} documents to vector store for {title} ({i//MAX_BATCH_SIZE + 1}/{(len(final_docs)-1)//MAX_BATCH_SIZE + 1})")

    async def aadd_prechunked_documents(self, chunks: List[str], metadata: dict):
        """
        异步将预分块的内容（已清洗）存入向量库。
        增加单次上传的分块数量限制 (MAX_BATCH_SIZE)。
        """
        title = metadata.get("title", "未知标题")
        final_docs = []
        
        for chunk_clean in chunks:
            # 使用统一的注入格式 [页面标题: {title}]
            content_for_vector = f"[页面标题: {title}]\n内容: {chunk_clean}"
            final_docs.append(Document(
                page_content=content_for_vector,
                metadata={
                    **metadata,
                    "title": title
                }
            ))
        
        if final_docs:
            # 分批提交以满足 batch size 限制
            for i in range(0, len(final_docs), MAX_BATCH_SIZE):
                batch = final_docs[i:i + MAX_BATCH_SIZE]
                await self.vector_db.aadd_documents(batch)
                print(f"Added batch of {len(batch)} documents to vector store for {title} ({i//MAX_BATCH_SIZE + 1}/{(len(final_docs)-1)//MAX_BATCH_SIZE + 1})")

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        相似度搜索。
        """
        return self.vector_db.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 4):
        """
        相似度搜索并返回得分。
        """
        return self.vector_db.similarity_search_with_relevance_scores(query, k=k)

    def rerank(self, query: str, documents: List[Document], top_n: int = 3) -> List[Document]:
        """
        对文档进行重排序。
        """
        if not documents:
            return []

        import requests
        # 从环境变量读取 Reranker 配置
        api_key = os.getenv("RERANKER_API_KEY", os.getenv("SILICONFLOW_API_KEY"))
        api_base = os.getenv("RERANKER_API_BASE", "https://api.siliconflow.cn/v1")
        model = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        url = f"{api_base}/rerank"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 准备重排序请求
        payload = {
            "model": model,
            "query": query,
            "documents": [doc.page_content for doc in documents],
            "top_n": top_n
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            reranked_docs = []
            for item in result.get("results", []):
                index = item["index"]
                doc = documents[index]
                # 将分数存入 metadata 以供参考
                doc.metadata["rerank_score"] = item["relevance_score"]
                reranked_docs.append(doc)
            
            return reranked_docs
        except Exception as e:
            print(f"Reranking failed: {e}")
            # 如果重排序失败，返回原始文档的前 top_n 个
            return documents[:top_n]

    def rewrite_query(self, query: str) -> str:
        """
        使用 LLM 改写查询词，以提高召回率。
        """
        # 从环境变量读取 RAG 改写 LLM 配置
        llm = ChatOpenAI(
            model=os.getenv("RAG_REWRITE_MODEL", "deepseek-chat"),
            api_key=os.getenv("RAG_REWRITE_API_KEY", os.getenv("DEEPSEEK_API_KEY")),
            base_url=os.getenv("RAG_REWRITE_API_BASE", "https://api.deepseek.com"),
            temperature=0
        )
        
        system_prompt = (
            "你是一个百科知识检索专家。你的任务是根据用户的提问，生成一个最适合在知识库中检索的关键词或短句。"
            "你应该：\n"
            "1. 提取核心实体、概念或技术术语。\n"
            "2. 去除口语化的修饰词，保留具有检索价值的关键词。\n"
            "3. 只输出改写后的文本，不要有任何多余的解释。"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            rewritten_query = chain.invoke({"query": query})
            print(f"Query Rewritten: '{query}' -> '{rewritten_query}'")
            return rewritten_query
        except Exception as e:
            print(f"Query rewriting failed: {e}")
            return query

    def hybrid_search_with_rerank(self, query: str, k: int = None, initial_k: int = None, use_rewrite: bool = False) -> List[Document]:
        """
        执行混合检索并使用重排序。
        配置参数具有最高优先级。
        """
        # 优先级：配置文件 > 调用参数 (如果配置文件中有定义)
        target_k = DEFAULT_RAG_CONFIG.final_top_k if DEFAULT_RAG_CONFIG.final_top_k is not None else k
        target_initial_k = DEFAULT_RAG_CONFIG.initial_top_k if DEFAULT_RAG_CONFIG.initial_top_k is not None else initial_k

        search_query = query
        if use_rewrite:
            search_query = self.rewrite_query(query)

        retriever = self.get_hybrid_retriever(k=target_initial_k)
        initial_docs = retriever.invoke(search_query)
        
        # 去重（如果 BM25 和 Vector 返回了相同的文档，虽然 EnsembleRetriever 通常会处理，但双重保险）
        seen_contents = set()
        unique_docs = []
        for doc in initial_docs:
            if doc.page_content not in seen_contents:
                unique_docs.append(doc)
                seen_contents.add(doc.page_content)
        
        return self.rerank(search_query, unique_docs, top_n=target_k)

    def get_hybrid_retriever(self, k: int = 4) -> EnsembleRetriever:
        """
        构建混合检索器 (BM25 + Vector)。
        从配置文件读取权重。
        """
        # 获取所有文档以构建 BM25 索引
        # 注意：在生产环境中，BM25 索引应持久化或按需加载
        collection_data = self.vector_db.get()
        docs = collection_data.get("documents", [])
        metadatas = collection_data.get("metadatas", [])
        
        all_docs = [Document(page_content=text, metadata=meta or {}) for text, meta in zip(docs, metadatas)]
        
        if not all_docs:
            # 如果数据库为空，返回默认向量检索器
            return self.vector_db.as_retriever(search_kwargs={"k": k})

        bm25_retriever = BM25Retriever.from_documents(all_docs)
        bm25_retriever.k = k
        
        # 启用带相关性得分的向量检索
        # 注意：Chroma 的 similarity_search_with_relevance_scores 预设返回 0-1
        # 但某些 Embedding 模型或距离函数可能超出此范围。这里使用普通的 similarity 检索
        # 以避免 LangChain 的 score_threshold 警告/过滤，或者改用 mmr
        vector_retriever = self.vector_db.as_retriever(
            search_kwargs={
                "k": k
            }
        )
        
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[DEFAULT_RAG_CONFIG.bm25_weight, DEFAULT_RAG_CONFIG.vector_weight]
        )
        return ensemble_retriever

if __name__ == "__main__":
    # 简单测试代码
    vdb = WikiVectorStore()
        # vdb.add_documents("星露谷物语中的甜瓜是一种夏季作物。", {"title": "Melon", "url": "..."})
        # results = vdb.similarity_search("甜瓜怎么种？")
        # for doc in results:
        #     print(f"Content: {doc.page_content}\nMetadata: {doc.metadata}\n")