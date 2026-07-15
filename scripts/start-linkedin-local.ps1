param(
    [int]$FrontendPort = 5173,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $root '.runtime'
$envFile = Join-Path $root '.env'
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment was not found: $python"
}
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Local .env file was not found: $envFile"
}
$pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if (-not $pnpm) {
    throw 'pnpm.cmd was not found in PATH.'
}

New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$certDir = Join-Path $runtime 'certs'
$pfxPath = Join-Path $certDir 'localhost.pfx'
$pfxPassword = 'mohtavayar-local-https'
New-Item -ItemType Directory -Path $certDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $pfxPath)) {
    $rsa = [Security.Cryptography.RSA]::Create(2048)
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
        'CN=localhost',
        $rsa,
        [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    $san = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddDnsName('localhost')
    $san.AddIpAddress([Net.IPAddress]::Loopback)
    $request.CertificateExtensions.Add($san.Build())
    $certificate = $request.CreateSelfSigned([DateTimeOffset]::Now.AddDays(-1), [DateTimeOffset]::Now.AddYears(1))
    $pfxBytes = $certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $pfxPassword)
    [IO.File]::WriteAllBytes($pfxPath, $pfxBytes)
    $certificate.Dispose()
    $rsa.Dispose()
}

function Stop-ManagedProcess([string]$PidFile) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return }
    $savedPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($savedPid -and $savedPid -match '^\d+$') {
        $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
        if ($process) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Set-EnvValue([string]$Name, [string]$Value) {
    $lines = @(Get-Content -LiteralPath $envFile -Encoding UTF8)
    $replacement = "$Name=$Value"
    $found = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match ('^' + [Regex]::Escape($Name) + '=')) {
            $lines[$index] = $replacement
            $found = $true
        }
    }
    if (-not $found) { $lines += $replacement }
    [IO.File]::WriteAllLines($envFile, $lines, [Text.UTF8Encoding]::new($false))
}

$backendPidFile = Join-Path $runtime 'linkedin-backend.pid'
$frontendPidFile = Join-Path $runtime 'linkedin-frontend.pid'
Stop-ManagedProcess $backendPidFile
Stop-ManagedProcess $frontendPidFile

$env:PORT = [string]$FrontendPort
$env:BASE_PATH = '/'
$env:LOCAL_HTTPS_PFX = $pfxPath
$env:LOCAL_HTTPS_PFX_PASSWORD = $pfxPassword
$frontend = Start-Process -FilePath $pnpm.Source `
    -ArgumentList @('--filter', '@workspace/frontend', 'run', 'dev') `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $runtime 'linkedin-frontend.out.log') `
    -RedirectStandardError (Join-Path $runtime 'linkedin-frontend.err.log') `
    -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $frontendPidFile -Value $frontend.Id

$backend = Start-Process -FilePath $python `
    -ArgumentList @('backend\manage.py', 'runserver', "127.0.0.1:$BackendPort", '--noreload') `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $runtime 'linkedin-backend.out.log') `
    -RedirectStandardError (Join-Path $runtime 'linkedin-backend.err.log') `
    -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $backendPidFile -Value $backend.Id

$publicUrl = "https://localhost:$FrontendPort"
$callback = "$publicUrl/api/auth/linkedin/callback/"
Set-EnvValue 'LINKEDIN_REDIRECT_URI' $callback
Set-EnvValue 'LINKEDIN_API_VERSION' '202606'

# Django reads .env only at process start, so restart just the managed backend.
Stop-ManagedProcess $backendPidFile
$backend = Start-Process -FilePath $python `
    -ArgumentList @('backend\manage.py', 'runserver', "127.0.0.1:$BackendPort", '--noreload') `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $runtime 'linkedin-backend.out.log') `
    -RedirectStandardError (Join-Path $runtime 'linkedin-backend.err.log') `
    -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $backendPidFile -Value $backend.Id

Write-Output "APP_URL=$publicUrl"
Write-Output "LINKEDIN_CALLBACK=$callback"
Write-Output 'On the first visit, accept the browser warning for the local development certificate.'
