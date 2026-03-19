import requests
from bs4 import BeautifulSoup
import json
import os
import re
from typing import List, Dict, Optional, Set
from datetime import datetime
import argparse
from urllib.parse import urljoin, urlparse
import time

class UniversalWebCrawler:
    """
    通用网页爬虫：从指定的起点 URL 开始，递归抓取同域名下的所有链接。
    """
    def __init__(self, storage_dir: str = "data/raw"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        self.visited_urls = set()
        self.domain = ""

    def is_internal(self, url: str) -> bool:
        """检查 URL 是否属于同一个域名"""
        parsed_url = urlparse(url)
        return parsed_url.netloc == self.domain or parsed_url.netloc == ""

    def get_safe_filename(self, url: str) -> str:
        """从 URL 生成安全的文件名"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        if not path or path == "/":
            return "index.json"
        
        # 移除末尾斜杠
        path = path.strip("/")
        # 替换非法字符
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", path)
        return f"{safe_name}.json"

    def fetch_page(self, url: str) -> Optional[Dict]:
        """抓取网页内容"""
        try:
            print(f"  Fetching: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 检查是否为 HTML
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                print(f"  Skipping non-HTML content: {content_type}")
                return None

            soup = BeautifulSoup(response.text, "lxml")
            title = soup.title.string if soup.title else url
            
            return {
                "title": title.strip(),
                "url": url,
                "html_body": response.text,
                "scraped_at": datetime.now().isoformat(),
                "category": "Web"
            }
        except Exception as e:
            print(f"  Failed to fetch {url}: {e}")
            return None

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """提取页面中所有的内部链接"""
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            # 移除片段标识符
            full_url = full_url.split("#")[0]
            
            if self.is_internal(full_url) and full_url not in self.visited_urls:
                # 排除一些明显不是页面的资源
                if not any(full_url.lower().endswith(ext) for ext in [".pdf", ".jpg", ".png", ".zip", ".docx"]):
                    links.append(full_url)
        return list(set(links))

    def save_raw(self, data: Dict):
        """保存原始数据"""
        category_dir = os.path.join(self.storage_dir, "Universal")
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        filename = self.get_safe_filename(data["url"])
        file_path = os.path.join(category_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {file_path}")

    def crawl(self, start_url: str, max_depth: int = 3, limit: int = 100):
        """递归爬取"""
        self.domain = urlparse(start_url).netloc
        queue = [(start_url, 0)]
        count = 0

        while queue and count < limit:
            current_url, depth = queue.pop(0)
            
            if current_url in self.visited_urls or depth > max_depth:
                continue
            
            self.visited_urls.add(current_url)
            data = self.fetch_page(current_url)
            
            if data:
                self.save_raw(data)
                count += 1
                
                if depth < max_depth:
                    new_links = self.extract_links(data["html_body"], current_url)
                    for link in new_links:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
            
            # 礼貌延迟
            time.sleep(0.5)

class WikiRawCrawler:
    """
    Stage 1: Raw Crawler
    负责从 Stardew Wiki 抓取原始 HTML 并按分类存储。支持递归抓取子分类。
    """
    BASE_URL = "https://stardewvalleywiki.com"
    API_URL = f"{BASE_URL}/mediawiki/api.php"

    def __init__(self, storage_dir: str = "data/raw"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def get_category_pages_recursive(self, category: str, depth: Optional[int] = None, visited_cats: set = None) -> Dict[str, List[str]]:
        """
        递归获取分类及其子分类下的页面标题。
        depth: 递归深度限制。如果为 None，则只要有子分类就一直抓取下去。
        返回 Dict[分类名, 页面标题列表]
        """
        if visited_cats is None:
            visited_cats = set()
        
        # 规范化分类名，防止大小写或空格导致的重复访问
        category_key = category.strip().replace(" ", "_")
        if category_key in visited_cats or (depth is not None and depth < 0):
            return {}
        
        visited_cats.add(category_key)
        print(f"  Fetching Category: {category} (Remaining depth: {depth if depth is not None else 'infinite'})")
        
        results = {category: []}
        subcats = []

        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "max",
            "format": "json"
        }
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "query" not in data or "categorymembers" not in data["query"]:
                return results

            for member in data["query"]["categorymembers"]:
                title = member["title"]
                if title.startswith("Category:"):
                    # 提取子分类名称
                    subcat_name = title.replace("Category:", "").strip()
                    subcats.append(subcat_name)
                elif any(title.startswith(prefix) for prefix in ["File:", "Template:", "Module:", "MediaWiki:", "Talk:"]):
                    continue
                else:
                    results[category].append(title)
            
            # 递归抓取子分类
            if depth is None or depth > 0:
                next_depth = (depth - 1) if depth is not None else None
                for subcat in subcats:
                    # 递归调用并将结果合并到 results 中
                    sub_results = self.get_category_pages_recursive(subcat, next_depth, visited_cats)
                    for k, v in sub_results.items():
                        if k in results:
                            results[k].extend(v)
                        else:
                            results[k] = v
                    
            return results
        except Exception as e:
            print(f"Failed to get category {category}: {e}")
            return results

    def get_all_categories(self) -> List[str]:
        """获取 Wiki 中的所有分类名称"""
        categories = []
        params = {
            "action": "query",
            "list": "allcategories",
            "aclimit": "max",
            "format": "json"
        }
        while True:
            try:
                response = requests.get(self.API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if "query" in data and "allcategories" in data["query"]:
                    for cat in data["query"]["allcategories"]:
                        categories.append(cat["*"])
                if "continue" in data:
                    params.update(data["continue"])
                else:
                    break
            except Exception as e:
                print(f"Failed to get categories: {e}")
                break
        return categories

    def fetch_raw_content(self, title: str, category: str = "Uncategorized") -> Optional[Dict]:
        """获取指定页面的原始 HTML 内容，优先获取中文词条"""
        params = {
            "action": "parse",
            "page": title,
            "format": "json",
            "prop": "text|langlinks",
            "redirects": 1
        }
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                print(f"Error fetching {title}: {data['error']['info']}")
                return None
            
            # 提取中文关联
            zh_title = None
            zh_url = None
            html_body = data["parse"]["text"]["*"]
            final_title = title
            final_url = f"{self.BASE_URL}/{title.replace(' ', '_')}"

            if "langlinks" in data["parse"]:
                for link in data["parse"]["langlinks"]:
                    if link["lang"] == "zh":
                        zh_title = link["*"]
                        zh_url = link.get("url")
                        break
            
            # 如果有中文链接，直接下载该页面内容
            if zh_url:
                try:
                    print(f"  Downloading Chinese page: {zh_title} ({zh_url})")
                    zh_response = requests.get(zh_url, timeout=10)
                    zh_response.raise_for_status()
                    html_body = zh_response.text
                    final_title = zh_title
                    final_url = zh_url
                except Exception as zh_e:
                    print(f"  Failed to download Chinese page for {title}: {zh_e}")

            return {
                "title": final_title,
                "category": category,
                "url": final_url,
                "html_body": html_body,
                "scraped_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Request failed for {title}: {e}")
            return None

    def find_existing_file(self, title: str) -> Optional[str]:
        """全局检查指定标题的文件是否已在任何分类中存在，并返回路径"""
        safe_title = title.replace(" ", "_").replace("/", "_").replace(":", "_").replace("?", "_")
        filename = f"{safe_title}.json"
        for root, dirs, files in os.walk(self.storage_dir):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def save_raw(self, data: Dict):
        """按分类存储为 JSON，如果已存在则合并 category"""
        new_category = data.get("category", "Uncategorized")
        title = data["title"]
        
        existing_path = self.find_existing_file(title)
        
        if existing_path:
            # 合并逻辑
            with open(existing_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            
            old_categories = existing_data.get("category", "Uncategorized")
            # 统一转为列表处理
            if isinstance(old_categories, str):
                cat_list = [c.strip() for c in old_categories.split(",")]
            else:
                cat_list = old_categories
            
            if new_category not in cat_list:
                cat_list.append(new_category)
                existing_data["category"] = ", ".join(cat_list) # 以逗号分隔存储
                with open(existing_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                print(f"Updated categories for '{title}' in {existing_path}: {existing_data['category']}")
            else:
                print(f"'{title}' already has category '{new_category}', skipping update.")
        else:
            # 常规保存逻辑
            safe_category = re.sub(r'[\\/*?:"<>|]', "_", new_category)
            category_dir = os.path.join(self.storage_dir, safe_category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)

            safe_title = title.replace(" ", "_").replace("/", "_").replace(":", "_").replace("?", "_")
            file_path = os.path.join(category_dir, f"{safe_title}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved raw data to {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 1: Raw Crawler")
    parser.add_argument("--category", type=str, help="Wiki category to fetch")
    parser.add_argument("--all", action="store_true", help="Fetch priority categories")
    parser.add_argument("--depth", type=int, help="Recursion depth for subcategories (None for infinite)")
    parser.add_argument("--limit", type=int, help="Limit number of pages PER category")
    parser.add_argument("--force", action="store_true", help="Force re-download even if title was seen in current run")
    args = parser.parse_args()

    crawler = WikiRawCrawler()
    scraped_titles = set()

    # 确定抓取起点
    start_categories = []
    if args.all:
        print("--- Stage 1: Raw (Priority Categories with recursion) ---")
        # 核心分类清单
        # start_categories = [
        #     "Crops", "NPCs", "Artisan Goods", "Fish", "Mining", 
        #     "Skills", "Bundles", "Locations", "Monsters", "Game mechanics", "Gameplay"
        # ]
        start_categories = [
            "NPCs","Game mechanics","Gameplay","Festivals","Seasons"
        ]
    else:
        start_categories = [args.category or "Crops"]

    for start_cat in start_categories:
        print(f"Starting recursive fetch from Category: {start_cat} (Depth: {args.depth})")
        cat_map = crawler.get_category_pages_recursive(start_cat, depth=args.depth)
        
        for cat_name, pages in cat_map.items():
            if not pages: continue
            print(f"  > Category '{cat_name}' has {len(pages)} pages.")
            
            count = 0
            for title in pages:
                if args.limit and count >= args.limit: break
                
                # 运行时去重检查
                if not args.force and title in scraped_titles:
                    continue
                
                # 跨运行/全局重复检查
                existing_path = crawler.find_existing_file(title)
                if not args.force and existing_path:
                    # 如果已经存在，我们依然尝试“保存”，让 save_raw 处理元数据合并
                    # 这样可以更新 category 标签而不需要重新 fetch_raw_content
                    # 构造一个极简数据用于合并
                    minimal_data = {"title": title, "category": cat_name}
                    crawler.save_raw(minimal_data)
                    scraped_titles.add(title)
                    count += 1
                    continue
                
                data = crawler.fetch_raw_content(title, category=cat_name)
                if data:
                    crawler.save_raw(data)
                    scraped_titles.add(title)
                    count += 1
