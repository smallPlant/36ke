# 构建时打包便携 Node.js + lark-cli 到 dist/36Ke/tools
param(
    [string]$Dest = ""
)

$ErrorActionPreference = "Stop"
$NodeVersion = "20.18.1"
$LarkVersion = "1.0.59"

if (-not $Dest) {
    $root = Split-Path $PSScriptRoot -Parent
    $Dest = Join-Path $root "dist\36Ke\tools"
}

$nodeDir = Join-Path $Dest "node"
$larkDir = Join-Path $Dest "lark-cli"
$npmPrefix = Join-Path $Dest "npm"

Write-Host "打包工具: Node.js v$NodeVersion + lark-cli v$LarkVersion -> $Dest"

if (Test-Path $Dest) {
    Remove-Item $Dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

function Download-FileWithRetry {
    param(
        [string[]]$Urls,
        [string]$OutFile,
        [int]$Retries = 3
    )
    foreach ($attempt in 1..$Retries) {
        foreach ($url in $Urls) {
            Write-Host "下载 ($attempt/$Retries): $url"
            try {
                Invoke-WebRequest -Uri $url -OutFile $OutFile -UseBasicParsing -TimeoutSec 180
                if ((Get-Item $OutFile).Length -gt 0) {
                    return
                }
            } catch {
                Write-Host "  失败: $_"
            }
        }
        Start-Sleep -Seconds 2
    }
    throw "下载失败: $OutFile"
}

# --- Node.js ---
$nodeZip = Join-Path $env:TEMP "node-v$NodeVersion-win-x64.zip"
$nodeUrls = @(
    "https://nodejs.org/dist/v$NodeVersion/node-v$NodeVersion-win-x64.zip"
)
Download-FileWithRetry -Urls $nodeUrls -OutFile $nodeZip

$extractRoot = Join-Path $env:TEMP "node-extract-$NodeVersion"
if (Test-Path $extractRoot) {
    Remove-Item $extractRoot -Recurse -Force
}
Expand-Archive -Path $nodeZip -DestinationPath $extractRoot -Force
$src = Join-Path $extractRoot "node-v$NodeVersion-win-x64"
Move-Item $src $nodeDir
Remove-Item $nodeZip -Force -ErrorAction SilentlyContinue
Remove-Item $extractRoot -Recurse -Force -ErrorAction SilentlyContinue

# --- lark-cli 二进制（直接下载，避免 npm install 脚本超时）---
$larkZipName = "lark-cli-$LarkVersion-windows-amd64.zip"
$larkZip = Join-Path $env:TEMP $larkZipName
$larkUrls = @(
    "https://registry.npmjs.org/-/binary/lark-cli/v$LarkVersion/$larkZipName",
    "https://registry.npmmirror.com/-/binary/lark-cli/v$LarkVersion/$larkZipName"
)
Download-FileWithRetry -Urls $larkUrls -OutFile $larkZip

if (Test-Path $larkDir) {
    Remove-Item $larkDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $larkDir | Out-Null
Expand-Archive -Path $larkZip -DestinationPath $larkDir -Force
Remove-Item $larkZip -Force -ErrorAction SilentlyContinue

$larkExe = Get-ChildItem $larkDir -Recurse -Filter "lark-cli.exe" | Select-Object -First 1
if (-not $larkExe) {
    throw "lark-cli.exe not found in $larkDir"
}
if ($larkExe.DirectoryName -ne $larkDir) {
    Move-Item $larkExe.FullName (Join-Path $larkDir "lark-cli.exe") -Force
}

Write-Host "完成:"
Write-Host "  Node: $(Join-Path $nodeDir 'node.exe')"
Write-Host "  Lark: $(Join-Path $larkDir 'lark-cli.exe')"
