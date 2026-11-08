# RAG jurídico local

Esta pasta contém o corpus jurídico, a ingestão, as três buscas e o editor de
validação. Ela é instalada dentro do processo do agente: não expõe servidor HTTP
nem ferramenta MCP própria.

O corpus atual tem 101 trechos. `avaliacao/gabarito.yaml` é a única fonte de
perguntas de avaliação; não misture cópias antigas dele.

## Comandos administrativos

```powershell
python -m pip install -e ".[dense,dev]"
python busca_lexical.py --indexar
python busca_densa.py --indexar --modelo e5-small
python avaliar.py --recuperador hibrida-e5-small --incluir-rascunho
python editor/servidor.py
```

`busca_lexical.py`, `busca_densa.py` e `comparar.py` mantêm o estilo simples do
protótipo original. Os índices em `indice/` são derivados e podem ser apagados e
reconstruídos.

## Anotações de recuperação

`corpus/retrieval-metadata.v1.json` complementa cada trecho jurídico com:

- `expressions`: palavras, expressões e formulações leigas, com peso adicional no
  BM25;
- `dense_descriptions`: uma a três descrições temáticas do mesmo trecho. Cada uma
  recebe vetor próprio; os resultados são agrupados novamente por `chunk_id`.

Esses campos não são fontes jurídicas e não aparecem como tal à usuária. Edite-os na
aba **Anotações de recuperação** do editor. O editor valida cobertura, campos vazios,
duplicatas, temas repetidos e o limite de descrições; ele cria um backup antes de
salvar, mas não reindexa automaticamente.

## Uso pelo backend

`rag_tool.LegalSearchTool` adapta as buscas para a ferramenta local
`legal_search_legal_sources(query, strategy, top_k)`. `auto` usa híbrida quando o
índice denso está pronto e BM25 como fallback. O backend mantém citações e fontes
transitórias como antes, mas não precisa mais de um serviço HTTP intermediário.
