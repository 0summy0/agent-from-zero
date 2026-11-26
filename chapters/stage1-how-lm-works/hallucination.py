import json
import re

CHAPTER_ID = "1.4-hallucination"

KNOWLEDGE_BASE = [
    {
        "id": "kb-capital-france",
        "title": "Capital of France",
        "keywords": ["paris", "capital", "france"],
        "text": "Paris is the capital of France.",
    },
    {
        "id": "kb-capital-canada",
        "title": "Capital of Canada",
        "keywords": ["ottawa", "capital", "canada"],
        "text": "Ottawa is the capital of Canada.",
    },
    {
        "id": "kb-water-freezing-point",
        "title": "Freezing point of water",
        "keywords": ["freezing", "point", "water", "celsius"],
        "text": "The freezing point of water is 0 degrees Celsius at standard atmospheric pressure.",
    },
]

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}

ABSTENTION_MESSAGE = "I don't know; more information is needed."


def tokenize(text):
    return re.findall(r"[^\W_]+", text.casefold())


def query_keywords(question):
    return sorted(set(tokenize(question)) - STOP_WORDS)


def retrieve_evidence(question, knowledge_base):
    keywords = query_keywords(question)
    if not keywords:
        return []

    matches = []
    for item in knowledge_base:
        title = item["title"]
        aliases = item.get("keywords", [])
        text = item["text"]
        priority_terms = set(tokenize(" ".join([title, *aliases])))
        searchable_terms = priority_terms | set(tokenize(text))

        # A fact is usable only when one record covers every content keyword.
        if not set(keywords).issubset(searchable_terms):
            continue
        score = len(keywords) + len(set(keywords) & priority_terms)
        matches.append((score, item))

    matches.sort(key=lambda match: (-match[0], match[1]["id"]))
    return [{"id": item["id"], "title": item["title"], "text": item["text"]} for _, item in matches]


def answer_with_evidence(question, knowledge_base):
    evidence = retrieve_evidence(question, knowledge_base)
    if not evidence:
        return {
            "status": "abstain",
            "answer": ABSTENTION_MESSAGE,
            "evidence": [],
            "query_keywords": query_keywords(question),
        }

    primary = evidence[0]
    return {
        "status": "grounded",
        "answer": f"{primary['text']} [{primary['id']}]",
        "evidence": evidence,
        "query_keywords": query_keywords(question),
    }


def run_minimal_path():
    grounded_question = "What is the capital of France?"
    outside_question = "What is the capital of Atlantis?"
    return {
        "chapter": CHAPTER_ID,
        "knowledge_base_size": len(KNOWLEDGE_BASE),
        "grounded_case": {
            "question": grounded_question,
            **answer_with_evidence(grounded_question, KNOWLEDGE_BASE),
        },
        "abstention_case": {
            "question": outside_question,
            **answer_with_evidence(outside_question, KNOWLEDGE_BASE),
        },
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
