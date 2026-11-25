# 贡献指南 / Contributing

## 新增一章的最低契约

每章必须同时提供：

1. `chapters/<stage>/<name>.py`
   - 暴露 `CHAPTER_ID`
   - 暴露 `run_minimal_path()`，返回可 JSON 序列化结果
   - 提供 `main()` 打印结果
   - 默认无 GPU、无网络、无付费 API
2. `docs/zh/<id>.md` 与 `docs/en/<id>.md`
   - 八个 front-matter 字段：`id`、`title_zh`、`title_en`、`prereq`、`est_minutes`、`ram_min_mb`、`needs_api_key`、`source_revision`
   - 作者标记 `<!-- AUTHOR: 你的名字 -->`
   - 中英代码块逐字一致
   - 标题数量差不超过 1
3. `quizzes/<id>.json` 与 `quizzes/<id>.en.json`
   - 至少 3 题
   - 每题 4 个选项
   - 中英答案下标一致
   - 各语言选项长度比小于 2.0
4. `tests/smoke/test_chapter_<id>.py`
   - 验证模块导入
   - 验证最小路径
   - 验证关键不变量
   - CPU 耗时小于 3 分钟

## 提交前检查

```bash
uv sync --frozen
uv run python tools/check_bounds.py
uv run python tools/check_parity.py
uv run python tools/check_quiz.py
uv run pytest tests/meta
uv run pytest
```

## 内容原则

- 先讲机制，再讲工具；不要用框架名替代解释。
- 示例必须小、确定、可复现。
- 不要声称模拟代码是真实大模型行为。
- 不要加入无法离线验证的外部链接作为核心步骤。
- 新增依赖必须有上界，并更新 `uv.lock`。
- 修改 `tools/` 或 `.python-version` 时，确认 CI 路径过滤会触发。

## 排版与语言

- 中文使用自然表达，不提交机翻式长句。
- 英文与中文保持相同概念深度，不额外删减关键限制。
- 代码、命令、JSON 字段名保持逐字一致。
