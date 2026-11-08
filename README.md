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
| `comparar.py` | Compara recuperadores de uma mesma prova, com intervalos de confiança |
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
| Data | 07/11/2026 |
| Corpus | versão `174e8766c4b2`: 101 trechos (98 de legislação + 3 de jurisprudência), 9 fontes; art. 7º da LMP dividido por inciso |
| Gabarito | versão `cb7a8926414d`: 166 perguntas, 31 revisadas e 135 em rascunho |
| Perguntas usadas | 143 com resposta (78 coloquiais, 33 adversas, 32 diretas) e 23 sem resposta |
| Comandos | `avaliar.py --incluir-rascunho --recuperador <nome>` e `comparar.py 174e8766c4b2-cb7a8926414d` |
| Arquivos | `avaliacao/resultados/<recuperador>-174e8766c4b2-cb7a8926414d.json` |

As versões são hashes do conteúdo (`corpus/manifesto.json` e `avaliacao/gabarito.yaml`):
qualquer mudança gera outra versão, e cada resultado fica num arquivo próprio. Como a maior
parte do gabarito ainda não foi revisada, os números servem para comparar as buscas entre
si, não como medida final.

### Avaliação por artigo (143 perguntas)

As partes de um artigo dividido (`-p1`, `-p2`...) contam como um só artigo. Em negrito, o
melhor valor de cada coluna.

| Recuperador | acerto@1 | acerto@3 | acerto@5 | acerto@10 | recall@5 | recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|---|---|---|---|
| BM25 (`lexical`) | 0,36 | 0,52 | 0,59 | 0,69 | 0,52 | 0,63 | 0,46 | 0,47 |
| Densa e5-small | 0,38 | 0,55 | 0,63 | 0,76 | 0,55 | 0,67 | 0,49 | 0,50 |
| Híbrida e5-small | 0,39 | 0,62 | 0,69 | 0,81 | 0,59 | 0,73 | 0,52 | 0,53 |
| Densa e5-base | 0,41 | 0,64 | 0,79 | 0,88 | 0,67 | 0,79 | 0,56 | 0,58 |
| Híbrida e5-base | 0,45 | 0,69 | **0,82** | 0,89 | 0,69 | 0,79 | 0,60 | 0,61 |
| Densa BGE-M3 | **0,51** | **0,72** | 0,81 | **0,90** | **0,71** | **0,81** | **0,64** | **0,64** |
| Híbrida BGE-M3 | 0,50 | 0,66 | 0,78 | **0,90** | 0,67 | **0,81** | 0,62 | 0,63 |

Por tipo de pergunta (acerto@1, BGE-M3 densa × BM25): diretas 0,72 × 0,62, coloquiais
0,49 × 0,27, adversas 0,36 × 0,30.

### Avaliação por trecho (143 perguntas)

Cada parte de um artigo dividido conta separadamente: trazer o `art22-p2` quando a
resposta está no `art22-p1`, ou o inciso de violência física quando a pergunta é sobre
violência patrimonial, não é acerto. É a medida mais próxima do que a LLM vai ler. Todas
as 143 perguntas têm a parte certa indicada no gabarito.

| Recuperador | acerto@1 | acerto@3 | acerto@5 | acerto@10 | recall@5 | recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|---|---|---|---|
| BM25 (`lexical`) | 0,36 | 0,52 | 0,58 | 0,66 | 0,50 | 0,59 | 0,45 | 0,46 |
| Densa e5-small | 0,38 | 0,52 | 0,61 | 0,72 | 0,50 | 0,63 | 0,47 | 0,47 |
| Híbrida e5-small | 0,38 | 0,59 | 0,67 | 0,78 | 0,57 | 0,67 | 0,50 | 0,50 |
| Densa e5-base | 0,40 | 0,60 | 0,71 | 0,86 | 0,60 | 0,75 | 0,54 | 0,55 |
| Híbrida e5-base | 0,45 | 0,66 | 0,77 | 0,86 | 0,63 | 0,75 | 0,58 | 0,58 |
| Densa BGE-M3 | **0,50** | **0,71** | **0,80** | **0,88** | **0,69** | **0,78** | **0,63** | **0,61** |
| Híbrida BGE-M3 | **0,50** | 0,65 | 0,76 | 0,87 | 0,64 | 0,76 | 0,61 | 0,60 |

### O que é conclusivo

`comparar.py` calcula intervalos de confiança de 95% por bootstrap pareado (as mesmas
perguntas sorteadas para todos os recuperadores). No MRR por artigo:

| Recuperador | MRR | Diferença para a BGE-M3 densa | Conclusiva? |
|---|---|---|---|
| Densa BGE-M3 | 0,64 [0,57; 0,70] | — | — |
| Híbrida BGE-M3 | 0,62 | −0,02 [−0,07; +0,04] | Não |
| Híbrida e5-base | 0,60 | −0,03 [−0,10; +0,03] | Não |
| Densa e5-base | 0,56 | −0,07 [−0,14; −0,01] | Sim |
| Híbrida e5-small | 0,52 | −0,12 [−0,18; −0,05] | Sim |
| Densa e5-small | 0,49 | −0,15 [−0,22; −0,08] | Sim |
| BM25 | 0,46 | −0,18 [−0,25; −0,11] | Sim |

- A **BGE-M3** densa é melhor que a BM25 e que as e5 densas e a híbrida e5-small, com
  diferença conclusiva. Ela, a BGE-M3 híbrida e a híbrida e5-base ficam empatadas dentro
  do intervalo.
- **Dividir o art. 7º por inciso foi neutro.** Por artigo, a BGE-M3 densa subiu 0,01 no
  acerto@5 e no MRR (não conclusivo); por trecho, ficou igual, mesmo com a tarefa mais
  difícil (agora precisa vir o inciso certo). As e5 pioraram um pouco por trecho.
- **A recusa não sai do escore da busca.** Com o melhor limiar possível, a BGE-M3 densa
  recusa só 3 das 23 perguntas sem resposta (sem recusar nenhuma com resposta); os outros
  recuperadores, nenhuma. A recusa precisa de outro sinal (reranqueador ou verificação
  pela LLM).

### Análise de erros (BGE-M3 densa, corpus `68fa3d5ea28f`)

Antes da divisão do art. 7º, a BGE-M3 densa não trazia nenhum artigo relevante nos 5
primeiros em 28 das 143 perguntas. Os erros se concentram em três causas:

- **Vocabulário diferente do da lei.** A pergunta diz "cadeia", "papel do hospital",
  "pegou meu celular"; a lei diz "prisão", "prontuário", "retenção de objetos". É o caso
  do art. 7º, relevante em 35 perguntas e presente nos 5 primeiros em só 4 (8 depois da
  divisão por inciso), e de perguntas sobre os arts. 9, 10-A e 21.
- **Artigos "ímã".** Os arts. 12-C e 12-D começam com uma frase genérica ("risco atual ou
  iminente à vida ou à integridade física, sexual, psicológica, moral ou patrimonial da
  mulher"). O 12-C aparece nos 5 primeiros de 68 das 143 perguntas e é relevante em 3; o
  12-D, em 45, e não é relevante em nenhuma. Há efeito parecido entre crimes vizinhos
  (estupro no lugar de cárcere privado, lesão corporal no lugar de importunação sexual).
- **Gabarito.** Poucos casos: uma pergunta sem texto (q132) e algumas com rótulos
  provavelmente incompletos (q094, q123, q141).

Em 23 das 28 falhas o artigo certo está entre os 30 primeiros candidatos, ao alcance de
um reranqueador. Próximos passos: palavras-chave por trecho (em andamento no grupo) e
reranqueador.

Resultados de testes anteriores (outros corpus e gabaritos) continuam em
`avaliacao/resultados/`, com a versão no nome do arquivo, mas não são comparáveis com estas
tabelas.

## Decisões da ingestão

- **Um trecho por artigo**, com caput, incisos, parágrafos e penas. Artigos com mais de
  2.500 caracteres são divididos em partes que repetem o caput.
- **Um trecho por inciso** nos artigos listados em `dividir_por_inciso` (`fontes.yaml`).
  Hoje só o art. 7º da Lei Maria da Penha: cada parte (`art7-p1` a `art7-p6`) traz o caput
  e uma forma de violência (física, psicológica, sexual, patrimonial, moral, vicária), as
  mesmas categorias do classificador. Inteiro, o art. 7º misturava as seis e quase nunca
  era recuperado.
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
