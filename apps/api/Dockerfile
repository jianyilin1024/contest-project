# 后端镜像：多阶段构建，运行阶段不带编译工具链
#
# APT_MIRROR / PIP_INDEX_URL 可通过构建参数覆盖：国内服务器建议设为
#   APT_MIRROR=mirrors.aliyun.com  PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
# 默认值保持官方源，方便在境外环境构建。

FROM python:3.11-slim AS builder

ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

RUN sed -i "s|deb.debian.org|"$APT_MIRROR"|g" /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --index-url "$PIP_INDEX_URL" -r requirements.txt


FROM python:3.11-slim AS runtime

ARG APT_MIRROR=deb.debian.org

ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN sed -i "s|deb.debian.org|"$APT_MIRROR"|g" /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 3

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
