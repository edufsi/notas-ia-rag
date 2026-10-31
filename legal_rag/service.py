from __future__ import annotations

import json

from .dense import DenseRetriever, HybridRetriever, corpus_version
from .errors import IndexUnavailableError, InvalidSearchError
from .lexical import LexicalRetriever
from .models import LegalSearchResponse, LegalSource, SearchStrategy
from .paths import RAGPaths


class LegalSearchService:
    def __init__(self, paths: RAGPaths | None = None, dense_model: str = "e5-small"):
        self.paths = paths or RAGPaths.from_root()
        self.lexical = LexicalRetriever(self.paths)
        self.dense = DenseRetriever(dense_model, self.paths)
        self.hybrid = HybridRetriever(self.lexical, self.dense)

    def status(self) -> dict:
        version = None
        if self.paths.manifest.is_file():
            version = json.loads(self.paths.manifest.read_text(encoding="utf-8")).get("versao")
        return {
            "ready": self.lexical.available,
            "corpus_version": version,
            "bm25": self.lexical.available,
            "dense": self.dense.available,
            "hybrid": self.hybrid.available,
        }

    def search(self, query: str, strategy: SearchStrategy | None = None,
               top_k: int | None = None) -> LegalSearchResponse:
        query = query.strip() if isinstance(query, str) else ""
        if not query or len(query) > 1000:
            raise InvalidSearchError("query deve conter entre 1 e 1000 caracteres")
        requested: SearchStrategy = strategy or "auto"
        if requested not in {"auto", "bm25", "dense", "hybrid"}:
            raise InvalidSearchError(f"Estratégia desconhecida: {requested}")
        limit = 5 if top_k is None else top_k
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
            raise InvalidSearchError("top_k deve ser um inteiro entre 1 e 10")

        effective = requested
        fallback = None
        if requested == "auto":
            if self.hybrid.available:
                effective = "hybrid"
            else:
                effective = "bm25"
                fallback = "Índice denso indisponível; busca BM25 utilizada."

        if effective == "bm25":
            results = self.lexical.search(query, limit)
        elif effective == "dense":
            if not self.dense.available:
                raise IndexUnavailableError("Busca densa solicitada, mas o índice não está pronto.")
            results = self.dense.search(query, limit)
        else:
            if not self.hybrid.available:
                raise IndexUnavailableError("Busca híbrida solicitada, mas seus índices não estão prontos.")
            try:
                results = self.hybrid.search(query, limit)
            except IndexUnavailableError as exc:
                if requested != "auto":
                    raise
                effective = "bm25"
                fallback = f"Busca densa indisponível em tempo de execução; BM25 utilizado. ({exc})"
                results = self.lexical.search(query, limit)

        return LegalSearchResponse(
            query=query,
            requested_strategy=requested,
            effective_strategy=effective,
            fallback_reason=fallback,
            corpus_version=corpus_version(self.paths),
            results=[self._source(item) for item in results],
        )

    @staticmethod
    def _source(item: dict) -> LegalSource:
        return LegalSource(
            chunk_id=item["id"],
            document=item["documento"],
            section=item["secao"],
            context=item["contexto"],
            text=item["texto"],
            organization=item["orgao"],
            source_type=item["tipo"],
            jurisdiction=item["jurisdicao"],
            locality=item.get("localidade"),
            url=item["url"],
            published_at=item["publicado_em"],
            verified_at=item["verificado_em"],
            score=float(item["score"]),
        )

