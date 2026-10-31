# Notas.IA Legal RAG

Serviço independente de recuperação de fontes jurídicas oficiais. Ele expõe à LLM
somente a ferramenta MCP `search_legal_sources`; ingestão, indexação e avaliação são
operações administrativas de linha de comando.

O serviço retorna trechos candidatos e seus metadados. Ele não declara que um trecho
resolve definitivamente uma pergunta e não produz conclusão jurídica.

## Instalação

```powershell
python -m pip install -e ".[dev]"
python -m legal_rag ingest
python -m legal_rag index --strategy bm25
```

Para preparar busca densa ou híbrida:

```powershell
python -m pip install -e ".[dense,dev]"
python -m legal_rag index --strategy dense --model e5-small
```

O download e o carregamento inicial do modelo pertencem ao comando de indexação. Uma
consulta ao servidor nunca inicia downloads. Se os artefatos densos não estiverem
completos no cache local, `auto` informa o fallback e usa BM25; pedidos explícitos de
`dense` ou `hybrid` falham de forma tipada.

## Servidor MCP

```powershell
python -m legal_rag serve --host 127.0.0.1 --port 8001
```

Endpoint Streamable HTTP: `http://127.0.0.1:8001/mcp`.

Contrato da ferramenta:

```text
search_legal_sources(query, strategy=null, top_k=null)
```

- `strategy`: `auto`, `bm25`, `dense` ou `hybrid`; `null` equivale a `auto`;
- `top_k`: de 1 a 10; `null` equivale a 5;
- `auto`: prefere a busca híbrida quando todos os recursos estão prontos e usa BM25
  como fallback explícito;
- a resposta registra estratégia solicitada e efetiva, motivo de fallback, versão do
  corpus e metadados das fontes.

## Administração e avaliação

```powershell
python -m legal_rag ingest --download
python -m legal_rag index --strategy bm25
python -m legal_rag index --strategy dense --model e5-small
python -m legal_rag evaluate --recuperador lexical --incluir-rascunho
```

O corpus e os materiais de avaliação permanecem versionáveis; `indice/` é reconstruível
e ignorado pelo Git. O gabarito ainda requer revisão jurídica especializada. A interface
de auditoria do gabarito continua disponível em `editor/` como ferramenta administrativa,
nunca como ferramenta MCP.

## Testes

```powershell
python -m pytest -q tests test_rag.py
```

Os testes cobrem BM25, argumentos omitidos ou `null`, fallback, erros de índices e o
contrato FastMCP em memória.
