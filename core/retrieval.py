from dataclasses import dataclass
from pathlib import Path
import yaml
from rank_bm25 import BM25Okapi

@dataclass
class RetrievedContext:
    table_snippets: str
    semantic_snippets: str

def _tokenize(s: str):
    return [t.lower() for t in s.replace("\n", " ").split()]

class BM25Retriever:
    def __init__(self, docs: list[str], names: list[str]):
        self.docs = docs
        self.names = names
        self.corpus = [_tokenize(d) for d in docs]
        self.bm25 = BM25Okapi(self.corpus)

    def topk(self, query: str, k: int = 6):
        q = _tokenize(query)
        scores = self.bm25.get_scores(q)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.names[i], self.docs[i], float(scores[i])) for i in ranked]

def load_semantic_docs(root: Path) -> list[str]:
    docs = []
    for p in [root/"semantic_layer/metrics.yaml", root/"semantic_layer/glossary.yaml", root/"semantic_layer/dimensions.yaml"]:
        if not p.exists():
            continue
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        docs.append(f"FILE: {p.name}\n{yaml.safe_dump(data, sort_keys=False)}")
    return docs

def build_retrievers(schema_info: str, root: Path):
    # Make table docs from schema_info by splitting on "Table:"
    table_docs = []
    table_names = []

    chunks = schema_info.split("Table:")
    for c in chunks[1:]:
        snippet = "Table:" + c
        first_line = c.strip().splitlines()[0] if c.strip().splitlines() else "UNKNOWN"
        table_name = first_line.split()[0]
        table_names.append(table_name)
        table_docs.append(snippet)

    semantic_docs = load_semantic_docs(root)
    semantic_names = [f"semantic_{i}" for i in range(len(semantic_docs))]

    table_ret = BM25Retriever(table_docs, table_names) if table_docs else None
    sem_ret = BM25Retriever(semantic_docs, semantic_names) if semantic_docs else None
    return table_ret, sem_ret

def retrieve_context(query: str, table_ret, sem_ret, k_tables=6, k_sem=2) -> RetrievedContext:
    table_snips = []
    if table_ret:
        for name, doc, _ in table_ret.topk(query, k=k_tables):
            table_snips.append(doc)

    sem_snips = []
    if sem_ret:
        for _, doc, _ in sem_ret.topk(query, k=k_sem):
            sem_snips.append(doc)

    return RetrievedContext(
        table_snippets="\n\n".join(table_snips),
        semantic_snippets="\n\n".join(sem_snips)
    )