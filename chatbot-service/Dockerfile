FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system chatbot \
    && useradd --system --gid chatbot --create-home chatbot

# Install the resolved runtime closure before copying local source.
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# The application modules are imported directly from WORKDIR.
COPY . .

# Named volumes inherit these writable directory permissions on first use.
RUN mkdir -p /app/data /app/logs \
    && chown -R chatbot:chatbot /app

EXPOSE 8000

USER chatbot

CMD ["uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
