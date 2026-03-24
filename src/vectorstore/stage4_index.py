import os
import time
import argparse
import shutil
import asyncio
from typing import List, Dict
from vectorstore.query_rag import WikiVectorStore
from vectorstore import CHUNK_SIZE

class WikiIndexer:
    """
    Stage 4: Index
    负责读取分块后的 Markdown 文件并存入向量库。
    已升级为异步版本，支持 RPM 和 TPM 限制。
    """
    def __init__(self, chunked_dir: str = "data/chunked"):
        self.chunked_dir = chunked_dir
        self.vdb = WikiVectorStore()
        self.CHUNK_SEPARATOR = "<!-- CHUNK_START -->"
        
        # 限制条件
        self.MAX_RPM = 2000
        self.MAX_TPM = 500000
        self.semaphore = asyncio.Semaphore(50) # 并发任务数限制，防止本地句柄过载
        
        # 统计
        self.request_count = 0
        self.token_count = 0
        self.start_time = time.time()

    async def _rate_limit_check(self, tokens_to_add: int):
        """简单的速率限制检查"""
        while True:
            elapsed = time.time() - self.start_time
            if elapsed >= 60:
                # 每分钟重置计数
                self.request_count = 0
                self.token_count = 0
                self.start_time = time.time()
            
            if self.request_count + 1 <= self.MAX_RPM and self.token_count + tokens_to_add <= self.MAX_TPM:
                self.request_count += 1
                self.token_count += tokens_to_add
                break
            
            # 等待一段时间后重试
            await asyncio.sleep(1)

    async def index_file(self, md_path: str, category: str, filename: str):
        """异步索引单个文件"""
        async with self.semaphore:
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 尝试提取 YAML 元数据
                import re
                yaml_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, flags=re.DOTALL)
                yaml_metadata = {}
                if yaml_match:
                    yaml_str = yaml_match.group(1)
                    for line in yaml_str.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            yaml_metadata[k.strip()] = v.strip()
                    # 移除 YAML 部分进行分块处理
                    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

                chunks = [c.strip() for c in content.split(self.CHUNK_SEPARATOR) if c.strip()]
                if not chunks:
                    return

                # 估算 token (粗略按字符数/2 估算，确保安全边际)
                estimated_tokens = sum(len(c) for c in chunks) // 2
                await self._rate_limit_check(estimated_tokens)

                title = yaml_metadata.get("title") or filename.replace(".md", "").replace("_", " ")
                metadata = {
                    "title": title,
                    "category": yaml_metadata.get("category") or category,
                    "url": yaml_metadata.get("url", ""),
                    "source": md_path.replace("data/chunked", "data/processed")
                }
                
                print(f"Indexing {category}/{filename} ({len(chunks)} chunks, ~{estimated_tokens} tokens)...")
                
                # 重试逻辑
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        await self.vdb.aadd_prechunked_documents(chunks, metadata)
                        return
                    except Exception as e:
                        if "rate_limit" in str(e).lower() or attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            print(f"Error indexing {filename}: {e}. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"Failed to index {filename} after {max_retries} attempts: {e}")
            except Exception as e:
                print(f"Unexpected error processing {filename}: {e}")

    async def index_all(self, limit: int = None, reset: bool = False):
        """递归读取 data/chunked 下的文件并异步存入向量库"""
        if reset:
            db_path = self.vdb.persist_directory
            if os.path.exists(db_path):
                print(f"Resetting vector store: Removing {db_path}...")
                shutil.rmtree(db_path)
            # 重新初始化 vdb 以创建空的数据库
            self.vdb = WikiVectorStore(persist_directory=db_path)

        if not os.path.exists(self.chunked_dir):
            print(f"Directory {self.chunked_dir} not found. Please run Stage 3 (chunking) first.")
            return

        tasks = []
        count = 0
        for root, dirs, files in os.walk(self.chunked_dir):
            for filename in files:
                if filename.endswith(".md"):
                    if limit and count >= limit:
                        break
                    
                    md_path = os.path.join(root, filename)
                    category = os.path.basename(root)
                    tasks.append(self.index_file(md_path, category, filename))
                    count += 1
            if limit and count >= limit:
                break

        print(f"Starting async indexing for {len(tasks)} files...")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 4: Async Indexer")
    parser.add_argument("--limit", type=int, help="Limit number of files to index")
    parser.add_argument("--reset", action="store_true", help="Reset (delete) the existing vector database before indexing")
    args = parser.parse_args()

    indexer = WikiIndexer()
    asyncio.run(indexer.index_all(limit=args.limit, reset=args.reset))
    print("--- Stage 4 Complete: Async indexing finished ---")
