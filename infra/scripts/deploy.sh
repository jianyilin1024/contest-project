#!/usr/bin/env bash
# 服务器端部署脚本：拉取最新代码并重建容器
# 用法：bash infra/scripts/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"

cd "$APP_DIR"

echo "==> 当前目录: $APP_DIR"
if [ ! -f "$ENV_FILE" ]; then
  echo "错误：找不到 $ENV_FILE，请先从 .env.example 复制并填写" >&2
  exit 1
fi

echo "==> 拉取最新代码"
git pull --ff-only

echo "==> 构建镜像"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

echo "==> 滚动重启"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans

echo "==> 清理旧镜像"
docker image prune -f

echo "==> 等待健康检查"
sleep 8
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo "部署完成。查看日志：docker compose -f $COMPOSE_FILE logs -f api"
