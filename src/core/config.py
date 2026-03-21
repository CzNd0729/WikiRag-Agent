from pydantic import BaseModel, Field

class RAGConfig(BaseModel):
    """RAG 检索相关配置参数。"""
    
    # 混合检索权重 (BM25 vs Vector)
    bm25_weight: float = Field(default=0.3, description="BM25 检索结果的权重。")
    vector_weight: float = Field(default=0.7, description="向量检索结果的权重。")
    
    # 粗检索 (Initial Search) 参数
    initial_top_k: int = Field(default=10, description="在重排序之前召回的初始文档数量。")
    
    # 最终结果 (Final Rerank) 参数
    final_top_k: int = Field(default=3, description="经过重排序后返回给 Agent 的最终文档数量。")

# 默认配置实例
DEFAULT_RAG_CONFIG = RAGConfig()
