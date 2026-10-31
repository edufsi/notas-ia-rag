from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .models import LegalSearchResponse, SearchStrategy
from .service import LegalSearchService


def create_server(service: LegalSearchService | None = None) -> FastMCP:
    service = service or LegalSearchService()
    mcp = FastMCP("Notas.IA Legal RAG")

    @mcp.tool(name="search_legal_sources")
    def search_legal_sources(
        query: str,
        strategy: SearchStrategy | None = None,
        top_k: int | None = None,
    ) -> LegalSearchResponse:
        """Pesquisa trechos de fontes jurídicas oficiais brasileiras.

        Retorna possíveis fontes para fundamentação. Os resultados não constituem
        conclusão jurídica e precisam ser avaliados no contexto da pergunta.
        """
        return service.search(query, strategy, top_k)

    @mcp.custom_route("/health/live", methods=["GET"])
    async def live(_: Request):
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/health/ready", methods=["GET"])
    async def ready(_: Request):
        status = service.status()
        return JSONResponse(
            {"status": "ok" if status["ready"] else "unavailable", **status},
            status_code=200 if status["ready"] else 503,
        )

    return mcp


mcp = create_server()

