---
id: appendix-real-llm-planner
title_zh: "附录：把确定性 planner 换成真实 LLM"
title_en: "Appendix: Replacing the Deterministic Planner with a Real LLM"
prereq: "完成 2.1、2.3 和 4.4；理解 Python 函数、JSON 和依赖注入"
est_minutes: unmeasured
ram_min_mb: 64
ram_basis: estimate
needs_api_key: false
source_revision: 1
---
<!-- AUTHOR: summy -->

# 附录：把确定性 planner 换成真实 LLM

## 1. 为什么已经有完整 Agent 循环

毕业项目的外层流程已经具备真实 Agent 需要的大部分工程能力：结构化计划校验、工具白名单、步数限制、trace、证据引用、安全扫描和评测。

目前唯一固定的是 `deterministic_planner()`：它用规则决定下一步。真实 LLM 不需要替换整个 Agent，只需要替换这个决策函数。

## 2. planner 的接口契约

当前 planner 接收问题和已有 trace，返回：

```python
{
    "thought": "Why this action was chosen",
    "plan": {
        "action": "calculator",
        "arguments": {"expression": "2 + 2"},
        "confidence": 0.99,
    },
}
```

`plan` 必须继续通过 `validate_plan()`，工具必须继续通过 `execute_action()`。模型不能绕过白名单直接执行命令。

## 3. 用依赖注入接入模型

下面的 `LLMPlanner` 不绑定任何供应商。它只要求你注入一个 `complete(payload)` 函数；示例使用本地假 provider，因此不需要 API key。

```python
import json

from agent_from_zero import capstone


class LLMPlanner:
    def __init__(self, complete, tool_schemas):
        self.complete = complete
        self.tool_schemas = tool_schemas

    def __call__(self, question, trace):
        payload = {
            "question": question,
            "trace": trace,
            "tools": self.tool_schemas,
            "instruction": "Return one JSON plan. Do not execute tools.",
        }
        raw = self.complete(payload)
        plan = json.loads(raw)
        return {"thought": "The model proposed the next validated plan.", "plan": plan}


def fake_complete(payload):
    return json.dumps(
        {
            "action": "calculator",
            "arguments": {"expression": "6 + 2"},
            "confidence": 0.9,
        }
    )


planner = LLMPlanner(fake_complete, capstone._ARGUMENT_SCHEMAS)
decision = planner("Calculate 6 + 2", [])
valid, errors = capstone.validate_plan(decision["plan"])
print(valid, errors)
print(capstone.execute_action(decision["plan"]))
```

这段代码的重点不是假 provider，而是接口：真实 provider 也只需要实现同样的 `complete(payload)`。

## 4. 真实 API provider 应该做什么

一个真实 `complete(payload)` 通常需要：

- 把系统指令、工具 schema、用户问题和压缩后的 trace 发给模型；
- 要求模型只返回 JSON，不直接执行工具；
- 处理超时、限流、非 JSON 输出和 schema 校验失败；
- 从环境变量读取 API key，不写进代码或日志；
- 记录模型名、延迟、Token 用量和原始计划，便于复盘。

即使模型返回了计划，也仍然要经过 `validate_plan()` 和 `execute_action()`。**模型负责提议，程序负责授权和执行。**

## 5. 为什么外层循环不用改

现有循环仍然可以做这些事：

- 最多执行 `MAX_STEPS` 步；
- 每一步记录 thought、action 和 observation；
- 只调用注册表中的本地工具；
- 无证据时弃权；
- 最后输出 usage、memory、security 和 evaluation。

你替换的只是“下一步做什么”的判断来源。工具执行、证据链、审计和停止条件都不变。

## 6. 练习与边界

尝试实现两个 provider：

1. `FakeProvider`：根据问题返回固定计划，用于离线测试。
2. `HTTPProvider`：调用你选择的 OpenAI-compatible 接口，读取环境变量中的 key。

然后写测试确认：无效 JSON、未知工具、越界参数和超过步数都会安全失败。

这个附录不把真实 API 调用加入默认测试，因为默认课程必须保持离线、零 GPU、无付费 key。真实模型会带来成本、延迟、隐私和不确定性，应该作为明确的进阶选项。
