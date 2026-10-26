# 推送 astrbot_plugin_group_chat_switch 到你自己的 GitHub 仓库
# 用法（在本目录打开 PowerShell）：
#     .\push_to_github.ps1 -GitHubUser 你的GitHub登录名
# 说明：
#   - 令牌用 Read-Host 读取，只存在本次会话的变量里，不落盘、不回显、不写进 .git/config
#   - 推完自动把 remote 还原成不含令牌的地址
#   - 令牌在 GitHub → Settings → Developer settings → Personal access tokens
#     新建 classic token，勾 repo 权限即可；用完建议立刻撤销

param(
    [Parameter(Mandatory = $true)]
    [string]$GitHubUser,

    [string]$RepoName = "astrbot_plugin_group_chat_switch"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "[1/5] 改写 metadata.yaml 里的占位作者与仓库地址" -ForegroundColor Cyan
$metaPath = Join-Path $here "metadata.yaml"
$meta = [IO.File]::ReadAllText($metaPath, [Text.Encoding]::UTF8)
if ($meta.Contains("your-github-name")) {
    $meta = $meta -replace 'your-github-name', $GitHubUser
    # 无 BOM 写回：PowerShell 5.1 的 Set-Content -Encoding UTF8 会加 BOM，YAML 会脏
    [IO.File]::WriteAllText($metaPath, $meta, (New-Object Text.UTF8Encoding($false)))
    Write-Host "  已写入作者 $GitHubUser" -ForegroundColor Green
} else {
    Write-Host "  占位已填好，跳过" -ForegroundColor DarkGray
}

Write-Host "[2/5] 提交改动" -ForegroundColor Cyan
git add -A
git -c user.name=$GitHubUser -c user.email="$GitHubUser@users.noreply.github.com" commit -m "chore: 填写作者与仓库地址" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "  没有新改动，跳过" -ForegroundColor DarkGray }

Write-Host "[3/5] 读取令牌（不会回显）" -ForegroundColor Cyan
$secure = Read-Host "粘贴你的 GitHub PAT" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

Write-Host "[4/5] 在 GitHub 上创建仓库（已存在则跳过）" -ForegroundColor Cyan
$headers = @{
    Authorization          = "Bearer $token"
    Accept                 = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}
$body = @{
    name        = $RepoName
    description = "用聊天指令按群开启/关闭 AI 聊天"
    private     = $false
} | ConvertTo-Json -Compress
try {
    Invoke-RestMethod -Method Post -Uri "https://api.github.com/user/repos" -Headers $headers -Body $body | Out-Null
    Write-Host "  已创建" -ForegroundColor Green
} catch {
    Write-Host "  创建失败或已存在：$($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "[5/5] 推送代码" -ForegroundColor Cyan
$cleanUrl = "https://github.com/$GitHubUser/$RepoName.git"
$authedUrl = "https://$GitHubUser`:$token@github.com/$GitHubUser/$RepoName.git"

git remote remove origin 2>$null
git remote add origin $cleanUrl
git push $authedUrl "HEAD:master" --force
if ($LASTEXITCODE -eq 0) {
    git remote set-url origin $cleanUrl
    Write-Host "  推送完成：$cleanUrl" -ForegroundColor Green
    Write-Host "  下一步：打开 https://cloud.astrbot.app/publish 提交这个仓库地址" -ForegroundColor Green
} else {
    Write-Host "  推送失败，检查仓库名、分支或令牌权限" -ForegroundColor Red
}

$token = $null
Remove-Variable token -ErrorAction SilentlyContinue
