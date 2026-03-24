import os
import re
import argparse
from typing import List
from langchain_core.documents import Document
from vectorstore import get_markdown_splitter, CHUNK_SIZE

class WikiChunker:
    """
    Stage 3: Chunking
    负责将清洗后的 Markdown 文件进行分块，并在分块间插入标识符。
    分块结果（清洗后的文本）存储在 data/chunked 文件夹中，以便于观察和后续索引。
    """
    def __init__(self, processed_dir: str = "data/processed", chunked_dir: str = "data/chunked"):
        self.processed_dir = processed_dir
        self.chunked_dir = chunked_dir
        # 与原 WikiVectorStore 保持一致的配置
        self.text_splitter = get_markdown_splitter()
        self.CHUNK_SEPARATOR = "\n\n<!-- CHUNK_START -->\n\n"

    def _clean_markdown(self, text: str) -> str:
        """
        清洗 Markdown 标记，保留核心文本。
        更激进的策略：完全移除表格。
        """
        # 0. 移除维基冗余标题 (例如: "西鲱 - 星露谷物语官方中文维基" 或 "夏威夷宴会 - Stardew Valley Wiki")
        # 同时尝试移除页面开头重复出现的单个标题行
        text = re.sub(r'.*? [\-–—] (?:星露谷物语官方中文维基|Stardew Valley Wiki)\s*', '', text)
        
        # 1. 移除页面开头可能重复的标题 (匹配第一行，如果它只包含标题词)
        # 在移除维基后缀后，第一行可能就是孤立的名称
        lines = [line for line in text.split('\n') if line.strip()]
        if lines:
            first_line = lines[0].strip()
            # 如果第一行很短（通常是鱼名或物品名），则移除它
            if len(first_line) < 10:
                text = '\n'.join(lines[1:])
            else:
                text = '\n'.join(lines)

        # 2. 完全移除 Markdown 表格 (匹配包含 | 的行)
        # 匹配逻辑：找到所有包含 | 的行并移除
        text = re.sub(r'(?m)^.*\|.*$\n?', '', text)

        # 2. 移除图片占位符 [xxx.png], [xxx.jpg] 等 (支持文件名中包含空格和点号，如 [Farming Skill Icon.png])
        text = re.sub(r'\[[^\]]*?\.(?:png|jpg|jpeg|gif|bmp|svg|webp)\]', '', text, flags=re.IGNORECASE)
        
        # 3. 移除链接标记，保留文本 [text](url) -> text
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

        # 3.5 移除维基引用标记 (例如: [1], [2])
        text = re.sub(r'\[\d+\]', '', text)
        
        # 4. 移除加粗、斜体等标记 **, __, *, _
        text = re.sub(r'(\*\*|__|\*|_)', '', text)
        
        # 5. 移除标题符号 #
        text = re.sub(r'#+\s*', '', text)
        
        # 6. 移除代码块和行内代码
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        
        # 7. 移除 HTML 标签
        text = re.sub(r'<.*?>', '', text)
        
        # 8. 移除多余空白
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def split_and_clean_content(self, text: str) -> List[str]:
        """
        按照 ## 二级标题进行分块。
        1. 每个 ## 标题及其正文为一个初步分块。
        2. 如果初步分块清洗后正文为空，则丢弃。
        3. 对每个初步分块使用 MarkdownTextSplitter 进行最终切分，严格遵守 CHUNK_SIZE。
        """
        # 使用正则表达式匹配所有的 ## 标题
        sections = re.split(r'(?m)^(##\s+.*$)', text)
        
        raw_segments = []
        if sections[0].strip():
            raw_segments.append(("", sections[0].strip()))
            
        for i in range(1, len(sections), 2):
            # 提取并清洗标题
            raw_title = sections[i].replace('##', '').strip()
            title = self._clean_markdown(raw_title)
            content = sections[i+1] if i+1 < len(sections) else ""
            raw_segments.append((title, content.strip()))
            
        final_clean_chunks = []
        # 使用统一配置的 CHUNK_SIZE

        for title, content in raw_segments:
            # 1. 初步清洗
            content_cleaned = re.sub(r'(\*\*|__|\*|_)', '', content)
            content_cleaned = re.sub(r'###+\s*', '', content_cleaned)
            content_cleaned = re.sub(r'(?m)^.*\|.*$\n?', '', content_cleaned)

            # 2. 执行完整的清洗策略
            cleaned_content = self._clean_markdown(content_cleaned)
            
            # 3. 激进的空内容检测
            meaningless_patterns = [
                r'任务\s*\\\s*产物',
                r'任务\s*\\\\\s*产物',
                r'任务', r'产物', r'地图', r'送礼', r'收集包', r'配方', r'鱼塘', r'历史'
            ]
            filtered_text = cleaned_content
            for pattern in meaningless_patterns:
                filtered_text = re.sub(pattern, '', filtered_text).strip()
            filtered_text = re.sub(r'[\\/\-]', ' ', filtered_text).strip()
            
            # 如果正文清洗后为空或不足 15 字符，丢弃
            if not filtered_text or len(filtered_text) < 15:
                continue
            
            # 4. 构造完整分块并使用 text_splitter 兜底
            prefix = f"{title}: " if title else ""
            formatted_chunk = f"{prefix}{cleaned_content}"
            
            # 使用官方 splitter 严格限制长度
            sub_chunks = self.text_splitter.split_text(formatted_chunk)
            for sub in sub_chunks:
                # 对切分出来的每个子块也进行空检查
                temp_sub = sub
                for pattern in meaningless_patterns:
                    temp_sub = re.sub(pattern, '', temp_sub).strip()
                if len(temp_sub) >= 15:
                    final_clean_chunks.append(sub.strip())

        return final_clean_chunks

    def chunk_all(self, limit: int = None):
        """递归读取 data/processed 下的文件并分块（清洗后）存入 data/chunked"""
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
                    relative_path = os.path.relpath(root, self.processed_dir)
                    target_dir = os.path.join(self.chunked_dir, relative_path)
                    
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 提取 YAML Front-matter 元数据
                    yaml_match = re.search(r'^(---\s*\n.*?\n---\s*\n)', content, flags=re.DOTALL)
                    yaml_header = yaml_match.group(1) if yaml_match else ""
                    
                    # 剥离元数据进行分块
                    clean_content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
                    
                    print(f"Chunking and cleaning {relative_path}/{filename}...")
                    clean_chunks = self.split_and_clean_content(clean_content)
                    
                    if clean_chunks:
                        # 在清洗后的分块间加入标识符存入新文件，保留原始 YAML Header
                        chunked_content = self.CHUNK_SEPARATOR.join(clean_chunks)
                        final_content = yaml_header + "<!-- CHUNK_START -->\n\n" + chunked_content
                        
                        target_path = os.path.join(target_dir, filename)
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(final_content)
                    
                    count += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3: Chunker")
    parser.add_argument("--limit", type=int, help="Limit number of files to chunk")
    args = parser.parse_args()

    chunker = WikiChunker()
    chunker.chunk_all(limit=args.limit)
    print("--- Stage 3 Complete: Cleaned chunks saved in data/chunked ---")
