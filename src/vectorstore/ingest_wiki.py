from .ingest_pipeline import run_stage1, run_stage2, run_stage3

if __name__ == "__main__":
    # 为了保持兼容性，旧的 ingest_wiki.py 转发到新流程
    import argparse
    parser = argparse.ArgumentParser(description="Stardew Wiki Ingestion (Legacy Entry)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3])
    parser.add_argument("--category", type=str)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if not args.stage or args.stage == 1:
        run_stage1(category=args.category, all_pages=args.all, limit=args.limit)
    if not args.stage or args.stage == 2:
        run_stage2()
    if not args.stage or args.stage == 3:
        run_stage3(limit=args.limit)
