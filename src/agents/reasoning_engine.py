import sys
from core.agent_graph import graph
from langchain_core.messages import HumanMessage

async def main():
    # 检查命令行参数是否有问题，如果没有则提示输入
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("请输入您的问题: ")
    
    if not question.strip():
        print("问题不能为空。")
        return

    config = {"configurable": {"thread_id": "test_user_123"}}
    
    print(f"\nUser: {question}\n")
    
    inputs = {
        "messages": [HumanMessage(content=question)],
        "reflection_count": 0,
        "context": []
    }
    
    async for output in graph.astream(inputs, config=config):
        for node, data in output.items():
            print(f"--- Node: {node} ---")
            if "messages" in data and len(data["messages"]) > 0:
                # 打印消息内容，排除系统消息和工具调用消息的原始 JSON（如果需要更干净的输出）
                msg = data["messages"][-1]
                print(msg.content)
            elif "context" in data:
                # 打印 context 增量
                for ctx in data["context"]:
                    print(f"[Context] {ctx}")
            print("-" * 20)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已退出。")
