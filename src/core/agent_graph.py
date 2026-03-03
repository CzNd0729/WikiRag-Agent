import os
import json
from typing import Annotated, List, Union, Dict, Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from core.llm_provider import get_chat_model
from core.rag_engine import RAGEngine
from mcp_servers.stardew_mcp import get_player_status, get_inventory
from agents.prompts import (
    COORDINATOR_PROMPT, 
    REFLECTOR_PROMPT, 
    SUMMARIZER_PROMPT
)
from agents.schemas import AgentAction, ReflectorAnalysis, FinalResponse, AgentState

# 初始化 RAG
rag = RAGEngine()

# 1. 业务工具层

@tool
async def search_wiki(query: str):
    """检索知识库。"""
    docs = await rag.search(query, k=5)
    return "\n\n".join([f"[{doc.metadata.get('title', 'Knowledge')}] {doc.page_content}" for doc in docs])

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

# 3. Graph 节点逻辑

async def coordinator(state: AgentState):
    """任务分发与协调。"""
    messages = state["messages"]
    summary = state.get("summary", "")
    
    prompt = COORDINATOR_PROMPT
    if summary:
        prompt += f"\n\nContext Summary: {summary}"
        
    # 为了让 ToolNode 正常工作，我们需要生成一个包含 tool_calls 的 AIMessage
    # 同时为了满足 JSON 强约束，我们依然保留之前的逻辑分析意图
    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        *messages
    ])
    
    try:
        data = json.loads(response.content)
        action = AgentAction(**data)
        
        if action.tool_name == "none":
            return {"next_node": "final_generator", "messages": [response]}
        
        # 核心修复：手动构造包含 tool_calls 的 AIMessage
        tool_call_id = f"call_{action.tool_name}"
        ai_msg = AIMessage(
            content=response.content,
            tool_calls=[{
                "id": tool_call_id,
                "name": action.tool_name,
                "args": {"query": action.query} if action.query else {}
            }]
        )
        
        return {
            "next_node": "tools",
            "messages": [ai_msg],
            "context": [f"Action: {action.tool_name} for {action.query} (Reason: {action.reason})"]
        }
    except Exception as e:
        return {"next_node": "coordinator", "context": [f"Error: Prompt format invalid or tool call failed. {e}"]}

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
    
    # 由于全局启用了 JSON 模式，这里必须要求 JSON 输出
    # 我们使用 with_structured_output 来自动处理 Prompt 注入
    llm_with_final = llm.with_structured_output(FinalResponse)
    
    prompt = [
        SystemMessage(content="你是一个专业的百科问答整合者。请基于提供的上下文信息，为用户生成一个准确、详尽且易于理解的最终回答。请务必以 JSON 格式输出。"),
        HumanMessage(content=f"已收集的背景知识与环境状态:\n{context_str}\n\n当前用户问题:\n{state['messages'][-1].content}")
    ]
    
    try:
        response = await llm_with_final.ainvoke(prompt)
        # 将结构化结果转为友好的文本展示
        answer_text = f"{response.answer}\n\n📚 参考来源: {', '.join(response.sources) if response.sources else '内置知识库'}\n💡 建议操作: {' | '.join(response.actionable_tips) if response.actionable_tips else '无'}"
        return {"messages": [AIMessage(content=answer_text)]}
    except Exception as e:
        # 兜底逻辑：如果结构化解析失败，尝试带 JSON 关键词的普通调用
        fallback_prompt = "请基于以下上下文回答用户问题。请以 JSON 格式输出，包含 'answer' 字段。\n\n上下文：" + context_str
        resp = await llm.ainvoke([
            SystemMessage(content=fallback_prompt),
            *state["messages"]
        ])
        return {"messages": [resp]}

async def summarizer(state: AgentState):
    """会话压缩。"""
    if len(state["messages"]) < 10:
        # 即使不压缩，也返回状态中的空消息增量，避免返回空字典导致某些下游处理器异常
        return {"messages": []}
        
    response = await llm.ainvoke([
        SystemMessage(content=SUMMARIZER_PROMPT),
        HumanMessage(content=str(state["messages"]))
    ])
    
    return {
        "summary": response.content,
        "messages": state["messages"][-2:] # 仅保留最后两轮
    }

# 4. 架构编排

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("coordinator", coordinator)
    workflow.add_node("reflector", reflector)
    workflow.add_node("final_generator", final_generator)
    workflow.add_node("summarizer", summarizer)
    
    tools = [search_wiki, get_context_status, get_context_details]
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("coordinator")
    
    workflow.add_conditional_edges("coordinator", lambda x: x["next_node"], {
        "tools": "tools",
        "final_generator": "final_generator"
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
