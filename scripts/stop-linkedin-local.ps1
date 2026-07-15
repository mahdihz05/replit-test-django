$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $root '.runtime'

foreach ($name in @('linkedin-backend.pid', 'linkedin-frontend.pid')) {
    $pidFile = Join-Path $runtime $name
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($savedPid -and $savedPid -match '^\d+$') {
        $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
        if ($process) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Output 'Managed LinkedIn local-test processes stopped.'
