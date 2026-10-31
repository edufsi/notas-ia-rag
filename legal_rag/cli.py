from __future__ import annotations

import argparse

from .dense import MODELS, index_dense
from .lexical import indexar as index_lexical


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG jurídico do Notas.IA")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--download", action="store_true")
    index = commands.add_parser("index")
    index.add_argument("--strategy", required=True, choices=("bm25", "dense"))
    index.add_argument("--model", default="e5-small", choices=tuple(MODELS))
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8001)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.command == "ingest":
        from ingestao import gerar
        gerar(args.download)
    elif args.command == "index":
        count = index_lexical() if args.strategy == "bm25" else index_dense(args.model)
        print(f"{count} trechos indexados ({args.strategy}).")
    elif args.command == "serve":
        from .mcp_server import mcp
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        import sys
        from avaliar import main as evaluate_main
        sys.argv = ["avaliar.py", *args.args]
        evaluate_main()

