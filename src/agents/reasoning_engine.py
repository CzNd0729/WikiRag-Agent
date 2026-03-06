from core.agent_graph import graph
from langchain_core.messages import HumanMessage

async def main():
    config = {"configurable": {"thread_id": "test_user_123"}}
    
    # 模拟复杂问题
    question = "哪些角色会去星之果实酒吧"
    
    print(f"User: {question}\n")
    
    inputs = {
        "messages": [HumanMessage(content=question)],
        "reflection_count": 0,
        "context": []
    }
    
    async for output in graph.astream(inputs, config=config):
        for node, data in output.items():
            print(f"--- Node: {node} ---")
            if "messages" in data:
                print(data["messages"][-1].content)
            elif "context" in data:
                print(data["context"][-1])
            print("-" * 20)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
