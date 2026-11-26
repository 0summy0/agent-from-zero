---
layout: home
hero:
  name: Agent From Zero
  text: 双语零基础 AI Agent 课程
  tagline: 18 章 + 进阶附录 · 中英同步 · CPU 可跑 · 每章代码由 CI 真实执行
  actions:
    - theme: brand
      text: 开始中文课程
      link: /zh/1.1-tokenizer
    - theme: alt
      text: Start in English
      link: /en/1.1-tokenizer
features:
  - title: 真正可运行
    details: 每章都有冒烟测试、依赖锁和 CI。不是只贴一段看起来能跑的代码，而是每天真实执行。
  - title: 零基础友好
    details: 明确前置知识，默认无 GPU、无付费 API；从 tokenizer 一路走到可运行的 Agent 毕业项目。
  - title: 双语同步
    details: 中英章节结构、代码块和测验由脚本校验，翻译不会悄悄落后。
  - title: 完整学习路径
    details: 语言模型基础 → Agent 核心 → 可靠性 → 多智能体、浏览器、实时语音与毕业项目。
---

## 立即运行 / Run now

```bash
uv sync --frozen
uv run agent-from-zero --demo
```

毕业项目 **Local Research Desk** 完全在本地运行：它组合结构化计划、工具调用、ReAct、证据检索、安全扫描、上下文摘要、追踪和评测。

- 中文毕业项目：[4.4 本地研究台](/zh/4.4-capstone)
- English capstone: [4.4 Local Research Desk](/en/4.4-capstone)
- 进阶附录：[把确定性 planner 换成真实 LLM](/zh/appendix-real-llm-planner)
- Advanced appendix: [Replace the planner with a real LLM](/en/appendix-real-llm-planner)
