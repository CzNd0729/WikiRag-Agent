import os
import argparse
import sys

# 确保可以导入当前目录下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_stage1(category=None, all_pages=False, limit=None):
    from stage1_raw import WikiRawCrawler
    crawler = WikiRawCrawler()
    if all_pages:
        print("--- Running Stage 1: ALL Pages ---")
        target_categories = ["Crops", "Villagers", "Events", "Items", "Quests", "Bundles", "Locations"]
        for cat in target_categories:
            print(f"Fetching category: {cat}...")
            pages = crawler.get_category_pages(cat)
            if limit: pages = pages[:limit]
            for title in pages:
                data = crawler.fetch_raw_content(title, category=cat)
                if data: crawler.save_raw(data)
    else:
        cat = category or "Crops"
        print(f"--- Running Stage 1: Category {cat} ---")
        pages = crawler.get_category_pages(cat)
        if limit: pages = pages[:limit]
        for title in pages:
            data = crawler.fetch_raw_content(title, category=cat)
            if data: crawler.save_raw(data)

def run_stage2():
    from stage2_process import WikiProcessor
    print("--- Running Stage 2: Processing ---")
    processor = WikiProcessor()
    processor.process_all()

def run_stage3(limit=None):
    from stage3_index import WikiIndexer
    print("--- Running Stage 3: Indexing ---")
    indexer = WikiIndexer()
    indexer.index_all(limit=limit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wiki Ingestion Pipeline")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="Stage to run")
    parser.add_argument("--category", type=str, help="Category for Stage 1")
    parser.add_argument("--all", action="store_true", help="Fetch ALL common categories in Stage 1")
    parser.add_argument("--limit", type=int, help="Limit number of items")
    args = parser.parse_args()

    if not args.stage or args.stage == 1:
        run_stage1(category=args.category, all_pages=args.all, limit=args.limit)
    if not args.stage or args.stage == 2:
        run_stage2()
    if not args.stage or args.stage == 3:
        run_stage3(limit=args.limit)
