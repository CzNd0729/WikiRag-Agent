import json
from typing import List, Optional
from langchain_core.messages import BaseMessage
from core.llm_provider import get_chat_model, get_embedding_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_chroma import Chroma
from langchain_core.documents import Document

class MemoryManager:
    """
    企业级记忆管理器，负责长短期记忆的协同，并接入 ChromaDB 持久化。
    """
    def __init__(self, persist_directory: str = "vectorstore/db"):
        self.llm = get_chat_model("AGENT_LLM")
        self.embeddings = get_embedding_model()
        self.persist_directory = persist_directory
        
        # 记忆专用的 Collection：user_memories
        self.vector_db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="user_memories",
            collection_metadata={"hnsw:space": "cosine"}
        )

    async def retrieve_long_term_memory(self, query: str, conversation_id: str, k: int = 5) -> str:
        """
        检索长期记忆。
        使用语义搜索从 ChromaDB 中召回相关的历史记忆或事实。
        """
        # 我们可以根据 conversation_id 过滤（如果需要的话），或者全局检索
        # 这里先实现全局检索，以便跨会话共享记忆
        try:
            results = await self.vector_db.asimilarity_search(query, k=k)
            if not results:
                return ""
            
            memories = [doc.page_content for doc in results]
            return "\n".join([f"- {m}" for m in memories])
        except Exception as e:
            print(f"Long-term memory retrieval error: {e}")
            return ""

    async def extract_memorable_facts(self, messages: List[BaseMessage], current_summary: str) -> List[str]:
        """
        从对话中提取值得长期记忆的事实。
        """
        if not messages:
            return []
            
        extraction_prompt = """你是一个记忆提取专家。请从以下对话和摘要中提取关于用户的长期偏好、重要事实或关键决策。
请只提取对未来对话有持续参考价值的信息。
如果你发现某些信息已经过时（例如用户改变了主意），请明确指出新的事实。
如果没有发现值得记忆的信息，请返回空列表 []。

输出格式：JSON 字符串列表，例如 ["用户喜欢在春天种植防风草", "用户目前的金钱目标是 10000G"]
"""
        # 取最近的对话片段
        history_text = "\n".join([f"{m.type}: {m.content}" for m in messages[-10:]])
        content = f"Summary: {current_summary}\nRecent History:\n{history_text}"
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=extraction_prompt),
                HumanMessage(content=content)
            ])
            # 解析 JSON 列表
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text.strip("`").strip()
            
            facts = json.loads(text)
            return facts if isinstance(facts, list) else []
        except Exception as e:
            print(f"Memory extraction error: {e}")
            return []

    def persist_memory(self, facts: List[str], conversation_id: str):
        """
        将提取的事实持久化到 ChromaDB。
        """
        if not facts:
            return
            
        documents = []
        for fact in facts:
            documents.append(Document(
                page_content=fact,
                metadata={
                    "conversation_id": conversation_id,
                    "source": "user_memory",
                    "timestamp": json.dumps({"created_at": "now"}) # 占位
                }
            ))
        
        try:
            self.vector_db.add_documents(documents)
            print(f"Successfully persisted {len(documents)} memory items to ChromaDB.")
        except Exception as e:
            print(f"Memory persistence error: {e}")
