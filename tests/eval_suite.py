import os
import asyncio
import json
from typing import Dict, List, Any
from langsmith import Client, aevaluate
from langchain_core.messages import HumanMessage
from core.agent_graph import graph
from core.llm_provider import get_chat_model
from langsmith.evaluation import EvaluationResult

# 配置
DATASET_NAME = "Sentinel-Wiki-Eval-Set"

# 评测用例集
EVAL_CASES = [
    {
        "question": "星露谷物语中如何获得五彩碎片？",
        "reference": "五彩碎片可以通过采矿（尤其是骷髅洞穴中的铱矿石节点、神秘石）、击杀怪物、钓鱼宝箱、万象晶球以及全景石等方式获得。"
    },
    {
        "question": "我的角色现在有多少钱？物品栏里有什么？",
        "reference": "用户正在询问当前存档状态。回答应包含玩家当前的金额（Gold）和物品栏（Inventory）中的具体内容。"
    },
    {
        "question": "春季种什么作物最赚钱？",
        "reference": "春季最赚钱的作物通常是草莓（Strawberry），其次是大黄（Rhubarb）和花椰菜（Cauliflower）。"
    },
    {
        "question": "如何到达沙漠？",
        "reference": "需要完成社区中心的金库献祭（或通过 Joja 超市购买相应项目）来修复巴士。修复后可以支付 500 金币乘巴士前往。"
    },
    {
        "question": "给阿比盖尔送什么礼物最好？",
        "reference": "阿比盖尔最喜欢的礼物包括紫水晶、南瓜、河豚、巧克力蛋糕、辛辣鳗鱼、黑莓馅饼和巧克力蛋糕。"
    }
]

async def target_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """评测目标：Agent 逻辑 (异步)"""
    config = {"configurable": {"thread_id": "eval_thread_" + os.urandom(4).hex()}}
    initial_state = {
        "messages": [HumanMessage(content=inputs["question"])],
        "reflection_count": 0,
        "context": []
    }
    
    final_response = ""
    used_tools = []
    
    async for output in graph.astream(initial_state, config=config):
        for node, data in output.items():
            if "messages" in data and len(data["messages"]) > 0:
                msg = data["messages"][-1]
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        used_tools.append(tc['name'])
                
                if node == "final_generator":
                    final_response = msg.content
                    
    return {
        "output": final_response,
        "used_tools": used_tools
    }

def prepare_dataset(client: Client):
    """创建或更新 LangSmith 数据集"""
    if not client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.create_dataset(DATASET_NAME, description="Sentinel-Wiki 评测基准集")
        for case in EVAL_CASES:
            client.create_example(
                inputs={"question": case["question"]},
                outputs={"reference": case["reference"]},
                dataset_id=dataset.id
            )
        print(f"数据集 {DATASET_NAME} 创建完成。")
    else:
        print(f"数据集 {DATASET_NAME} 已存在。")

async def llm_judge(run: Any, example: Any) -> EvaluationResult:
    """异步 LLM Judge"""
    judge_llm = get_chat_model("JUDGE_LLM")
    
    prediction = run.outputs.get("output", "")
    reference = example.outputs.get("reference", "")
    question = example.inputs.get("question", "")
    
    prompt = f"""你是一名专业的 AI 评测员。请对比以下【AI 回答】与【参考答案】，判断其准确性。

[用户问题]
{question}

[参考答案]
{reference}

[AI 回答]
{prediction}

请根据以下标准给出评分（0 或 1）：
1. 如果 AI 回答包含了参考答案中的核心事实，且没有明显的错误或幻觉，请给出 1 分。
2. 如果 AI 回答与参考答案冲突，或者遗漏了绝大部分核心事实，请给出 0 分。

请输出 JSON 格式，包含 score (0/1) 和 reasoning (简要理由)。
示例：{{"score": 1, "reasoning": "回答准确覆盖了五彩碎片的获取方式。" }}
"""
    
    try:
        response = await judge_llm.ainvoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        res_data = json.loads(content)
        return EvaluationResult(
            key="correctness",
            score=float(res_data.get("score", 0)),
            comment=res_data.get("reasoning", "No reasoning provided")
        )
    except Exception as e:
        return EvaluationResult(
            key="correctness",
            score=0.0,
            comment=f"Judge Error: {str(e)}"
        )

async def run_suite():
    print("=== Starting LangSmith Powered Evaluation (Async) ===")
    client = Client()
    prepare_dataset(client)
    
    # 切换到 aevaluate 处理异步目标函数
    results = await aevaluate(
        target_agent,
        data=DATASET_NAME,
        evaluators=[llm_judge],
        experiment_prefix="sentinel-wiki-async-judge",
    )
    
    print(f"\n评测完成！请访问以下链接查看详细报告：")
    print(results)

if __name__ == "__main__":
    asyncio.run(run_suite())
