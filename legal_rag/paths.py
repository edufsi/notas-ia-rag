from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RAGPaths:
    root: Path
    corpus: Path
    manifest: Path
    indexes: Path

    @classmethod
    def from_root(cls, root: str | Path | None = None) -> "RAGPaths":
        resolved = Path(root).resolve() if root else Path(__file__).resolve().parents[1]
        return cls(
            root=resolved,
            corpus=resolved / "corpus" / "trechos.jsonl",
            manifest=resolved / "corpus" / "manifesto.json",
            indexes=resolved / "indice",
        )

