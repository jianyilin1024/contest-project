#!/usr/bin/env bash
# 服务器初始化脚本（Ubuntu 22.04 / 24.04）
# 用法：在阿里云控制台以 root 登录后执行
#   bash init-server.sh
set -euo pipefail

echo "==> 1/6 更新系统并安装基础工具"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg git ufw fail2ban

echo "==> 2/6 安装 Docker 与 Compose 插件"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> 3/6 配置时区与 Docker 日志上限"
timedatectl set-timezone Asia/Shanghai
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" },
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
systemctl restart docker

echo "==> 4/6 创建部署用户"
if ! id -u deploy >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" deploy
  usermod -aG docker deploy
  mkdir -p /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
  chown -R deploy:deploy /home/deploy/.ssh
fi

echo "==> 5/6 配置防火墙（仅放行 SSH / HTTP / HTTPS）"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> 6/6 配置 2G swap（小内存机器必需）"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo
echo "初始化完成。请把 deploy 用户的公钥写入 /home/deploy/.ssh/authorized_keys，"
echo "然后把代码克隆到 /home/deploy/contest-project 后执行 deploy.sh。"
