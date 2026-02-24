import requests
from bs4 import BeautifulSoup
import json
import os
import re
from typing import List, Dict, Optional
from datetime import datetime
import argparse

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

    def file_exists(self, title: str, category: str) -> bool:
        """检查指定标题的文件是否已存在"""
        safe_category = re.sub(r'[\\/*?:"<>|]', "_", category)
        safe_title = title.replace(" ", "_").replace("/", "_").replace(":", "_").replace("?", "_")
        file_path = os.path.join(self.storage_dir, safe_category, f"{safe_title}.json")
        return os.path.exists(file_path)

    def save_raw(self, data: Dict):
        """按分类存储为 JSON"""
        category = data.get("category", "Uncategorized")
        # 清理分类名中的非法字符（用于文件夹名）
        safe_category = re.sub(r'[\\/*?:"<>|]', "_", category)
        category_dir = os.path.join(self.storage_dir, safe_category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        safe_title = data["title"].replace(" ", "_").replace("/", "_").replace(":", "_").replace("?", "_")
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
        start_categories = [
            "Crops", "Villagers", "Artisan Goods", "Fish", "Mining", 
            "Skills", "Bundles", "Locations", "Monsters", "Quests", "Events"
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
                
                # 跨运行文件检查：如果非 force 模式且文件已存在，则跳过
                if not args.force and crawler.file_exists(title, category=cat_name):
                    print(f"  Skipping '{title}' (already exists in {cat_name})")
                    scraped_titles.add(title)
                    count += 1
                    continue
                
                data = crawler.fetch_raw_content(title, category=cat_name)
                if data:
                    crawler.save_raw(data)
                    scraped_titles.add(title)
                    count += 1
