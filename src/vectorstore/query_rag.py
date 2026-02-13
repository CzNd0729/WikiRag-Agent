import os
from typing import List
from langchain_chroma import Chroma  
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from dotenv import load_dotenv

load_dotenv()

class WikiVectorStore:
    """
    Wiki 知识向量库管理器。
    """
    def __init__(self, persist_directory: str = "vectorstore/db"):
        self.persist_directory = persist_directory
        self.embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview")
        self.vector_db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="stardew_wiki"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def add_documents(self, text: str, metadata: dict):
        """
        对文本进行分块并存入向量库。
        """
        doc = Document(page_content=text, metadata=metadata)
        chunks = self.text_splitter.split_documents([doc])
        self.vector_db.add_documents(chunks)
        print(f"Added {len(chunks)} chunks to vector store for {metadata.get('title', 'Unknown')}")

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        相似度搜索。
        """
        return self.vector_db.similarity_search(query, k=k)

    def get_hybrid_retriever(self, k: int = 4) -> EnsembleRetriever:
        """
        构建混合检索器 (BM25 + Vector)。
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
        
        vector_retriever = self.vector_db.as_retriever(search_kwargs={"k": k})
        
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.3, 0.7] # 向量检索权重更高
        )
        return ensemble_retriever

if __name__ == "__main__":
    # 简单测试代码（需要 GOOGLE_API_KEY）
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY not found in environment.")
    else:
        vdb = WikiVectorStore()
        # vdb.add_documents("星露谷物语中的甜瓜是一种夏季作物。", {"title": "Melon", "url": "..."})
        # results = vdb.similarity_search("甜瓜怎么种？")
        # for doc in results:
        #     print(f"Content: {doc.page_content}\nMetadata: {doc.metadata}\n")