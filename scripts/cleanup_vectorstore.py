from vectorstore.query_rag import WikiVectorStore
import os

def remove_crop_calendar_chunks():
    """
    从向量库中删除标题为 '作物生长日历' 的所有切片。
    """
    # 初始化向量库
    vdb_path = "vectorstore/db"
    if not os.path.exists(vdb_path):
        print(f"错误: 向量库目录 {vdb_path} 不存在。")
        return

    vdb = WikiVectorStore(persist_directory=vdb_path)
    
    # 查找标题为 '作物生长日历' 的文档 IDs
    # ChromaDB 的 get 方法支持 metadata 过滤
    target_title = "辣椒"
    
    print(f"正在查找标题为 '{target_title}' 的分块...")
    
    # 使用 collection.get(where={"title": target_title})
    # 注意：这里的 vector_db 是 langchain_chroma.Chroma 对象
    # 它底层封装了 chromadb.Collection
    collection = vdb.vector_db._collection
    results = collection.get(where={"title": target_title,"category":"Multiple harvest crops"})
    
    ids_to_delete = results.get("ids", [])
    
    if not ids_to_delete:
        print(f"未找到标题为 '{target_title}' 的任何分块。")
        return

    print(f"找到 {len(ids_to_delete)} 个分块。正在删除...")
    
    # 执行删除操作
    vdb.vector_db.delete(ids=ids_to_delete)
    
    print(f"成功从向量库中移除标题为 '{target_title}' 的所有内容。")

if __name__ == "__main__":
    remove_crop_calendar_chunks()
