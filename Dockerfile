FROM python:3.13-slim

WORKDIR /srv

# libgomp1 -- OpenMP runtime torch/sentence-transformers need at import time;
# missing on the plain slim image and easy to miss since it only fails once
# a model actually loads, not at pip install time.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# The pip that ships in python:3.13-slim resolves rpds-py (a chromadb/
# jsonschema transitive dep) badly for this Python version -- it reports a
# ResolutionImpossible conflict that a current pip resolves fine.
#
# torch is installed separately, from PyTorch's CPU-only wheel index, before
# the rest of requirements.txt. Everything in this project runs CPU
# inference (embeddings, reranker -- Ollama and the API LLMs run as separate
# services/processes entirely). A plain `pip install torch` on Linux pulls
# in several GB of nvidia-* CUDA library wheels as declared dependencies of
# the default PyPI wheel, none of which this image ever uses -- installing
# the CPU build here first means pip sees torch already satisfied when it
# hits llama-index/sentence-transformers' torch requirement later, instead
# of resolving to the CUDA-bundled default.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
