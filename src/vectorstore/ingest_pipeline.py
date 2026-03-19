import os
import argparse
import sys

def run_stage1(category=None, all_pages=False, limit=None, url=None, depth=3):
    if url:
        from vectorstore.stage1_raw import UniversalWebCrawler
        print(f"--- Running Stage 1: Universal Crawler for {url} ---")
        crawler = UniversalWebCrawler()
        crawler.crawl(url, max_depth=depth, limit=limit or 100)
        return

    from vectorstore.stage1_raw import WikiRawCrawler
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
    from vectorstore.stage2_process import WikiProcessor
    print("--- Running Stage 2: Processing ---")
    processor = WikiProcessor()
    processor.process_all()

def run_stage3(limit=None):
    from vectorstore.stage3_chunk import WikiChunker
    print("--- Running Stage 3: Chunking ---")
    chunker = WikiChunker()
    chunker.chunk_all(limit=limit)

def run_stage4(limit=None):
    import asyncio
    from vectorstore.stage4_index import WikiIndexer
    print("--- Running Stage 4: Indexing ---")
    indexer = WikiIndexer()
    asyncio.run(indexer.index_all(limit=limit))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wiki Ingestion Pipeline")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4], help="Stage to run")
    parser.add_argument("--category", type=str, help="Category for Stage 1")
    parser.add_argument("--all", action="store_true", help="Fetch ALL common categories in Stage 1")
    parser.add_argument("--limit", type=int, help="Limit number of items")
    parser.add_argument("--url", type=str, help="Start URL for Universal Crawler")
    parser.add_argument("--depth", type=int, default=3, help="Recursion depth for Universal Crawler")
    args = parser.parse_args()

    if not args.stage or args.stage == 1:
        run_stage1(category=args.category, all_pages=args.all, limit=args.limit, url=args.url, depth=args.depth)
    if not args.stage or args.stage == 2:
        run_stage2()
    if not args.stage or args.stage == 3:
        run_stage3(limit=args.limit)
    if not args.stage or args.stage == 4:
        run_stage4(limit=args.limit)
