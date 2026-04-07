"""双向一致性测试生成器"""
import os
from ..judge.base import BaseJudge
from ..schemas import BidirectionalTest


def generate_bidirectional_tests(
    knowledge_base_path: str,
    judge: BaseJudge,
    num_samples: int = 20,
) -> list[BidirectionalTest]:
    """
    从知识库文档中提取二元关系，生成正向/反向 query 对。
    """
    documents = _load_documents(knowledge_base_path)
    if not documents:
        raise ValueError(f"未找到文档: {knowledge_base_path}")

    per_doc = max(1, num_samples // len(documents))
    prompt_template = BaseJudge.load_prompt("bidirectional_gen")

    tests = []
    for doc_id, text in documents.items():
        doc_text = text[:4000] if len(text) > 4000 else text
        prompt = prompt_template.replace("{num_samples}", str(per_doc)).replace("{document}", doc_text)
        raw = judge.call_json(prompt)

        items = []
        if isinstance(raw, dict):
            if "_array" in raw:
                items = raw["_array"]
            elif "tests" in raw:
                items = raw["tests"]
            elif "forward_query" in raw:
                items = [raw]

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                tests.append(BidirectionalTest(
                    relation=item.get("relation", ""),
                    forward_query=item.get("forward_query", ""),
                    backward_query=item.get("backward_query", ""),
                    expected_entity=item.get("expected_entity", ""),
                    source_doc_id=doc_id,
                ))
            except Exception:
                continue

        if len(tests) >= num_samples:
            break

    return tests[:num_samples]


def _load_documents(path: str) -> dict:
    docs = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            docs[os.path.basename(path)] = f.read()
        return docs
    for fname in sorted(os.listdir(path)):
        if fname.endswith(".txt"):
            with open(os.path.join(path, fname), "r", encoding="utf-8") as f:
                docs[fname] = f.read()
    return docs
