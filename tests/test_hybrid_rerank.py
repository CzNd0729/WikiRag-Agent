from vectorstore.query_rag import WikiVectorStore
import sys

def test_hybrid_search_interactive():
    print("正在初始化向量库...")
    try:
        store = WikiVectorStore()
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    print("=== 混合搜索 (Hybrid Search) + 重排序 (Rerank) 交互式测试 ===")
    print("输入 'exit' 或 'quit' 退出")
    
    while True:
        try:
            query = input("\n请输入查询问题: ").strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit']:
                break
            
            print(f"正在搜索: {query}...")
            # 使用 hybrid_search_with_rerank 方法
            results = store.hybrid_search_with_rerank(query, k=5)
            
            if not results:
                print("未找到相关结果。")
                continue

            for i, doc in enumerate(results):
                source = doc.metadata.get('source', 'unknown')
                content = doc.page_content.replace('\n', ' ')
                print(f"\n{i+1}. [来源: {source}]")
                print(f"   内容: {content}...")
            print("-" * 50)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"搜索出错: {e}")

if __name__ == "__main__":
    test_hybrid_search_interactive()
