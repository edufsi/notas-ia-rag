FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY legal_rag ./legal_rag
COPY ingestao.py avaliar.py fontes.yaml ./
COPY corpus ./corpus
COPY dados ./dados
COPY avaliacao ./avaliacao
RUN python -m pip install .

EXPOSE 8001

CMD ["python", "-m", "legal_rag", "serve", "--host", "0.0.0.0", "--port", "8001"]
