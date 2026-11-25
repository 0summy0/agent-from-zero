# Agent From Zero

一套中英双语、零 GPU 也能运行、每章代码都由 CI 真实执行的 AI Agent 入门课程。当前交付仅包含工程地基与第 0 号样章 1.1 Tokenizer，不包含后续章节。

A bilingual AI Agent course for beginners, designed to run without a GPU and to verify every chapter through executable CI checks. This delivery contains only the project foundation and sample chapter 1.1, Tokenizer; later chapters are intentionally out of scope.

## 前置要求 / Prerequisites

- 会 Python 函数、循环和异常处理。
- 会执行 `git clone`。
- 不要求微积分与线性代数。
- Understand Python functions, loops, and exceptions, and know how to run `git clone`.
- No calculus or linear algebra is required.

## 从零运行 / Run from scratch

```bash
uv sync --frozen
uv run pytest
uv run python tools/check_parity.py && uv run python tools/check_quiz.py
```

默认测试闸门排除 `requires_gpu`、`requires_api_key` 和 `slow`，但有意保留 `requires_network`。离线运行时可执行 `uv run pytest -m "not requires_network and not requires_gpu and not requires_api_key and not slow"`。模型文件下载支持 `HF_ENDPOINT=https://hf-mirror.com`，缓存位于 `.cache/` 或 `HF_HOME` 指定的目录。

The default test gate excludes GPU, paid-key, and slow tests, while network tests remain enabled. Offline users can run `uv run pytest -m "not requires_network and not requires_gpu and not requires_api_key and not slow"`. Model downloads honor `HF_ENDPOINT=https://hf-mirror.com` and use `.cache/` or `HF_HOME` for cached files.

## 硬件基线 / Hardware baseline

测量环境：2026-11-24，Linux aarch64 容器，2 核，7.8 GiB 内存，Python 3.12.5，uv 0.13.9，无 NVIDIA GPU。

| 项目 | 实测结果或状态 | 测量条件 |
|---|---|---|
| `uv sync --frozen` 冷启动 | 3.835 s | 最终锁文件，新建 `.venv` 与全新临时 uv 缓存，2 核 / 7.8 GiB |
| `.venv` 磁盘占用 | 126M | 最终锁文件冷启动完成后，2 核 / 7.8 GiB |
| 1.1 样章冒烟单次耗时 | 2.227 s（pytest 内部 0.33 s） | tokenizer 已缓存，外部计时包含 Python 进程启动，2 核 / 7.8 GiB |
| 1.1 样章冒烟峰值内存 | 123.77 MiB（126744 KiB） | `resource.RUSAGE_CHILDREN`，tokenizer 已缓存，2 核 / 7.8 GiB |
| 本机 CPU 路径 | 可实测；无需 CUDA | Linux aarch64 容器 |
| 免费托管 Notebook | 未测：本轮不创建或使用外部托管账号 | 无 |
| 容器路径 | 未测：当前机器无 Docker | `command -v docker` 无输出 |

上述数据只代表本次容器，不是对所有电脑的最低配置承诺。章节 front-matter 中的内存值来自本机实测。

## 环境路径 / Environment options

1. **本机 CPU**：当前已验证的默认路径；安装 uv 后运行上方三条命令。
2. **免费托管 Notebook**：尚未实测，不作为当前可用性的依据。
3. **容器**：当前执行环境本身是 Linux 容器，但 Docker 构建与运行未测。

## 课程目录 / Course index

| 章节 | 中文 | English | 冒烟测试 |
|---|---|---|---|
| 1.1 Tokenizer | [中文样章](docs/zh/1.1-tokenizer.md) | [English sample](docs/en/1.1-tokenizer.md) | `tests/smoke/test_chapter_1_1_tokenizer.py` |

后续 Stage 1.2–4.4 不在本轮范围内，待样章 DoD 全部通过并由用户确认后再推进。
