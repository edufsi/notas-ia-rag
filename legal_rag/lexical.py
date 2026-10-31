from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from .errors import IndexUnavailableError
from .paths import RAGPaths


STOPWORDS = set("""
a à ao aos as às até com como da das de dela dele do dos e é ela ele em entre era essa esse esta este eu foi
for há isso isto já la lhe mais mas me meu minha muito na nas não nem no nos nós o os ou para pela pelas
pelo pelos por qual quais quando que quem se sem ser seu sua são só também te tem tenho ter tu um uma uns
umas vai você vou posso pode fazer faz sobre quero saber tá ta to tô pra pro
""".split())
PESOS_BM25 = (0.0, 1.0, 0.3, 0.2)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


NORMALIZED_STOPWORDS = {normalizar(item) for item in STOPWORDS}


def termos(consulta: str) -> list[str]:
    palavras = re.findall(r"\w+", normalizar(consulta))
    return [item for item in palavras if item not in NORMALIZED_STOPWORDS and len(item) > 1]


def indexar(paths: RAGPaths | None = None) -> int:
    paths = paths or RAGPaths.from_root()
    if not paths.corpus.is_file():
        raise IndexUnavailableError(f"Corpus ausente: {paths.corpus}")
    target = paths.indexes / "lexical.sqlite"
    paths.indexes.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    connection = sqlite3.connect(target)
    try:
        connection.execute("CREATE TABLE trechos (id TEXT PRIMARY KEY, dados TEXT)")
        connection.execute("""CREATE VIRTUAL TABLE fts USING fts5(
            id UNINDEXED, texto, contexto, documento,
            tokenize = 'unicode61 remove_diacritics 2', prefix = '4 5 6')""")
        count = 0
        for line in paths.corpus.read_text(encoding="utf-8").splitlines():
            chunk = json.loads(line)
            connection.execute("INSERT INTO trechos VALUES (?, ?)", (chunk["id"], line))
            connection.execute(
                "INSERT INTO fts VALUES (?, ?, ?, ?)",
                (chunk["id"], chunk["texto"], chunk["contexto"], chunk["documento"]),
            )
            count += 1
        connection.commit()
        return count
    finally:
        connection.close()


class LexicalRetriever:
    def __init__(self, paths: RAGPaths | None = None):
        self.paths = paths or RAGPaths.from_root()
        self.index_path = self.paths.indexes / "lexical.sqlite"

    @property
    def available(self) -> bool:
        return self.index_path.is_file()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self.available:
            raise IndexUnavailableError(
                "Índice BM25 ausente. Execute: python -m legal_rag index --strategy bm25"
            )
        words = termos(query)
        if not words:
            return []
        expression = " OR ".join(
            f'"{word[:5]}"*' if len(word) > 5 else f'"{word}"' for word in words
        )
        weights = ", ".join(str(item) for item in PESOS_BM25)
        connection = sqlite3.connect(self.index_path, timeout=30)
        try:
            rows = connection.execute(
                f"""SELECT fts.id, bm25(fts, {weights}) AS score, trechos.dados
                    FROM fts JOIN trechos ON trechos.id = fts.id
                    WHERE fts MATCH ? ORDER BY score LIMIT ?""",
                (expression, limit),
            ).fetchall()
        finally:
            connection.close()
        return [{**json.loads(data), "score": -score} for _, score, data in rows]

