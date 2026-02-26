import os
from typing import Annotated, List, Union, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from vectorstore.query_rag import WikiVectorStore
from mcp_servers.stardew_mcp import get_player_status, get_inventory, get_social_info, get_farm_map
from agents.prompts import COORDINATOR_PROMPT, WIKI_AGENT_PROMPT, SAVE_AGENT_PROMPT

# 1. 定义工具

@tool
async def search_wiki(query: str):
    """搜索星露谷物语 Wiki 知识。"""
    vdb = WikiVectorStore()
    retriever = vdb.get_hybrid_retriever(k=3)
    # LangChain retrievers support ainvoke for async
    docs = await retriever.ainvoke(query)
    return "\n\n".join([doc.page_content for doc in docs])

@tool
async def get_save_status():
    """读取玩家当前存档状态（金钱、日期、天气等）。"""
    # 模拟异步，因为目前 parser 是同步的，后续可优化
    return get_player_status()

@tool
async def get_save_inventory():
    """读取玩家当前背包和储物箱物品。"""
    return get_inventory()

# 2. 定义状态结构
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]

# 3. 初始化 LLM (使用 DeepSeek)
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
)

# 4. 定义节点工厂
def create_agent(llm, tools, system_prompt: str):
    """通用代理节点创建函数。"""
    llm_with_tools = llm.bind_tools(tools)
    
    async def agent_node(state: AgentState):
        messages = [AIMessage(content=system_prompt)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}
    
    return agent_node

# 初始化各个代理节点
coordinator_node = create_agent(llm, [search_wiki, get_save_status, get_save_inventory], COORDINATOR_PROMPT)
wiki_node = create_agent(llm, [search_wiki], WIKI_AGENT_PROMPT)
save_node = create_agent(llm, [get_save_status, get_save_inventory], SAVE_AGENT_PROMPT)

# 5. 构建图
def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("wiki_expert", wiki_node)
    workflow.add_node("save_expert", save_node)
    
    # 工具节点
    tools = [search_wiki, get_save_status, get_save_inventory]
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("coordinator")
    
    # 路由逻辑
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "continue"
        return "end"

    workflow.add_conditional_edges(
        "coordinator",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "coordinator")
    
    return workflow.compile()

# 导出 graph 变量供 LangGraph Studio/Dev 使用
graph = create_graph()

async def main():
    # 示例运行
    input_state = {"messages": [HumanMessage(content="我现在有多少钱？")]}
    async for output in graph.astream(input_state):
        for key, value in output.items():
            print(f"Node '{key}':")
            # 打印消息内容以供验证
            if "messages" in value:
                last_msg = value["messages"][-1]
                print(last_msg.content)
        print("-" * 20)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"运行失败: {e}")
