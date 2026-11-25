import math
import random
from collections import defaultdict

CHAPTER_ID = "1.2-sampling"
CORPUS = [
    "the cat sat on the mat",
    "the dog sat on the rug",
    "the cat slept on the mat",
    "the dog ran with the cat",
    "the bird sat on the tree",
]


def tokenize(text):
    return text.lower().split()


def build_bigram(corpus):
    transitions = defaultdict(lambda: defaultdict(int))
    for sentence in corpus:
        tokens = tokenize(sentence)
        for left, right in zip(tokens, tokens[1:]):
            transitions[left][right] += 1
    vocabulary = sorted({token for sentence in corpus for token in tokenize(sentence)})
    return {"transitions": transitions, "vocabulary": vocabulary}


def next_token_distribution(model, context):
    vocabulary = model["vocabulary"]
    counts = model["transitions"].get(context, {})
    total = sum(counts.values()) + len(vocabulary)
    return {token: (counts.get(token, 0) + 1) / total for token in vocabulary}


def apply_temperature(probabilities, temperature):
    if temperature <= 0:
        raise ValueError("temperature must be greater than zero")
    tokens = list(probabilities)
    logits = [math.log(probabilities[token]) for token in tokens]
    scaled = [value / temperature for value in logits]
    peak = max(scaled)
    weights = [math.exp(value - peak) for value in scaled]
    total = sum(weights)
    return {token: weight / total for token, weight in zip(tokens, weights)}


def top_p_filter(probabilities, p):
    if not 0 < p <= 1:
        raise ValueError("top_p must be in (0, 1]")
    ordered = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
    kept = []
    cumulative = 0.0
    for token, probability in ordered:
        kept.append((token, probability))
        cumulative += probability
        if cumulative >= p:
            break
    mass = sum(probability for _, probability in kept)
    return {token: probability / mass for token, probability in kept}, cumulative


def weighted_choice(probabilities, seed):
    rng = random.Random(seed)
    target = rng.random()
    cumulative = 0.0
    for token, probability in probabilities.items():
        cumulative += probability
        if target <= cumulative:
            return token
    return next(reversed(probabilities))


def rounded(probabilities):
    return {token: round(value, 6) for token, value in probabilities.items()}


def run_minimal_path():
    model = build_bigram(CORPUS)
    base = next_token_distribution(model, "the")
    tempered = apply_temperature(base, temperature=0.5)
    nucleus, original_mass = top_p_filter(tempered, p=0.8)
    return {
        "chapter": CHAPTER_ID,
        "context": "the",
        "temperature": 0.5,
        "top_p": 0.8,
        "base_distribution": rounded(base),
        "tempered_distribution": rounded(tempered),
        "nucleus_distribution": rounded(nucleus),
        "nucleus_original_mass": round(original_mass, 6),
        "sampled_token": weighted_choice(nucleus, seed=7),
    }


def main():
    import json

    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
