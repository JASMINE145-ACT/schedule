# 启动前端 V2 服务

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "启动 Travel Planner Frontend V2" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 切换到前端目录
$frontendDir = Split-Path -Parent $MyInvocation.MyCommand.Path | Join-Path -ChildPath "frontend"
Set-Location $frontendDir

Write-Host "📍 前端地址: http://localhost:8501" -ForegroundColor Cyan
Write-Host "🤖 智能对话式旅行规划界面" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 启动服务
python start_frontend_v2.py
