# Changelog

## [1.0.0] - 2026-11-26

### Added

- MIT 许可证。
- 18 章中英双语课程，覆盖语言模型基础、Agent 核心、可靠性、编排与毕业项目。
- 每章可运行代码、冒烟测试和三组中英自测题。
- Local Research Desk 毕业项目与 `agent-from-zero` CLI。
- 结构化输出、工具调用、ReAct、记忆、MCP、Agent Skills 的最小实现。
- 评测、JSONL trace、安全扫描、成本与延迟模拟。
- 多智能体、本地浏览器工具和实时语音事件流。
- VitePress 双语网站配置、GitHub Pages 工作流与线上部署。
- 依赖锁定、双语对等、quiz 契约、每日漂移和 notebook 执行 CI。

### Fixed

- 离线测试命令保留完整四闸门，不会意外启用 GPU 测试。
- 所有 push/PR workflow 覆盖 `tools/**` 与 `.python-version`。
- `uv.lock` 纳入仓库，CI 使用 `uv sync --frozen`。
- PyPI 源统一为官方索引。

### Pending

- 真人试读与阅读时长测量。
- 可选的 tokenizer 坏缓存自愈与每日漂移 issue 去重。
