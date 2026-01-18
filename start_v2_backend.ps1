# 启动后端 V2 服务

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "启动 Travel Planner Backend V2" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 切换到后端目录
$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path | Join-Path -ChildPath "backend"
Set-Location $backendDir

# 检查环境变量
$requiredVars = @("GOOGLE_MAPS_API_KEY", "ANTHROPIC_API_KEY")
$missingVars = @()

foreach ($var in $requiredVars) {
    if (-not $env:$var) {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "❌ 缺少必需的环境变量: $($missingVars -join ', ')" -ForegroundColor Red
    Write-Host "请在 .env 文件中设置这些变量" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 环境变量检查通过" -ForegroundColor Green
Write-Host ""
Write-Host "📍 后端地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📖 API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🔄 自动重载: 已启用" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 启动服务
python start_backend_v2.py
