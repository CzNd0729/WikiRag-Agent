import json
import os
from typing import List, Optional
from langchain_core.messages import BaseMessage
from core.llm_provider import get_chat_model, get_embedding_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.prompts import MEMORY_EXTRACTION_PROMPT
# from langchain_chroma import Chroma
# from langchain_core.documents import Document
from sqlalchemy import create_engine, Column, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class UserProfile(Base):
    """PostgreSQL 中的用户画像模型。"""
    __tablename__ = 'user_profiles'
    user_id = Column(String, primary_key=True)
    profile = Column(Text, default="[]") # 存储经过精炼的事实列表

class MemoryManager:
    """
    记忆管理器：
    1. PostgreSQL: 存储持久化的用户画像（跨会话）。
    """
    def __init__(self, persist_directory: str = "vectorstore/db"):
        self.llm = get_chat_model("AGENT_LLM")
        self.embeddings = get_embedding_model()
        self.persist_directory = persist_directory
        
        # 1. 初始化 PostgreSQL
        postgres_url = os.getenv("POSTGRES_URL")
        if postgres_url:
            self.engine = create_engine(postgres_url)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        else:
            self.Session = None
            print("Warning: POSTGRES_URL not set. User profiles will not be persisted to PostgreSQL.")

        # 2. 初始化 ChromaDB (对话历史集合) - 暂时不需要
        # self.vector_db = Chroma(
        #     persist_directory=persist_directory,
        #     embedding_function=self.embeddings,
        #     collection_name="user_chat_history", # 独立于 wiki 知识库
        #     collection_metadata={"hnsw:space": "cosine"}
        # )

    async def get_user_profile(self, user_id: str) -> List[str]:
        """从 PostgreSQL 获取用户画像。"""
        if not self.Session:
            return []
        
        with self.Session() as session:
            user = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if user and user.profile:
                try:
                    return json.loads(user.profile)
                except:
                    return [user.profile]
            return []

    def update_user_profile(self, user_id: str, facts: List[str]):
        """将更新后的用户画像持久化到 PostgreSQL。"""
        if not self.Session:
            return
            
        with self.Session() as session:
            user = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not user:
                user = UserProfile(user_id=user_id)
                session.add(user)
            
            user.profile = json.dumps(facts, ensure_ascii=False)
            session.commit()

    async def retrieve_chat_history(self, query: str, user_id: str, k: int = 5) -> str:
        """
        从 ChromaDB 检索该用户的相关对话历史。- 暂时不需要
        """
        return ""
        # try:
        #     results = await self.vector_db.asimilarity_search(
        #         query, 
        #         k=k, 
        #         filter={"user_id": user_id}
        #     )
        #     if not results:
        #         return ""
        #     
        #     memories = [doc.page_content for doc in results]
        #     return "\n".join([f"- {m}" for m in memories])
        # except Exception as e:
        #     print(f"Chat history retrieval error: {e}")
        #     return ""

    async def extract_memorable_facts(self, messages: List[BaseMessage], current_summary: str) -> List[str]:
        """
        从对话中提取值得长期记忆的事实。
        仅保留用户提问 (HumanMessage) 和 AI 最终回答 (AIMessage)，过滤掉中间过程噪音。
        """
        if not messages:
            return []
            
        # 过滤出原始问题和最终回答
        filtered_history = [
            m for m in messages 
            if isinstance(m, (HumanMessage, AIMessage)) and not getattr(m, "tool_calls", None)
        ]
        
        if not filtered_history:
            return []

        history_text = "\n".join([f"{m.type.upper()}: {m.content}" for m in filtered_history])
        content = f"Context Summary: {current_summary}\nFiltered Conversation:\n{history_text}"
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=MEMORY_EXTRACTION_PROMPT),
                HumanMessage(content=content)
            ])
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

    def persist_chat_history(self, facts: List[str], user_id: str, conversation_id: str):
        """
        将提取的对话事实存入 ChromaDB。- 暂时不需要
        """
        pass
        # if not facts:
        #     return
        #     
        # documents = []
        # for fact in facts:
        #     documents.append(Document(
        #         page_content=fact,
        #         metadata={
        #             "user_id": user_id,
        #             "conversation_id": conversation_id,
        #             "source": "chat_history",
        #             "timestamp": "now"
        #         }
        #     ))
        # 
        # try:
        #     self.vector_db.add_documents(documents)
        #     print(f"Successfully persisted {len(documents)} chat history items for user {user_id} to ChromaDB.")
        # except Exception as e:
        #     print(f"Chat history persistence error: {e}")
