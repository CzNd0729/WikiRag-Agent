import os
import json
from typing import Annotated, List, Union, Dict, Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage

from core.llm_provider import get_chat_model
from core.rag_engine import RAGEngine
from mcp_servers.stardew_mcp import get_player_status, get_inventory
from agents.prompts import (
    COORDINATOR_PROMPT, 
    REFLECTOR_PROMPT, 
    SUMMARIZER_PROMPT,
    FINAL_GENERATOR_PROMPT
)
from agents.schemas import AgentAction, ReflectorAnalysis, FinalResponse, AgentState

# 初始化 RAG
rag = RAGEngine()

# 1. 业务工具层

@tool
async def search_wiki(query: str):
    """检索知识库。返回分块内容及其对应的原始文件路径(source)。"""
    docs = await rag.search(query, k=5)
    results = []
    for doc in docs:
        title = doc.metadata.get('title', 'Knowledge')
        source = doc.metadata.get('source', 'Unknown')
        results.append(f"[{title}] (Source: {source})\n{doc.page_content}")
    return "\n\n".join(results)

@tool
async def read_full_wiki(source_path: str):
    """读取完整的原始 Wiki Markdown 文本。source_path 应从 search_wiki 的结果中获取。"""
    try:
        # 安全检查：确保只能读取 data/processed 或 data/raw 目录下的文件
        normalized_path = os.path.normpath(source_path)
        if not (normalized_path.startswith("data" + os.sep + "processed") or 
                normalized_path.startswith("data" + os.sep + "raw")):
             return f"Error: Unauthorized path access: {source_path}"
             
        if not os.path.exists(normalized_path):
            return f"Error: File not found: {source_path}"
            
        with open(normalized_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {e}"

@tool
async def get_context_status():
    """读取实时环境基础数据。"""
    # get_player_status 是同步的，可以直接调用或包装
    return get_player_status()

@tool
async def get_context_details():
    """读取环境详细清单。"""
    return get_inventory()

# 2. 模型工厂

llm = get_chat_model("AGENT_LLM")
# 绑定原生工具
tools = [search_wiki, read_full_wiki, get_context_status, get_context_details]
llm_with_tools = llm.bind_tools(tools)

# 3. Graph 节点逻辑

async def tools_node(state: AgentState):
    """自定义工具调用节点。执行工具并直接将结果写入 context，而不是 messages。"""
    last_message = state["messages"][-1]
    
    # 获取 llm 建议的工具调用
    tool_calls = getattr(last_message, "tool_calls", [])
    if not tool_calls:
        return {"next_node": "final_generator"}
    
    new_contexts = []
    # 建立工具映射
    tool_map = {tool.name: tool for tool in tools}
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in tool_map:
            result = await tool_map[tool_name].ainvoke(tool_args)
            # 将结果加入 context 而不是发送 ToolMessage 到 messages
            new_contexts.append(f"Tool [{tool_name}] output:\n{result}")
        else:
            new_contexts.append(f"Error: Tool {tool_name} not found.")
            
    return {
        "context": new_contexts,
        "next_node": "reflector"
    }

async def coordinator(state: AgentState):
    """任务分发与协调。"""
    messages = state["messages"]
    summary = state.get("summary", "")
    
    prompt = COORDINATOR_PROMPT
    if summary:
        prompt += f"\n\nContext Summary: {summary}"
        
    # 构建请求消息列表
    req_messages = [SystemMessage(content=prompt)]
    # 如果有 context，注入作为短期记忆参考
    if state.get("context"):
        context_str = "\n".join(state["context"])
        req_messages.append(SystemMessage(content=f"已收集的信息:\n{context_str}"))
    
    req_messages.extend(messages)
        
    response = await llm_with_tools.ainvoke(req_messages)
    
    if response.tool_calls:
        # 模型决定调用工具
        return {
            "next_node": "tools",
            "messages": [response],
            "context": [f"Action: 调用工具 {tc['name']} 参数 {tc['args']}" for tc in response.tool_calls]
        }
    
    # 无需工具，直接生成最终回答
    return {"next_node": "final_generator", "messages": [response]}

async def reflector(state: AgentState):
    """结果反思与质检。"""
    context_str = "\n".join(state["context"])
    
    response = await llm.ainvoke([
        SystemMessage(content=REFLECTOR_PROMPT),
        HumanMessage(content=f"Collected: {context_str}\n\nTask: {state['messages'][0].content}")
    ])
    
    try:
        data = json.loads(response.content)
        analysis = ReflectorAnalysis(**data)
        
        if analysis.next_step == "continue" and state["reflection_count"] < 3:
            return {
                "next_node": "coordinator", 
                "reflection_count": state["reflection_count"] + 1,
                "context": [f"Reflect: {analysis.critique}"]
            }
        return {"next_node": "final_generator"}
    except:
        return {"next_node": "final_generator"}

async def final_generator(state: AgentState):
    """最终回答生成。"""
    context_str = "\n".join(state["context"])
    llm_with_final = llm.with_structured_output(FinalResponse)
    
    prompt = [
        SystemMessage(content=FINAL_GENERATOR_PROMPT),
        HumanMessage(content=f"已收集的背景知识与环境状态:\n{context_str}\n\n当前用户问题:\n{state['messages'][-1].content}")
    ]
    
    try:
        response = await llm_with_final.ainvoke(prompt)
        answer_text = f"{response.answer}\n\n📚 参考来源: {', '.join(response.sources) if response.sources else '内置知识库'}\n💡 建议操作: {' | '.join(response.actionable_tips) if response.actionable_tips else '无'}"
        return {"messages": [AIMessage(content=answer_text)]}
    except Exception as e:
        fallback_prompt = "请基于以下上下文回答用户问题。请以 JSON 格式输出，包含 'answer' 字段。\n\n上下文：" + context_str
        resp = await llm.ainvoke([
            SystemMessage(content=fallback_prompt),
            *state["messages"]
        ])
        return {"messages": [resp]}

async def summarizer(state: AgentState):
    """会话管理：自动裁剪过长历史并生成摘要。"""
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len, # 粗略计数
        max_tokens=4000,
        start_on="human",
        include_system=True
    )
    
    if len(state["messages"]) < 10:
        return {"messages": []}

    response = await llm.ainvoke([
        SystemMessage(content=SUMMARIZER_PROMPT),
        HumanMessage(content=str(trimmed_messages))
    ])
    
    return {
        "summary": response.content
    }

# 4. 架构编排

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("coordinator", coordinator)
    workflow.add_node("tools", tools_node) # 使用自定义 tools_node
    workflow.add_node("reflector", reflector)
    workflow.add_node("final_generator", final_generator)
    workflow.add_node("summarizer", summarizer)
    
    workflow.set_entry_point("coordinator")
    
    workflow.add_conditional_edges("coordinator", lambda x: x["next_node"], {
        "tools": "tools",
        "final_generator": "final_generator",
        "coordinator": "coordinator"
    })
    
    workflow.add_edge("tools", "reflector")
    
    workflow.add_conditional_edges("reflector", lambda x: x["next_node"], {
        "coordinator": "coordinator",
        "final_generator": "final_generator"
    })
    
    workflow.add_edge("final_generator", "summarizer")
    workflow.add_edge("summarizer", END)
    
    return workflow.compile(checkpointer=MemorySaver())

graph = build_graph()
