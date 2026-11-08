"""Compara recuperadores avaliados na mesma prova (mesmo corpus e mesmo gabarito).

Uso (na raiz deste repositório):
    .venv/Scripts/python comparar.py 68fa3d5ea28f-7e4ef9e1910b
    .venv/Scripts/python comparar.py 68fa3d5ea28f-7e4ef9e1910b --metrica acerto@1 --por-trecho

Lê avaliacao/resultados/<recuperador>-<corpus>-<gabarito>.json e, para cada recuperador,
mostra a média da métrica com intervalo de confiança de 95% e a diferença em relação ao
melhor, também com intervalo. Os intervalos vêm de bootstrap pareado: as perguntas são
sorteadas com reposição e todos os recuperadores são medidos nas mesmas perguntas.

Se o intervalo da diferença inclui zero, a diferença não é conclusiva com esse gabarito.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

RESULTADOS = Path(__file__).resolve().parent / "avaliacao" / "resultados"


def carregar(prova, metrica, por_trecho):
    """Recuperador -> {id da pergunta: valor da métrica}."""
    tabela = {}
    for arquivo in sorted(RESULTADOS.glob(f"*-{prova}.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        valores = {}
        for p in dados["perguntas"]:
            fonte = p.get("metricas_trecho") if por_trecho else p
            if fonte is not None:
                valores[p["id"]] = fonte[metrica]
        tabela[dados["recuperador"]] = valores
    return tabela


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prova", help="<corpus>-<gabarito>, como no nome dos arquivos de resultado")
    parser.add_argument("--metrica", default="MRR")
    parser.add_argument("--por-trecho", action="store_true")
    parser.add_argument("--reamostragens", type=int, default=10000)
    args = parser.parse_args()

    tabela = carregar(args.prova, args.metrica, args.por_trecho)
    if len(tabela) < 2:
        sys.exit(f"Preciso de pelo menos 2 recuperadores avaliados na prova {args.prova}.")
    # só perguntas medidas por todos, para a comparação ser pareada
    ids = sorted(set.intersection(*(set(v) for v in tabela.values())))
    nomes = sorted(tabela, key=lambda n: -np.mean([tabela[n][i] for i in ids]))
    m = np.array([[tabela[n][i] for i in ids] for n in nomes])  # recuperador x pergunta

    rng = np.random.default_rng(42)
    amostras = rng.integers(0, len(ids), size=(args.reamostragens, len(ids)))
    medias = m[:, amostras].mean(axis=2)  # recuperador x reamostragem
    melhor = medias[0]

    print(f"Prova {args.prova} · {args.metrica}{' por trecho' if args.por_trecho else ''} · "
          f"{len(ids)} perguntas · IC 95% por bootstrap pareado\n")
    print(f"{'recuperador':20}{'média':>8}{'IC 95%':>18}{'dif. p/ o 1º':>14}{'IC 95% da dif.':>20}")
    for k, nome in enumerate(nomes):
        lo, hi = np.percentile(medias[k], [2.5, 97.5])
        linha = f"{nome:20}{m[k].mean():8.3f}{f'[{lo:.3f}, {hi:.3f}]':>18}"
        if k:
            dif = medias[k] - melhor
            dlo, dhi = np.percentile(dif, [2.5, 97.5])
            conclusivo = "" if dlo <= 0 <= dhi else " *"
            linha += f"{m[k].mean() - m[0].mean():14.3f}{f'[{dlo:.3f}, {dhi:.3f}]':>20}{conclusivo}"
        print(linha)
    print("\n* diferença conclusiva: o intervalo não inclui zero")


if __name__ == "__main__":
    main()
