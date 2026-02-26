from bs4 import BeautifulSoup
import json
import os
import re
import argparse
from markdownify import markdownify as md

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
        """提取正文并转为 Markdown，保留表格，移除冗余元素"""
        soup = BeautifulSoup(html_content, "lxml")
        
        # 0. 尝试只提取正文容器内容，如果存在
        # MediaWiki 的正文通常在 #mw-content-text 或 #content 中
        content_div = soup.select_one("#mw-content-text") or soup.select_one("#content")
        if content_div:
            # 使用 content_div 作为新的 soup 根，但这可能会丢失标题
            # 为了保留标题，我们可以只移除已知的侧边栏和页眉页脚
            pass

        # 1. 预清洗：移除绝对不需要的元素
        # 移除“作物生长日历”板块及其表格
        # 在星露谷 Wiki 中，这通常是一个 span id="作物生长日历" 后面紧跟一个表格
        for header in soup.find_all(['h2', 'h3', 'h4']):
            if "作物生长日历" in header.get_text():
                # 寻找接下来的表格或特定容器并移除
                curr = header.next_sibling
                while curr:
                    next_node = curr.next_sibling
                    # 如果遇到了下一个同级标题，停止移除
                    if curr.name in ['h2', 'h3', 'h4']:
                        break
                    curr.extract()
                    curr = next_node
                header.decompose()

        # 移除编辑链接
        for edit_section in soup.find_all('span', class_='mw-editsection'):
            edit_section.decompose()
            
        # 移除脚本、样式、空元素、引用包装、侧边栏/导航等
        bad_selectors = [
            "script", "style", ".mw-empty-elt", "div.mw-references-wrap",
            "#toc", ".toc", ".navbox", "#navbox", ".catlinks", "#footer", "#header",
            "#mw-navigation", "#mw-head", "#mw-panel", "#p-navigation", "#p-tb", "#p-lang",
            ".printfooter", ".noprint", "#p-personal", "#p-search", "#p-cactions", "#p-variants", "#p-views",
            "#siteSub", "#contentSub", "#jump-to-nav",
            ".mw-jump-link"
        ]
        for selector in bad_selectors:
            for element in soup.select(selector):
                element.decompose()

        # 2. 特殊处理：将 img 转换为 [Alt文本] 或 [文件名]
        for img in soup.find_all('img'):
            alt = img.get('alt', '').strip()
            if not alt:
                src = img.get('src', '')
                alt = os.path.basename(src).split('?')[0] if src else 'Image'
            
            # 替换为文本节点
            img.replace_with(f"[{alt}]")

        # 3. 使用 markdownify 进行转换
        # 我们不再 strip 'img'，因为我们已经手动处理了它们
        content_markdown = md(
            str(soup),
            heading_style="ATX",
            newline_style="BACKSLASH",
            strip=['script', 'style', 'a', 'form', 'input', 'button'], # 移除干扰 RAG 的标签
        )

        # 4. 后处理
        # 清理 data-sort-value (Wiki 常见的冗余属性)
        content_markdown = re.sub(r'data-sort-value="[^"]*"', '', content_markdown)
        
        # 针对 MediaWiki 的一些残留文本进行清理
        content_markdown = content_markdown.replace("跳到导航", "").replace("跳到搜索", "")
        content_markdown = content_markdown.replace("来自Stardew Valley Wiki", "")
        
        # 清理多余空行
        content_markdown = re.sub(r'\n{3,}', '\n\n', content_markdown)
        content_markdown = content_markdown.strip()
                    
        return content_markdown

    def process_file(self, raw_path: str):
        """处理单个 JSON 文件"""
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        # 兼容处理：category 可能已经是逗号分隔的字符串
        raw_category = raw_data.get("category", "Uncategorized")
        if isinstance(raw_category, str):
            first_category = raw_category.split(",")[0].strip()
        else:
            first_category = "Uncategorized"

        target_dir = os.path.join(self.processed_dir, first_category)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        print(f"Processing {first_category}/{os.path.basename(raw_path)}...")
        markdown = self.html_to_markdown(raw_data["html_body"])
        
        # 构建元数据头部
        header_lines = [
            "---",
            f"title: {raw_data['title']}",
            f"category: {raw_category}",
            f"url: {raw_data['url']}"
        ]
        
        # 如果存在旧版本的 zh_title 或 zh_url，依然可以兼容显示，但新抓取的数据已经合并到 title/url 中
        if raw_data.get("zh_title"):
            header_lines.append(f"zh_title: {raw_data['zh_title']}")
        if raw_data.get("zh_url"):
            header_lines.append(f"zh_url: {raw_data['zh_url']}")
            
        header_lines.append(f"scraped_at: {raw_data['scraped_at']}")
        header_lines.append("---\n\n")
        
        header = "\n".join(header_lines)
        
        md_filename = os.path.basename(raw_path).replace(".json", ".md")
        md_path = os.path.join(target_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(header + markdown)

    def process_all(self, target_file: str = None):
        """递归处理 data/raw 下的所有 JSON 文件，或处理指定文件"""
        if not os.path.exists(self.raw_dir): return

        for root, dirs, files in os.walk(self.raw_dir):
            for filename in files:
                if filename.endswith(".json"):
                    # 允许 target_file 匹配文件名的一部分，方便调试
                    if target_file and target_file not in filename:
                        continue
                    
                    raw_path = os.path.join(root, filename)
                    self.process_file(raw_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Specific JSON file to process (filename only or with .json)")
    args = parser.parse_args()

    processor = WikiProcessor()
    processor.process_all(target_file=args.file)
    print("--- Stage 2 Complete ---")
