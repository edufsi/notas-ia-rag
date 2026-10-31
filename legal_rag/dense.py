from __future__ import annotations

import json
import threading

from .errors import IndexUnavailableError
from .lexical import LexicalRetriever
from .paths import RAGPaths


MODELS = {
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    "e5-base": ("intfloat/multilingual-e5-base", "query: ", "passage: "),
    "bge-m3": ("BAAI/bge-m3", "", ""),
}


def corpus_version(paths: RAGPaths) -> str:
    if not paths.manifest.is_file():
        raise IndexUnavailableError(f"Manifesto ausente: {paths.manifest}")
    return json.loads(paths.manifest.read_text(encoding="utf-8"))["versao"]


def chunk_text(chunk: dict) -> str:
    return f"{chunk['documento']}, {chunk['secao']}. {chunk['contexto']}\n{chunk['texto']}"


def load_model(name: str, *, local_only: bool = False):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise IndexUnavailableError(
            "Dependências densas ausentes. Instale o extra 'dense'."
        ) from exc
    try:
        return SentenceTransformer(
            MODELS[name][0],
            device="cpu",
            local_files_only=local_only,
        )
    except Exception as exc:
        if local_only:
            raise IndexUnavailableError(
                "Modelo denso não está completo no cache local; reconstrua o índice "
                "pelo comando administrativo antes de usar a busca densa."
            ) from exc
        raise


def index_dense(name: str = "e5-small", paths: RAGPaths | None = None) -> int:
    if name not in MODELS:
        raise ValueError(f"Modelo denso desconhecido: {name}")
    paths = paths or RAGPaths.from_root()
    try:
        import faiss
        import numpy as np
    except ImportError as exc:
        raise IndexUnavailableError("Dependências FAISS/NumPy ausentes.") from exc
    chunks = [json.loads(line) for line in paths.corpus.read_text(encoding="utf-8").splitlines()]
    model = load_model(name)
    vectors = model.encode(
        [MODELS[name][2] + chunk_text(chunk) for chunk in chunks],
        batch_size=8,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.asarray(vectors, dtype="float32"))
    paths.indexes.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(paths.indexes / f"densa-{name}.faiss"))
    (paths.indexes / f"densa-{name}.json").write_text(json.dumps({
        "modelo": MODELS[name][0],
        "corpus": corpus_version(paths),
        "ids": [chunk["id"] for chunk in chunks],
    }, ensure_ascii=False), encoding="utf-8")
    return len(chunks)


class DenseRetriever:
    def __init__(self, name: str = "e5-small", paths: RAGPaths | None = None):
        self.name = name
        self.paths = paths or RAGPaths.from_root()
        self._lock = threading.Lock()
        self._loaded = False

    @property
    def available(self) -> bool:
        meta = self.paths.indexes / f"densa-{self.name}.json"
        index = self.paths.indexes / f"densa-{self.name}.faiss"
        if not meta.is_file() or not index.is_file():
            return False
        try:
            return json.loads(meta.read_text(encoding="utf-8"))["corpus"] == corpus_version(self.paths)
        except (KeyError, ValueError, IndexUnavailableError):
            return False

    def _load(self) -> None:
        if self._loaded:
            return
        if not self.available:
            raise IndexUnavailableError(
                f"Índice denso {self.name} ausente ou incompatível com o corpus."
            )
        try:
            import faiss
        except ImportError as exc:
            raise IndexUnavailableError("FAISS não está instalado.") from exc
        meta = json.loads(
            (self.paths.indexes / f"densa-{self.name}.json").read_text(encoding="utf-8")
        )
        self.index = faiss.read_index(str(self.paths.indexes / f"densa-{self.name}.faiss"))
        self.ids = meta["ids"]
        self.chunks = {
            item["id"]: item
            for item in (
                json.loads(line) for line in self.paths.corpus.read_text(encoding="utf-8").splitlines()
            )
        }
        # Uma consulta nunca deve iniciar downloads. A preparação do modelo é
        # responsabilidade do comando administrativo `legal_rag index`.
        self.model = load_model(self.name, local_only=True)
        self._loaded = True

    def search(self, query: str, limit: int = 5) -> list[dict]:
        try:
            import numpy as np
        except ImportError as exc:
            raise IndexUnavailableError("NumPy não está instalado.") from exc
        with self._lock:
            self._load()
            vector = self.model.encode(
                [MODELS[self.name][1] + query], normalize_embeddings=True
            )
            scores, positions = self.index.search(
                np.asarray(vector, dtype="float32"), min(limit, len(self.ids))
            )
            return [
                {**self.chunks[self.ids[position]], "score": float(score)}
                for score, position in zip(scores[0], positions[0])
                if position >= 0
            ]


class HybridRetriever:
    def __init__(self, lexical: LexicalRetriever, dense: DenseRetriever,
                 rrf_k: int = 60, candidates: int = 30):
        self.lexical = lexical
        self.dense = dense
        self.rrf_k = rrf_k
        self.candidates = candidates

    @property
    def available(self) -> bool:
        return self.lexical.available and self.dense.available

    def search(self, query: str, limit: int = 5) -> list[dict]:
        fusion: dict[str, float] = {}
        by_id: dict[str, dict] = {}
        for results in (
            self.lexical.search(query, self.candidates),
            self.dense.search(query, self.candidates),
        ):
            for position, result in enumerate(results, 1):
                fusion[result["id"]] = fusion.get(result["id"], 0.0) + 1 / (
                    self.rrf_k + position
                )
                by_id.setdefault(result["id"], result)
        ordered = sorted(fusion, key=fusion.get, reverse=True)[:limit]
        return [{**by_id[item], "score": fusion[item]} for item in ordered]

