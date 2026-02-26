from langchain_text_splitters import MarkdownTextSplitter

# 统一的分块配置，适配 512 token 限制的模型 (如 bge-large-zh-v1.5)
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50

# 向量库单次提交的最大 batch size
MAX_BATCH_SIZE = 32

def get_markdown_splitter():
    """获取统一配置的 MarkdownTextSplitter 实例"""
    return MarkdownTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
