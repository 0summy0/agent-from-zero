import json
import math

CHAPTER_ID = "1.3-attention"

# 五个手工构造的二维 token 向量；每行依次是 query、key、value。
TOY_TOKENS = ["I", "like", "small", "models", "too"]
TOY_VECTORS = [
    ([1.0, 0.0], [1.0, 0.0], [1.0, 0.0]),
    ([0.8, 0.6], [0.9, 0.4], [0.0, 1.0]),
    ([0.2, 1.0], [0.1, 1.0], [0.0, 1.0]),
    ([0.6, 0.8], [0.7, 0.7], [1.0, 0.0]),
    ([0.7, 0.7], [0.6, 0.8], [1.0, 0.0]),
]


def dot_product(left, right):
    """计算两个等长向量的点积：对应位置相乘，再相加。"""
    if not left or len(left) != len(right):
        raise ValueError("vectors must be non-empty and have the same length")
    return sum(a * b for a, b in zip(left, right))


def softmax(scores):
    """把一组分数变成总和为 1 的概率；先减最大值避免溢出。"""
    if not scores:
        raise ValueError("scores must not be empty")
    peak = max(scores)
    exponentials = [math.exp(score - peak) for score in scores]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def scaled_dot_product_scores(query, keys):
    """计算 query 与每个 key 的缩放点积分数。"""
    if not keys or any(len(key) != len(query) for key in keys):
        raise ValueError("query and keys must be non-empty vectors of equal length")
    scale = math.sqrt(len(query))
    return [dot_product(query, key) / scale for key in keys]


def weighted_sum(weights, values):
    """按权重混合 value 向量，得到 context vector。"""
    if not values or len(weights) != len(values):
        raise ValueError("weights and values must have the same non-zero length")
    dimension = len(values[0])
    if any(len(value) != dimension for value in values):
        raise ValueError("value vectors must have the same length")
    return [
        sum(weight * value[index] for weight, value in zip(weights, values))
        for index in range(dimension)
    ]


def attention(query, keys, values):
    """对一个 query 执行 scaled dot-product attention。"""
    if len(keys) != len(values):
        raise ValueError("keys and values must have the same length")
    scores = scaled_dot_product_scores(query, keys)
    weights = softmax(scores)
    return {
        "scaled_scores": scores,
        "attention_weights": weights,
        "context_vector": weighted_sum(weights, values),
    }


def truncate_to_recent_tokens(tokens, window_size):
    """超出窗口时只保留最近 window_size 个 token，并保持原顺序。"""
    if not isinstance(window_size, int) or isinstance(window_size, bool) or window_size <= 0:
        raise ValueError("window_size must be a positive integer")
    start = max(0, len(tokens) - window_size)
    return tokens[start:]


def rounded_vector(vector):
    return [round(value, 6) for value in vector]


def attention_demo(tokens, vectors, window_size):
    """对窗口内的每个 token 计算 attention，返回完整的中间结果。"""
    if len(tokens) != len(vectors):
        raise ValueError("tokens and vectors must have the same length")
    recent_tokens = truncate_to_recent_tokens(tokens, window_size)
    recent_vectors = vectors[len(tokens) - len(recent_tokens):]
    keys = [item[1] for item in recent_vectors]
    values = [item[2] for item in recent_vectors]
    rows = []
    for token, (query, _, _) in zip(recent_tokens, recent_vectors):
        result = attention(query, keys, values)
        rows.append({
            "query_token": token,
            "query": query,
            "scaled_scores": rounded_vector(result["scaled_scores"]),
            "attention_weights": rounded_vector(result["attention_weights"]),
            "context_vector": rounded_vector(result["context_vector"]),
        })
    return {
        "window_size": window_size,
        "kept_tokens": recent_tokens,
        "dropped_tokens": tokens[:len(tokens) - len(recent_tokens)],
        "keys": keys,
        "values": values,
        "rows": rows,
    }


def run_minimal_path():
    """运行可重复、无需模型或网络的完整教学示例。"""
    full = attention_demo(TOY_TOKENS, TOY_VECTORS, window_size=len(TOY_TOKENS))
    truncated = attention_demo(TOY_TOKENS, TOY_VECTORS, window_size=3)
    return {
        "chapter": CHAPTER_ID,
        "vector_dimension": len(TOY_VECTORS[0][0]),
        "scale": round(math.sqrt(len(TOY_VECTORS[0][0])), 6),
        "full_window": full,
        "context_window": truncated,
        "demo_scope": "toy single-head full attention; real models use learned projections, masks, and multiple heads",
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
