from bs4 import BeautifulSoup
import json
import os
import re
import argparse

class WikiProcessor:
    """
    Stage 2: Process
    负责将 Raw HTML 转换为清洗后的 Markdown。
    """
    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)

    def html_to_markdown(self, html_content: str) -> str:
        """提取正文并转为 Markdown，移除目录和冗余元素"""
        soup = BeautifulSoup(html_content, "lxml")
        
        # 彻底清除目录和浮动容器
        for element in list(soup.find_all(True)):
            if not element.parent: continue
            
            # 检查 TOC class/id
            classes = element.get('class', [])
            if classes and isinstance(classes, str): classes = [classes]
            if (classes and 'toc' in classes) or element.get('id') == 'toc':
                element.decompose()
                continue
            
            # 检查标题中的 Contents/目录
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                text = element.get_text().strip()
                if re.search(r'^(Contents|目录)$', text, re.I):
                    container = element
                    while container.parent and container.parent.name not in ['body', '[document]', 'html']:
                        parent = container.parent
                        style = str(parent.get('style', ''))
                        p_classes = parent.get('class', [])
                        if p_classes and isinstance(p_classes, str): p_classes = [p_classes]
                        if 'float' in style or (p_classes and ('toc' in p_classes or 'toctitle' in p_classes)):
                            container = parent
                        else:
                            break
                    if container == element:
                        next_node = element.find_next_sibling()
                        if next_node and next_node.name in ['ul', 'ol']:
                            next_node.decompose()
                    container.decompose()

        # 移除编辑链接和不需要的标签
        for edit_section in soup.find_all('span', class_='mw-editsection'):
            edit_section.decompose()
        for element in soup(["script", "style", "table", "div.mw-references-wrap", ".mw-empty-elt"]):
            element.decompose()
            
        markdown_parts = []
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
            content = element.get_text().strip()
            if not content: continue
            if element.name == 'h1': markdown_parts.append(f"# {content}")
            elif element.name == 'h2': markdown_parts.append(f"## {content}")
            elif element.name == 'h3': markdown_parts.append(f"### {content}")
            elif element.name == 'li': markdown_parts.append(f"* {content}")
            else: markdown_parts.append(content)
                    
        return "\n\n".join(markdown_parts)

    def process_all(self):
        """递归处理 data/raw 下的所有 JSON 文件"""
        if not os.path.exists(self.raw_dir): return

        for root, dirs, files in os.walk(self.raw_dir):
            for filename in files:
                if filename.endswith(".json"):
                    raw_path = os.path.join(root, filename)
                    with open(raw_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    
                    category = raw_data.get("category", "Uncategorized")
                    target_dir = os.path.join(self.processed_dir, category)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)

                    print(f"Processing {category}/{filename}...")
                    markdown = self.html_to_markdown(raw_data["html_body"])
                    
                    header = f"---\ntitle: {raw_data['title']}\ncategory: {category}\nurl: {raw_data['url']}\nscraped_at: {raw_data['scraped_at']}\n---\n\n"
                    
                    md_path = os.path.join(target_dir, filename.replace(".json", ".md"))
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(header + markdown)

if __name__ == "__main__":
    processor = WikiProcessor()
    processor.process_all()
    print("--- Stage 2 Complete ---")
