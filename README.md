# notas-ia-rag

RAG jurídico do [Notas.ia](https://github.com/aline-fraga/notas-ia): recupera trechos de
leis oficiais para responder dúvidas com citação. No repositório principal, este
repositório fica na pasta `rag/` como submodule.

Desenho da solução em
[`arquitetura-chat-codex-eduardo-f/resposta-rag.md`](https://github.com/aline-fraga/notas-ia/blob/main/arquitetura-chat-codex-eduardo-f/resposta-rag.md)
(SQLite FTS5 + FAISS + RRF).

## Como rodar

Na raiz deste repositório (ou em `notas-ia/rag/`). No Windows; em Linux/Mac troque
`Scripts` por `bin`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python ingestao.py              # gera o corpus a partir de fontes.yaml
.venv/Scripts/python busca_lexical.py --indexar
.venv/Scripts/python busca_densa.py --indexar --modelo e5-small   # baixa o modelo na 1ª vez
.venv/Scripts/python busca_densa.py "meu ex fica me seguindo" --hibrida
.venv/Scripts/python avaliar.py --recuperador hibrida-e5-small --incluir-rascunho
```

O índice denso precisa ser refeito sempre que o corpus mudar (o script avisa).

## Arquivos

| Arquivo | O que é |
|---|---|
| `fontes.yaml` | Lista das fontes oficiais. Só entra no corpus o que estiver aqui |
| `ingestao.py` | Baixa as páginas do Planalto e divide em trechos por artigo |
| `dados/brutos/` | Páginas originais, como vieram do site (para reproduzir o corpus) |
| `corpus/trechos.jsonl` | Um trecho por linha, com texto e metadados |
| `corpus/manifesto.json` | Versão do corpus (hash), data e contagem por fonte |
| `busca_lexical.py` | Busca BM25 com SQLite FTS5 (linha de base) |
| `busca_densa.py` | Busca densa (embeddings + FAISS) e híbrida (BM25 + densa por RRF) |
| `avaliacao/gabarito.yaml` | Perguntas leigas com os artigos que as respondem |
| `avaliar.py` | Mede acerto@k, recall@k, MRR e nDCG@10 contra o gabarito |
| `avaliacao/resultados/` | Resultado de cada avaliação, por recuperador e versão do corpus |
| `editor/` | Aplicação local para escrever e revisar o gabarito ([como usar](editor/README.md)) |

## Gabarito

O gabarito é a referência para comparar as buscas, então precisa ser feito por pessoas:

O jeito mais fácil é pelo **editor do gabarito**: `python editor/servidor.py` (ver
[editor/README.md](editor/README.md)). O processo:

1. Escrever a pergunta como uma usuária escreveria e indicar o `tipo`.
2. Apontar os artigos que respondem (`relevantes`) e os que ajudam (`parciais`).
   Quando um artigo tiver sido dividido em partes, abrir "Partes exatas de artigos
   divididos" e indicar quais trechos realmente contêm a resposta.
3. Duas pessoas conferem, sem ver a resposta uma da outra; divergências são discutidas.
4. Só então o `status` vira `revisado`. Por padrão, o `avaliar.py` usa só os revisados.

O gabarito tem agora 77 perguntas em **rascunho**: 31 iniciais, escritas com auxílio de
IA, e 46 escritas pelo grupo a partir de temas da legislação. Quem escreve uma pergunta
não é revisor dela. Meta: 150 a 300.

## Resultados (provisórios)

### Estado do teste

| | |
|---|---|
| Data | 04/11/2026 |
| Corpus | versão `68fa3d5ea28f`: 96 trechos (93 de legislação + 3 de jurisprudência), 9 fontes |
| Gabarito | versão `ce98fa8bdb91`: 77 perguntas, **todas em rascunho** (0 revisadas) |
| Perguntas usadas | 66 com resposta (37 coloquiais, 15 diretas, 14 adversas) e 11 sem resposta |
| Comando | `avaliar.py --incluir-rascunho --recuperador <nome>` |
| Arquivos | `avaliacao/resultados/<recuperador>-68fa3d5ea28f-ce98fa8bdb91.json` |

As versões são hashes do conteúdo (`corpus/manifesto.json` e `avaliacao/gabarito.yaml`):
qualquer mudança no corpus ou no gabarito gera outra versão, e o `avaliar.py` grava cada
resultado num arquivo próprio. Com o gabarito ainda sem revisão, os números servem para
comparar as buscas entre si, não como medida final. Com 66 perguntas, cada uma vale
~1,5 ponto no acerto.

### Avaliação por artigo (66 perguntas)

| Recuperador | acerto@1 | acerto@3 | acerto@5 | MRR | nDCG@10 |
|---|---|---|---|---|---|
| BM25 (`lexical`) | 0,44 | 0,53 | 0,68 | 0,53 | 0,56 |
| Densa e5-small | 0,45 | 0,68 | 0,79 | 0,59 | 0,64 |
| Híbrida e5-small | 0,45 | 0,71 | 0,79 | 0,59 | 0,63 |
| Densa e5-base | 0,45 | 0,62 | 0,82 | 0,59 | 0,64 |
| Híbrida e5-base | 0,45 | 0,71 | 0,79 | 0,60 | 0,65 |
| **Densa BGE-M3** | **0,59** | **0,76** | **0,83** | **0,70** | **0,72** |
| Híbrida BGE-M3 | 0,48 | 0,73 | 0,79 | 0,63 | 0,66 |

Na avaliação por trecho (58 perguntas; 8 aguardam a indicação da parte em artigos
divididos), a ordem é a mesma: BGE-M3 densa com acerto@1 0,60 e MRR 0,70; BM25 com
0,47 e 0,55.

- A **BGE-M3 densa** continua a melhor em todas as métricas.
- Somar a BM25 à BGE-M3 (híbrida) **piora** o resultado; com a e5, a híbrida ajuda pouco.
- O ganho maior da busca densa está nas perguntas **diretas** (BGE-M3: acerto@1 0,87,
  contra 0,60 da BM25) e **coloquiais** (0,51 contra 0,35).
- **Nenhum recuperador separa as perguntas sem resposta**: o escore do 1º resultado
  delas fica na mesma faixa das perguntas com resposta. A recusa vai precisar de outro
  sinal (reranqueador ou verificação pela LLM), não de um limiar no escore da busca.

Resultados de testes anteriores (outros corpus e gabaritos) continuam em
`avaliacao/resultados/`, com a versão no nome do arquivo, mas não são comparáveis com esta
tabela.

O avaliador preserva as métricas por artigo e também calcula métricas por trecho. Para
artigos não divididos, o rótulo é automático. Artigos divididos exigem os campos
`trechos_relevantes`/`trechos_parciais`; enquanto faltarem, o relatório informa a
cobertura e não inventa qual parte seria correta.

## Decisões da ingestão

- **Um trecho por artigo**, com caput, incisos, parágrafos e penas. Artigos com mais de
  2.500 caracteres são divididos em partes que repetem o caput.
- **Texto revogado é descartado.** O Planalto mantém a redação antiga riscada
  (`<strike>` ou `line-through`); ela nunca entra no corpus.
- **Anotações de alteração** ("Incluído pela Lei nº ...") saem do texto e vão para o
  campo `alterado_por`.
- **Leis que só alteram outras leis** não entram: o texto já está na versão compilada.
- **Rubricas** do Código Penal ("Calúnia", "Lesão corporal") ficam no início do trecho,
  porque ajudam a busca.
- **Jurisprudência curta** pode ser extraída de páginas oficiais por uma frase distintiva
  declarada em `fontes.yaml`. A ingestão guarda o menor bloco que contém a frase e falha
  explicitamente se a página mudar, em vez de inserir silenciosamente outro conteúdo.

## Limitações conhecidas

- O corpus ainda não foi revisado por alguém da área jurídica.
- A busca lexical não liga linguagem coloquial à linguagem da lei ("fica me seguindo"
  não encontra "perseguição"). É o que a busca densa deve resolver.
- Ainda não há notas em linguagem simples nem cartilhas (só texto de lei).
