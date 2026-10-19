# 一键启动本地开发环境（数据库 + 后端 + 前端）
# 用法：在仓库根目录执行  .\start-dev.ps1
# 停止：.\stop-dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "==> 检查运行环境" -ForegroundColor Cyan

$apiPython = Join-Path $root "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $apiPython)) {
    Write-Host "后端依赖未安装。请先执行：" -ForegroundColor Yellow
    Write-Host "  cd apps\api; python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt"
    exit 1
}
if (-not (Test-Path (Join-Path $root "apps\web\node_modules"))) {
    Write-Host "前端依赖未安装。请先执行：" -ForegroundColor Yellow
    Write-Host "  cd apps\web; pnpm install"
    exit 1
}

Write-Host "==> 启动数据库与 Redis" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f "$root\docker-compose.yml" up -d
} else {
    Write-Host "未检测到 Docker，跳过数据库。页面仍可打开，仅 AI/数据功能不可用。" -ForegroundColor Yellow
}

Write-Host "==> 启动后端 http://localhost:8000" -ForegroundColor Cyan
Start-Process powershell -WorkingDirectory "$root\apps\api" `
    -ArgumentList "-NoExit", "-Command", "& '$apiPython' -m uvicorn app.main:app --reload --port 8000"

Write-Host "==> 启动前端 http://localhost:3000" -ForegroundColor Cyan
Start-Process powershell -WorkingDirectory "$root\apps\web" `
    -ArgumentList "-NoExit", "-Command", "pnpm dev"

Write-Host "==> 等待服务就绪..." -ForegroundColor Cyan
Start-Sleep -Seconds 12

$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:3000" -TimeoutSec 5 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}

if ($ok) {
    Write-Host "页面已就绪：http://localhost:3000" -ForegroundColor Green
    Start-Process "http://localhost:3000"
} else {
    Write-Host "前端启动较慢或失败，请查看弹出的前端窗口日志。" -ForegroundColor Yellow
    Write-Host "手动访问：http://localhost:3000"
}
