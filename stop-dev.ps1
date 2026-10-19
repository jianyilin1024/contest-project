# 停止本地开发环境
# 用法：在仓库根目录执行  .\stop-dev.ps1

$root = $PSScriptRoot

Write-Host "==> 停止占用 3000 / 8000 端口的进程" -ForegroundColor Cyan
foreach ($port in 3000, 8000) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Host "已停止端口 $port 上的进程 PID $($c.OwningProcess)"
        } catch {
            Write-Host "无法停止端口 $port 的进程：$($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host "==> 停止数据库与 Redis" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f "$root\docker-compose.yml" down
} else {
    Write-Host "未检测到 Docker，跳过。"
}

Write-Host "已停止。" -ForegroundColor Green
