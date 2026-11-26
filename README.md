# Agent From Zero

一套**中英双语、零 GPU 也能运行、每章代码都由 CI 真实执行**的 AI Agent 入门课程。

当前版本包含 **18 章完整课程 + 真实 LLM planner 双语附录**、每章中英文档与自测题、可运行代码、冒烟测试，以及毕业项目 **Local Research Desk**。

A bilingual, zero-GPU AI Agent course with 18 executable chapters, a real-LLM planner appendix, and a runnable capstone project.

## 项目状态

- 18 章中英课程：已完成
- 真实 LLM planner 双语附录：已完成
- 每章代码 + 冒烟测试：已完成
- 每章中英 quiz：各 3 题，共 54 组
- 双语代码块与结构对等校验：已完成
- 依赖锁定、CI 矩阵、每日漂移检查、ruff 与 Windows CI：已完成
- VitePress 双语网站：配置完成，由 GitHub Actions 构建部署
- 毕业项目 Local Research Desk：可本地运行
- 真人试读与阅读时长测量：待完成

## 前置要求

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- 不需要 CUDA、GPU、付费 API key 或模型权重
- 不需要高等数学；第一章只要求会 Python 函数、循环和异常

## 快速开始

```bash
uv sync --frozen
uv run pytest
uv run python tools/check_parity.py
uv run python tools/check_quiz.py
```

运行毕业项目：

```bash
uv run agent-from-zero --demo
uv run agent-from-zero "What is the capital of France?"
uv run agent-from-zero "Calculate (6 + 2) * 7"
uv run agent-from-zero "What is the capital of Atlantis?" --trace-dir traces/atlantis
```

`--demo` 会展示一个基于证据的回答和一个无证据弃权。默认输出 JSON，包含答案、证据、trace、usage、memory、security 和 evaluation。

离线测试：

```bash
uv run pytest -m "not requires_network and not requires_gpu and not requires_api_key and not slow"
```

## 课程目录

| 章节 | 中文 | English |
|---|---|---|
| 1.1 Tokenizer | [中文](docs/zh/1.1-tokenizer.md) | [English](docs/en/1.1-tokenizer.md) |
| 1.2 采样 | [中文](docs/zh/1.2-sampling.md) | [English](docs/en/1.2-sampling.md) |
| 1.3 上下文与注意力 | [中文](docs/zh/1.3-attention.md) | [English](docs/en/1.3-attention.md) |
| 1.4 幻觉与证据 | [中文](docs/zh/1.4-hallucination.md) | [English](docs/en/1.4-hallucination.md) |
| 2.1 结构化输出 | [中文](docs/zh/2.1-structured-output.md) | [English](docs/en/2.1-structured-output.md) |
| 2.2 工具调用 | [中文](docs/zh/2.2-tool-calling.md) | [English](docs/en/2.2-tool-calling.md) |
| 2.3 ReAct 循环 | [中文](docs/zh/2.3-react-loop.md) | [English](docs/en/2.3-react-loop.md) |
| 2.4 记忆与上下文 | [中文](docs/zh/2.4-memory-context.md) | [English](docs/en/2.4-memory-context.md) |
| 2.5 MCP | [中文](docs/zh/2.5-mcp.md) | [English](docs/en/2.5-mcp.md) |
| 2.6 Agent Skills | [中文](docs/zh/2.6-agent-skills.md) | [English](docs/en/2.6-agent-skills.md) |
| 3.1 评测 | [中文](docs/zh/3.1-evaluation.md) | [English](docs/en/3.1-evaluation.md) |
| 3.2 追踪 | [中文](docs/zh/3.2-tracing.md) | [English](docs/en/3.2-tracing.md) |
| 3.3 安全 | [中文](docs/zh/3.3-security.md) | [English](docs/en/3.3-security.md) |
| 3.4 成本与延迟 | [中文](docs/zh/3.4-cost-latency.md) | [English](docs/en/3.4-cost-latency.md) |
| 4.1 多智能体 | [中文](docs/zh/4.1-multi-agent.md) | [English](docs/en/4.1-multi-agent.md) |
| 4.2 浏览器使用 | [中文](docs/zh/4.2-browser-use.md) | [English](docs/en/4.2-browser-use.md) |
| 4.3 实时语音 | [中文](docs/zh/4.3-realtime-voice.md) | [English](docs/en/4.3-realtime-voice.md) |
| 4.4 毕业项目 | [中文](docs/zh/4.4-capstone.md) | [English](docs/en/4.4-capstone.md) |
| 附录：真实 LLM planner | [中文](docs/zh/appendix-real-llm-planner.md) | [English](docs/en/appendix-real-llm-planner.md) |

## 双语网站

线上地址：**[https://0summy0.github.io/agent-from-zero/](https://0summy0.github.io/agent-from-zero/)**

网站源码位于 `docs/`，使用 VitePress。GitHub Actions 会在推送到 `main` 时构建并部署到 GitHub Pages。

本地预览（需要 Node.js 22+ 和 npm）：

```bash
npm install
npm run docs:dev
npm run docs:build
```

构建产物位于 `docs/.vitepress/dist/`，不会提交到仓库。

## 质量保证

这个项目不只检查 Markdown 是否存在，还检查：

- 每个章节代码能否导入并执行最小路径；
- 中英章节 id 集合是否一致；
- 中英代码块指纹是否逐字一致；
- front-matter 九个字段是否齐全，`ram_basis` 是否明确区分实测与估算；
- 中英 quiz 数量、答案下标和选项长度比例是否一致；
- 所有直接依赖是否有上界；
- CI 是否在 Linux 与 Windows 上通过锁定依赖和最新允许依赖两档测试；
- 每日调度是否能在上游依赖漂移时发现问题，并避免重复开 issue；
- Node 侧是否使用 `package-lock.json` + `npm ci`；
- Python 代码是否通过 ruff lint 与 format 检查；
- 关键章节输出是否符合 golden JSON Schema；
- 有 notebook 时是否由 nbval 真正执行。

相关脚本：

- `tools/check_bounds.py`
- `tools/check_parity.py`
- `tools/check_quiz.py`
- `tests/meta/test_repo_contract.py`
- `tests/smoke/test_chapter_*.py`
- `tests/test_golden_contracts.py`
- `uv run ruff check .`

## 项目结构

```text
agent-from-zero/
├── chapters/                 # 每章可运行教学代码
├── docs/                     # VitePress 网站与中英章节
├── quizzes/                  # 中英自测题
├── src/agent_from_zero/      # 毕业项目 Local Research Desk
├── tests/
│   ├── meta/                 # 仓库契约测试
│   ├── smoke/                # 每章冒烟测试
│   └── golden/               # 输出结构契约
├── tools/                    # 依赖、双语、quiz 校验脚本
├── .github/workflows/        # CI、每日漂移、notebook、网站部署
├── pyproject.toml
├── uv.lock
├── package.json
└── package-lock.json
```

## 教学边界

- 所有 Agent 示例都是确定性、本地、无副作用的，用来解释机制，不冒充真实大模型。
- 第 2.5 章实现的是 MCP 教学子集，不是完整 MCP SDK。
- 第 4.2 章使用本地 HTML 模拟浏览器，不访问真实网站。
- 第 4.3 章模拟实时语音事件流，不生成真实音频。
- 成本与延迟数字是教学模拟，不是供应商账单。
- 毕业项目不是生产系统；真实应用仍需人工审校、权限隔离、监控和更完整评测。

## 下一步

1. 找 3 位零基础读者试读，记录卡点与真实阅读时长。
2. 根据试读结果修订第一章，再决定是否增加扩展章节。
3. 可选增强：tokenizer 坏缓存自愈、真实 LLM planner 附录。

## 作者

summy

## 许可证

本项目使用 [MIT License](LICENSE)。
