import os
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

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
    """
    return OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
        openai_api_key=os.getenv("EMBEDDING_API_KEY"),
        openai_api_base=os.getenv("EMBEDDING_API_BASE"),
        chunk_size=64
    )
