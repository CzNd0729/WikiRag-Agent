import os
import argparse
from vectorstore.query_rag import WikiVectorStore

class WikiIndexer:
    """
    Stage 3: Index
    负责将清洗后的 Markdown 文件进行分块并存入向量库。
    """
    def __init__(self, processed_dir: str = "data/processed"):
        self.processed_dir = processed_dir
        self.vdb = WikiVectorStore()

    def index_all(self, limit: int = None):
        """递归读取 data/processed 下的文件并存入向量库"""
        if not os.path.exists(self.processed_dir):
            print(f"Directory {self.processed_dir} not found.")
            return

        count = 0
        for root, dirs, files in os.walk(self.processed_dir):
            for filename in files:
                if filename.endswith(".md"):
                    if limit and count >= limit:
                        print(f"Reached limit of {limit} files.")
                        return
                    
                    md_path = os.path.join(root, filename)
                    category = os.path.basename(root)
                    
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    title = filename.replace(".md", "").replace("_", " ")
                    metadata = {
                        "title": title,
                        "category": category,
                        "source": md_path
                    }
                    
                    print(f"Indexing {category}/{filename}...")
                    self.vdb.add_documents(content, metadata)
                    count += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3: Indexer")
    parser.add_argument("--limit", type=int, help="Limit number of files to index")
    args = parser.parse_args()

    indexer = WikiIndexer()
    indexer.index_all(limit=args.limit)
    print("--- Stage 3 Complete ---")
