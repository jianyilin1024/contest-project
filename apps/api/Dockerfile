# 后端镜像：多阶段构建。
#
# 设计取舍：
# - 依赖全部有 manylinux wheel，因此**不需要**编译器（省掉 build-essential 的 200MB
#   下载和约 1GB 的构建内存峰值，小内存服务器上不会再被 OOM 杀掉）；
# - 健康检查用 Python 自带 urllib，不额外安装 curl，运行时阶段完全不需要 apt；
# - PIP_INDEX_URL 可通过构建参数覆盖，国内服务器用阿里云源会快很多。

FROM python:3.11-slim AS builder

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --index-url "$PIP_INDEX_URL" -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
