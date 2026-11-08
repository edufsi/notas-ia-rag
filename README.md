# notas-ia-rag

RAG jurídico do [Notas.IA](https://github.com/aline-fraga/notas-ia): recupera trechos
de fontes oficiais para fundamentar respostas com citação. No repositório principal,
fica em `services/legal-mcp/` como submódulo. Apesar do nome histórico, esta versão não
expõe um servidor MCP próprio: o backend usa a biblioteca local como a ferramenta
`legal_search_legal_sources`.

O desenho de recuperação mantém SQLite FTS5 (BM25), FAISS (busca densa) e RRF (busca
híbrida). A avaliação abaixo mede **a recuperação direta**, não a qualidade da conversa
ou da resposta final da LLM.

## Como rodar

Na raiz deste repositório. No Windows; em Linux/macOS troque `Scripts` por `bin`.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python ingestao.py
.venv/Scripts/python busca_lexical.py --indexar
.venv/Scripts/python busca_densa.py --indexar --modelo e5-small
.venv/Scripts/python busca_densa.py "meu ex fica me seguindo" --hibrida
.venv/Scripts/python avaliar.py --recuperador hibrida-e5-small --incluir-rascunho
```

Para PyTorch apenas em CPU, instale-o antes com:

```powershell
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Índices precisam ser refeitos quando o corpus ou as anotações de recuperação mudam. Os
scripts detectam essa incompatibilidade. No Compose principal, o agente faz essa
verificação antes de iniciar a API.

## Arquivos

| Arquivo | O que é |
|---|---|
| `fontes.yaml` | Lista de fontes oficiais permitidas no corpus |
| `ingestao.py` | Baixa páginas e divide o conteúdo em trechos |
| `dados/brutos/` | Páginas originais para reproduzir o corpus |
| `corpus/trechos.jsonl` | Um trecho jurídico por linha, com metadados |
| `corpus/manifesto.json` | Hash, data e contagem da versão do corpus |
| `corpus/retrieval-metadata.v1.json` | Expressões e descrições usadas somente para recuperação |
| `busca_lexical.py` | BM25 com SQLite FTS5 |
| `busca_densa.py` | Busca densa FAISS e híbrida por RRF |
| `avaliacao/gabarito.yaml` | Perguntas e fontes esperadas para avaliação |
| `avaliar.py` | Mede acerto@k, recall@k, MRR e nDCG@10 |
| `comparar.py` | Compara recuperadores com bootstrap pareado |
| `avaliacao/resultados/` | Resultados versionados de cada execução |
| `editor/` | Editor local do gabarito e das anotações de recuperação |

## Gabarito e revisão humana

O gabarito é a referência da avaliação, portanto deve ser curado por pessoas. Abra o
editor com `python editor/servidor.py` e siga este fluxo:

1. Escreva a pergunta como uma usuária a escreveria, antes de procurar a fonte.
2. Marque trechos `relevantes` e `parciais`; para artigos divididos, indique a parte
   que de fato responde.
3. Duas pessoas revisam o item e discutem divergências.
4. Só então o status passa a `revisado`; por padrão, a avaliação usa apenas revisados.

O arquivo atual possui 165 perguntas: 31 revisadas e 134 em rascunho. Resultados que
incluem rascunhos são úteis para comparar métodos, mas não constituem validação final.

## Anotações de recuperação

Cada trecho recebe anotações curadas em `retrieval-metadata.v1.json`:

- `expressions`: palavras, expressões e formulações leigas com peso adicional no BM25;
- `dense_descriptions`: uma a três descrições temáticas distintas. Cada descrição recebe
  um vetor, e resultados do mesmo trecho são agrupados antes de retornar à LLM.

Essas anotações não são fontes jurídicas, nem autorizam conclusões. A aba
**Anotações de recuperação** do editor valida cobertura, campos vazios, duplicatas,
temas repetidos e o limite de três descrições; ela cria backup, mas não reindexa.

## Resultados provisórios

O corpus atual tem 101 trechos e nove fontes. O art. 7º da Lei Maria da Penha é dividido
por inciso para separar formas de violência. Os resultados completos, identificados pelo
hash de corpus e gabarito, ficam em `avaliacao/resultados/`.

Na rodada documentada com 143 perguntas respondíveis, busca densa BGE-M3 e híbrida
e5-base/BGE-M3 superaram a BM25 em MRR; a diferença da BGE-M3 densa para BM25 foi
conclusiva no bootstrap pareado. Isso não elimina a utilidade da BM25: ela é a linha de
base reproduzível e o fallback quando não há índice denso.

Os principais erros observados são vocabulário leigo diferente do texto legal, artigos
genéricos que atraem resultados demais e lacunas no gabarito. As expressões e descrições
temáticas foram adicionadas justamente como um reforço controlado para esses casos.

## Decisões e limites

- O corpus contém textos oficiais e metadados de procedência; não declara que um trecho
  resolve definitivamente uma situação individual.
- Texto revogado é descartado na ingestão; alterações legislativas são preservadas em
  metadados.
- O corpus, gabarito e anotações ainda precisam de revisão jurídica especializada.
- Não há ainda cartilhas em linguagem simples nem julgamento automático de suficiência da
  recuperação. A LLM deve citar apenas fontes que a ferramenta devolveu.
