from langgraph.graph import StateGraph, END
from agents.schemas import AgentState
from core.nodes import (
    coordinator, 
    tools_node, 
    reflector, 
    final_generator, 
    summarizer
)

def build_graph():
    """构建 LangGraph 状态机编排逻辑。"""
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("coordinator", coordinator)
    workflow.add_node("tools", tools_node)
    workflow.add_node("reflector", reflector)
    workflow.add_node("final_generator", final_generator)
    workflow.add_node("summarizer", summarizer)
    
    # 设置入口
    workflow.set_entry_point("coordinator")
    
    # 添加条件边与普通边
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
    
    # 编译图
    return workflow.compile()

# 导出编译后的图实例
graph = build_graph()
