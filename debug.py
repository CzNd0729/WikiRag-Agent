import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_ollama import OllamaEmbeddings

# --- 1. 初始化 Ollama Embedding 模型 ---
# 关键点：显式提供 http://，并指定支持多语言的模型（如 bge-m3）
try:
    embeddings_model = OllamaEmbeddings(
        model="bge-m3",
        base_url="http://localhost:11434",
    )
    print("✅ 模型初始化成功！")
except Exception as e:
    print(f"❌ 模型初始化失败，请检查 Ollama 是否启动: {e}")
    exit()

# --- 2. 定义跨语言测试文本 ---
# 这里测试两个语义非常接近但语言不同的短语
text_en = "Star Dew Valley is an excellent farm simulation game."
text_zh = "星露谷物语是一款非常出色的农场模拟游戏。"

print("-" * 30)
print(f"📄 待测试文本（英文）: {text_en}")
print(f"📄 待测试文本（中文）: {text_zh}")
print("-" * 30)

# --- 3. 计算向量 ---
try:
    print("⏳ 正在计算中文文本向量...")
    vector_zh = embeddings_model.embed_query(text_zh)
    
    print("⏳ 正在计算英文文本向量...")
    vector_en = embeddings_model.embed_query(text_en)
    
    print("✅ 向量计算完成。")
except Exception as e:
    print(f"❌ 向量计算失败: {e}")
    exit()

# --- 4. 计算余弦相似度 ---
# 余弦相似度的结果在 [-1, 1] 之间，越接近 1 说明语义越相似。
# 跨语言模型通常能达到 0.7 - 0.9 以上。

# 需要将向量转换为符合 scikit-learn 要求的 2D 数组格式: [1, n_features]
vec_zh_2d = np.array(vector_zh).reshape(1, -1)
vec_en_2d = np.array(vector_en).reshape(1, -1)

# 计算相似度
similarity_score = cosine_similarity(vec_zh_2d, vec_en_2d)[0][0]

print("-" * 30)
print(f"📊 跨语言语义相似度得分: {similarity_score:.4f}")

if similarity_score > 0.8:
    print("✨ 测试结果：模型成功识别了两种语言的极高语义相关性。")
elif similarity_score > 0.5:
    print("👍 测试结果：模型识别到了语义相关性，但不够精准。")
else:
    print("⚠️ 测试结果：模型对这两种语言的语义映射存在较大差异，不推荐用于此类跨语言任务。")
print("-" * 30)