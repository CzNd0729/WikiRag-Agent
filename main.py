import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv

# 确保 src 目录在路径中
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

def setup_env():
    """环境预检查"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("警告: 未发现 .env 文件。正在从 .env.example 创建...")
            with open(".env.example", "r", encoding="utf-8") as f_in:
                with open(".env", "w", encoding="utf-8") as f_out:
                    f_out.write(f_in.read())
            print("请编辑 .env 文件并填入您的 API Key。")
        else:
            print("错误: 找不到 .env.example 文件。")
            sys.exit(1)
    
    load_dotenv()
    
    # 检查核心变量
    required_vars = [
        "AGENT_LLM_API_KEY", 
        "EMBEDDING_API_KEY", 
        "VECTOR_DB_DIR",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"错误: 缺少以下环境变量: {', '.join(missing)}")
        print("请在 .env 文件中配置它们。")
        sys.exit(1)

async def run_chat(args):
    """启动交互式对话 (仿 reasoning_engine 逻辑)"""
    from core.graph import graph
    from langchain_core.messages import HumanMessage
    from langfuse.callback import CallbackHandler
    
    # 注入 Langfuse Callback
    langfuse_handler = CallbackHandler()
    
    # 获取问题：从参数或手动输入
    if args.question:
        question = " ".join(args.question)
    else:
        question = input("请输入您的问题: ")
    
    if not question.strip():
        print("问题不能为空。")
        return

    config = {
        "configurable": {"thread_id": "main_chat_user_" + os.urandom(4).hex()},
        "callbacks": [langfuse_handler]
    }
    print(f"\nUser: {question}\n")
    
    inputs = {
        "messages": [HumanMessage(content=question)],
        "reflection_count": 0,
        "context": []
    }
    
    # 使用 stream_mode="messages" 获取流式消息输出，针对 final_generator 节点
    async for msg, metadata in graph.astream(inputs, config=config, stream_mode="messages"):
        if metadata.get("langgraph_node") == "final_generator":
            # 只有在 final_generator 节点才打印内容
            print(msg.content, end="", flush=True)
    print("\n")
    print("-" * 20)
    
    # 确保 Langfuse 数据上传完成
    langfuse_handler.flush()

async def run_eval():
    """启动评测套件"""
    from tests.eval_suite import run_suite
    await run_suite()

def main():
    parser = argparse.ArgumentParser(description="WikiRag-Agent Agent 统一入口")
    parser.add_argument("mode", choices=["chat", "eval"], default="chat", nargs="?",
                        help="运行模式: chat (交互对话, 默认), eval (自动化评测)")
    parser.add_argument("question", nargs="*", help="针对 chat 模式的直接提问内容")
    
    args = parser.parse_args()
    
    setup_env()
    
    if args.mode == "chat":
        try:
            asyncio.run(run_chat(args))
        except KeyboardInterrupt:
            print("\n已退出。")
    elif args.mode == "eval":
        asyncio.run(run_eval())

if __name__ == "__main__":
    main()
