#!/usr/bin/env bash
# 服务器端部署脚本：优先用 CI 构建好的镜像，取不到再本地构建。
# 用法：bash infra/scripts/deploy.sh
#
# 2 核 2G 的机器建议：先在 GitHub Actions 跑好 Build Images，
# 并把 Packages 设为 public，这样服务器全程不需要构建。
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

COMPOSE="docker compose -f $COMPOSE_FILE --env-file $ENV_FILE"

echo "==> 拉取最新代码"
git pull --ff-only

echo "==> 尝试拉取预构建镜像"
if $COMPOSE pull --quiet 2>/dev/null; then
  echo "    已使用 CI 构建的镜像，跳过本地构建"
  UP_ARGS="--no-build"
else
  echo "    取不到预构建镜像（未登录 ghcr 或包为私有），改为本地构建"
  echo "    提示：2G 内存的机器首次构建较慢，请耐心等待"
  $COMPOSE build
  UP_ARGS=""
fi

echo "==> 滚动重启"
# shellcheck disable=SC2086
$COMPOSE up -d --remove-orphans $UP_ARGS

echo "==> 清理旧镜像"
docker image prune -f

echo "==> 等待健康检查"
sleep 10
$COMPOSE ps

echo
echo "部署完成。查看日志：$COMPOSE logs -f api"
