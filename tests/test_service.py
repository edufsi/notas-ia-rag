from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from legal_rag.errors import IndexUnavailableError, InvalidSearchError
from legal_rag.lexical import indexar
from legal_rag.paths import RAGPaths
from legal_rag.service import LegalSearchService


def fixture_paths(tmp_path: Path) -> RAGPaths:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    chunks = [{
        "id": "lei:art1", "documento": "Lei de teste", "secao": "Art. 1",
        "contexto": "Proteção", "texto": "A violência patrimonial inclui retenção de documentos.",
        "orgao": "Órgão oficial", "tipo": "legislacao", "jurisdicao": "Brasil",
        "localidade": None, "url": "https://example.test/art1", "publicado_em": "2020-01-01",
        "verificado_em": "2026-01-01",
    }]
    (corpus / "trechos.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in chunks), encoding="utf-8"
    )
    (corpus / "manifesto.json").write_text(
        json.dumps({"versao": "fixture", "total_trechos": 1}), encoding="utf-8"
    )
    return RAGPaths.from_root(tmp_path)


def test_auto_falls_back_to_bm25_and_accepts_nulls(tmp_path):
    paths = fixture_paths(tmp_path)
    indexar(paths)
    result = LegalSearchService(paths).search("documentos", None, None)
    assert result.requested_strategy == "auto"
    assert result.effective_strategy == "bm25"
    assert result.fallback_reason
    assert result.results[0].chunk_id == "lei:art1"


def test_explicit_dense_fails_when_unavailable(tmp_path):
    paths = fixture_paths(tmp_path)
    indexar(paths)
    with pytest.raises(IndexUnavailableError):
        LegalSearchService(paths).search("documentos", "dense", 3)


def test_auto_falls_back_when_dense_fails_at_runtime(tmp_path):
    paths = fixture_paths(tmp_path)
    indexar(paths)
    service = LegalSearchService(paths)

    class BrokenHybrid:
        available = True

        @staticmethod
        def search(query, limit):
            raise IndexUnavailableError("modelo não está no cache")

    service.hybrid = BrokenHybrid()
    result = service.search("documentos", "auto", 3)
    assert result.effective_strategy == "bm25"
    assert "tempo de execução" in result.fallback_reason
    assert result.results[0].chunk_id == "lei:art1"


@pytest.mark.parametrize("top_k", [0, 11, True, "5"])
def test_invalid_top_k(tmp_path, top_k):
    paths = fixture_paths(tmp_path)
    indexar(paths)
    with pytest.raises(InvalidSearchError):
        LegalSearchService(paths).search("documentos", "bm25", top_k)

