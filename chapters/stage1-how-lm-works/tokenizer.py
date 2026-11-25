import json
import os
import urllib.request
from pathlib import Path

from tokenizers import Tokenizer

CHAPTER_ID = "1.1-tokenizer"
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
CHINESE_SAMPLE = "智能体现在会调用工具"
ENGLISH_SAMPLE = "Agents can call tools now"
ROOT = Path(__file__).resolve().parents[2]


def tokenizer_path():
    cache_root = Path(os.environ.get("HF_HOME", ROOT / ".cache" / "huggingface"))
    return cache_root / "models" / "Qwen--Qwen2.5-0.5B-Instruct" / "tokenizer.json"


def download_tokenizer(url, path):
    temporary_path = path.with_suffix(".tmp")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "agent-from-zero/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if not data:
            raise RuntimeError(f"empty tokenizer download: {url}")
        temporary_path.write_bytes(data)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_tokenizer():
    path = tokenizer_path()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    override_url = os.environ.get("TOKENIZER_URL")
    if override_url:
        urls = [override_url]
    else:
        endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")
        urls = [
            f"{endpoint}/{MODEL_ID}/resolve/main/tokenizer.json",
            f"https://modelscope.cn/models/{MODEL_ID}/resolve/master/tokenizer.json",
        ]
    errors = []
    for url in urls:
        try:
            download_tokenizer(url, path)
            return path
        except (OSError, RuntimeError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("tokenizer download failed\n" + "\n".join(errors))


def encode_sample(tokenizer, text):
    encoding = tokenizer.encode(text, add_special_tokens=False)
    return {
        "text": text,
        "characters": len(text),
        "tokens": [tokenizer.decode([token_id], skip_special_tokens=False) for token_id in encoding.ids],
        "token_ids": encoding.ids,
        "token_count": len(encoding.ids),
    }


def run_minimal_path():
    tokenizer = Tokenizer.from_file(str(ensure_tokenizer()))
    chinese = encode_sample(tokenizer, CHINESE_SAMPLE)
    english = encode_sample(tokenizer, ENGLISH_SAMPLE)
    return {
        "chapter": CHAPTER_ID,
        "model": MODEL_ID,
        "model_weights_downloaded": False,
        "chinese": chinese,
        "english": english,
        "token_count_difference": chinese["token_count"] - english["token_count"],
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
