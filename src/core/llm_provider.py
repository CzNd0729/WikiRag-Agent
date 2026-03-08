import os
import requests
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class SiliconFlowEmbeddings(Embeddings):
    """
    自定义 SiliconFlow Embedding 类。
    直接通过 requests 调用以确保与 test.py 一致，并支持 Qwen3/BGE 指令前缀。
    """
    def __init__(self, model: str, api_key: str, api_base: str):
        self.model = model
        self.api_key = api_key
        self.url = f"{api_base.rstrip('/')}/embeddings"
        
        # 判断是否为 Qwen 系列模型
        self.is_qwen = "qwen" in model.lower()

    def _get_embedding(self, text: str, is_query: bool = True) -> List[float]:
        # 为 Qwen 系列模型添加检索指令
        prefix = ""
        if self.is_qwen:
            prefix = "Queries: " if is_query else "Documents: "
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": f"{prefix}{text}",
            "encoding_format": "float"
        }
        
        response = requests.post(self.url, json=payload, headers=headers)
        if response.status_code == 200:
            # 硅基流动返回向量是归一化过的 (Norm=1.0)
            return response.json()['data'][0]['embedding']
        else:
            raise Exception(f"SiliconFlow API Error: {response.status_code} - {response.text}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """实现 LangChain 要求的 embed_documents"""
        return [self._get_embedding(t, is_query=False) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """实现 LangChain 要求的 embed_query"""
        return self._get_embedding(text, is_query=True)

def get_chat_model(model_key: str = "AGENT_LLM"):
    """
    根据环境变量键名获取 ChatOpenAI 实例。
    """
    model = os.getenv(f"{model_key}_MODEL")
    api_key = os.getenv(f"{model_key}_API_KEY")
    api_base = os.getenv(f"{model_key}_API_BASE")
    
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=api_base,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}} if "deepseek" in model.lower() or "qwen" in model.lower() else {}
    )

def get_embedding_model():
    """
    从环境变量获取 Embedding 模型。
    切换到自定义 SiliconFlowEmbeddings 以确保一致性和指令前缀支持。
    """
    return SiliconFlowEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
        api_key=os.getenv("EMBEDDING_API_KEY"),
        api_base=os.getenv("EMBEDDING_API_BASE")
    )
