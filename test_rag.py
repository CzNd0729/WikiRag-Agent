import os
import sys
from dotenv import load_dotenv


from vectorstore.query_rag import WikiVectorStore

def run_test():
    load_dotenv()
    print("正在初始化 Wiki 向量库 (SiliconFlow BAAI/bge-m3)...")
    
    try:
        vdb = WikiVectorStore()
        # 初始化混合检索器
        retriever = vdb.get_hybrid_retriever(k=4)
        
        print("\n--- Sentinel-Wiki 检索测试已就绪 ---")
        print("输入 'exit' 或 'quit' 退出")
        
        while True:
            query = input("\n请输入您的测试问题: ").strip()
            
            if not query:
                continue
            if query.lower() in ['exit', 'quit']:
                break
            
            print(f"\n正在搜索: '{query}'...")
            
            # 使用混合检索器进行检索
            results = retriever.invoke(query)
            
            if not results:
                print("未找到匹配结果。")
                continue
            
            print(f"找到 {len(results)} 条相关结果:\n" + "="*50)
            
            for i, doc in enumerate(results):
                title = doc.metadata.get("title", "未知标题")
                category = doc.metadata.get("category", "未知分类")
                
                print(f"结果 #{i+1} | [{category}] {title}")
                # 打印前 200 个字符
                content_preview = doc.page_content.replace("\n", " ")[:200] + "..."
                print(f"内容预览: {content_preview}")
                print("-" * 50)
                
    except Exception as e:
        print(f"初始化或运行过程中出错: {e}")

if __name__ == "__main__":
    run_test()
