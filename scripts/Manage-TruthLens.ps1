[CmdletBinding()]
param(
    [ValidateSet('check','start','status','stop','restart')][string]$Action = 'check',
    [ValidateSet('backend','website','alerts','adapter','worker','ngrok')][string[]]$Services = @('backend','website','alerts','adapter'),
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PrivateRoot = '',
    [ValidateRange(1024,65535)][int]$WebsitePort = 3000,
    [switch]$EnableProviders,
    [switch]$ControlledAcceptance
)
$ErrorActionPreference = 'Stop'
if ($ControlledAcceptance -and @($Services | Where-Object { $_ -notin @('backend','website') }).Count) { throw 'Controlled acceptance supports only backend and website.' }
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
if (-not $PrivateRoot) {
    if ((Split-Path -Leaf (Split-Path -Parent $project)) -eq '.worktrees') { $PrivateRoot = Split-Path -Parent (Split-Path -Parent $project) }
    else { $PrivateRoot = $project }
}
$private = (Resolve-Path -LiteralPath $PrivateRoot).Path
$runner = Join-Path $project 'scripts\runtime.py'
$runtime = Join-Path $project '.tmp\runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
function Get-Records {
    Get-ChildItem -LiteralPath $runtime -Filter '*.json' | Where-Object { $_.BaseName -notlike '*.*' } | ForEach-Object {
        try {
            $entry = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            if (($entry.controlled_acceptance -or -not $ControlledAcceptance) -and $entry.service -in $Services -and $entry.state -ne 'stopped' -and ([guid]$entry.instance).ToString() -eq $_.BaseName) { $entry }
        } catch { Write-Warning 'Ignored an invalid private runtime record.' }
    }
}
function Test-Owned($entry) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$entry.pid)"
    return ($process -and $process.CommandLine -and $process.CommandLine.Contains($runner) -and $process.CommandLine.Contains([string]$entry.instance))
}
function Get-Python($service) {
    $component = if ($service -in @('adapter','worker','ngrok')) { 'whatsapp-adapter' } else { 'backend' }
    $candidate = Join-Path $project "$component\.venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $candidate)) { $candidate = Join-Path $private "$component\.venv\Scripts\python.exe" }
    if (-not (Test-Path -LiteralPath $candidate)) { throw "Python environment missing for $service. Install the documented dependencies first." }
    return $candidate
}
if ($Action -in @('status','stop','restart')) {
    foreach ($entry in @(Get-Records)) {
        $owned = Test-Owned $entry
        if ($Action -eq 'status') { [pscustomobject]@{Service=$entry.service; State=$entry.state; PID=$entry.pid; Owned=$owned; Port=$entry.port} }
        elseif ($owned) {
            # Graceful stop targets only this launcher's random instance; never kill a port owner.
            $stopFile = Join-Path $runtime (([guid]$entry.instance).ToString() + '.stop')
            [IO.File]::WriteAllText($stopFile, 'stop')
            $deadline = (Get-Date).AddSeconds(20)
            while ((Test-Owned $entry) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
            if (Test-Owned $entry) { Write-Warning "Service $($entry.service) is still stopping; it was not force-killed." }
        }
    }
    if ($Action -in @('status','stop')) { return }
}
if ($Action -in @('start','restart')) {
    # Validate every dependency and port before starting anything; leave other services alone.
    foreach ($service in $Services) {
        $python = Get-Python $service
        $checkArgs = @($runner,'--project',$project,'--private',$private,'--service',$service,'--check')
        if ($service -eq 'website') { $checkArgs += @('--port',[string]$WebsitePort) }
        if ($EnableProviders -and $service -eq 'backend') { $checkArgs += '--providers-enabled' }
        if ($ControlledAcceptance) { $checkArgs += '--controlled-acceptance'; if ($service -eq 'backend') { $checkArgs += @('--port','8002') } }
        $check = (& $python @checkArgs) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw "Preflight failed for $service. No service was started." }
        if ($check.port_in_use) { throw "Port $($check.port) is occupied. Omit $service to reuse your existing service; no existing process was stopped." }
    }
}
foreach ($service in $Services) {
    $python = Get-Python $service
    $argsList = @($runner,'--project',$project,'--private',$private,'--service',$service)
    if ($service -eq 'website') { $argsList += @('--port', [string]$WebsitePort) }
    if ($EnableProviders -and $service -eq 'backend') { $argsList += '--providers-enabled' }
    if ($ControlledAcceptance) { $argsList += '--controlled-acceptance'; if ($service -eq 'backend') { $argsList += @('--port','8002') } }
    if ($Action -eq 'check') { & $python @argsList --check; if ($LASTEXITCODE -ne 0) { throw "Preflight failed for $service. No process was started." }; continue }
    $instance = [guid]::NewGuid().ToString()
    $argsList += @('--instance', $instance)
    $quoted = $argsList | ForEach-Object { '"' + $_.Replace('"','\"') + '"' }
    $process = Start-Process -FilePath $python -ArgumentList $quoted -WindowStyle Hidden -WorkingDirectory $project -PassThru -RedirectStandardOutput (Join-Path $runtime "$instance.stdout.log") -RedirectStandardError (Join-Path $runtime "$instance.stderr.log")
    Start-Sleep -Milliseconds 800
    if ($process.HasExited) { throw "Startup failed for $service. See the private sanitized runtime logs; no existing process was stopped." }
    if ($service -in @('backend','alerts','website','adapter')) {
        $port = switch ($service) { 'backend' {if ($ControlledAcceptance) {8002} else {8000}} 'alerts' {8001} 'website' {$WebsitePort} 'adapter' {8100} }
        $healthPath = if ($service -eq 'backend') { '/api/health' } elseif ($service -eq 'website') { '/' } else { '/health' }
        $ready = $false
        $deadline = (Get-Date).AddSeconds(20)
        while (-not $ready -and (Get-Date) -lt $deadline) {
            try { $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port$healthPath" -TimeoutSec 2; $ready = $response.StatusCode -eq 200 }
            catch { Start-Sleep -Milliseconds 200 }
        }
        if (-not $ready) { throw "Startup health failed for $service. See the private sanitized logs; no existing process was stopped." }
    }
    Write-Output "Started $service (PID $($process.Id)); providers default off, worker/outbound paused."
}
