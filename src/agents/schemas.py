from typing import List, Optional, Literal, Annotated, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
import operator

class AgentAction(BaseModel):
    """Agent 建议执行的下一个动作。"""
    tool_name: Literal["search_wiki", "read_full_wiki", "get_context_status", "get_context_details", "none"] = Field(
        description="建议使用的工具名称。如果不需要工具，则为 none。"
    )
    query: Optional[str] = Field(description="工具的输入参数，例如搜索关键词或文件路径。")
    reason: str = Field(description="选择该动作的原因。")

class ReflectorAnalysis(BaseModel):
    """反思节点生成的分析。"""
    is_sufficient: bool = Field(description="当前收集的信息是否足以回答用户问题。")
    critique: str = Field(description="如果不足，说明缺失的信息；如果充足，说明改进建议。")
    next_step: Literal["continue", "finish"] = Field(description="下一步是继续检索还是结束生成。")

class FinalResponse(BaseModel):
    """Agent 给出的最终结构化回答。"""
    answer: str = Field(description="对用户问题的详细、专业的回答。")
    sources: List[str] = Field(default=[], description="回答参考的 Wiki 页面标题或数据源。")
    actionable_tips: List[str] = Field(default=[], description="给用户的具体操作性建议。")

class AgentState(TypedDict):
    """LangGraph 状态定义。"""
    # 消息列表，支持累加
    messages: Annotated[List[BaseMessage], operator.add]
    # 当前对话摘要（长会话管理）
    summary: str
    # 专家收集到的原始背景知识或实时环境片段
    context: Annotated[List[str], operator.add]
    # 下一个目标节点
    next_node: str
    # 反思次数，防止死循环
    reflection_count: int
