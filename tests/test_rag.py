import os
import sys
from dotenv import load_dotenv


from vectorstore.query_rag import WikiVectorStore

def run_test():
    load_dotenv()
    print("正在初始化 Wiki 向量库 (SiliconFlow BAAI/bge-m3)...")
    
    try:
        vdb = WikiVectorStore()
        
        print("\n--- WikiRag-Agent 向量搜索测试 (Top 30) ---")
        print("输入 'exit' 或 'quit' 退出")
        
        while True:
            query = input("\n请输入您的测试问题: ").strip()
            
            if not query:
                continue
            if query.lower() in ['exit', 'quit']:
                break
            
            print(f"\n正在执行向量搜索: '{query}'...")
            
            # 仅查看向量匹配召回的结果，返回 top 30 并标注相似度
            scored_results = vdb.similarity_search_with_score(query, k=30)
            
            if not scored_results:
                print("未找到匹配结果。")
                continue
            
            print(f"找到 {len(scored_results)} 条相关结果 (向量检索 Top 30):\n" + "="*50)
            
            for i, (doc, score) in enumerate(scored_results):
                title = doc.metadata.get("title", "未知标题")
                category = doc.metadata.get("category", "未知分类")
                # 优先显示原始 Markdown 文本
                original_md = doc.metadata.get("original_markdown")
                
                print(f"结果 #{i+1:2d} | 得分: {score:.4f} | [{category}] {title}")
                content_preview = doc.page_content.replace("\n", " ") + "..."
                print(f"检索内容预览: {content_preview}")
                print("-" * 50)
                
    except Exception as e:
        print(f"初始化或运行过程中出错: {e}")

if __name__ == "__main__":
    run_test()
