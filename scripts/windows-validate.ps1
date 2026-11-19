<#
.SYNOPSIS
  Runs the Phase 0 Windows validation steps (docs/PHASE_0_CLOSURE.md, section 6,
  steps 2-9) and writes a report you can send back.

.DESCRIPTION
  Step 1 (installing Node.js, Python, pnpm, and uv from the README section
  "Windows PowerShell") is deliberately NOT automated: it must be done by hand
  so that any undocumented extra step is noticed. Step 10 (looking at the page)
  is manual too.

  The script never changes system settings and never "fixes" a failure. It runs
  each step, records pass/fail, duration, and output, and continues. Output is
  written to a new folder windows-validation-<timestamp> in the repository root.

.PARAMETER SkipBrowserTests
  Skip step 7 (Playwright browser download and browser tests).

.PARAMETER SkipInstall
  Skip step 2 (dependency installation) when you have just run it yourself.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows-validate.ps1
#>
param(
    [switch]$SkipBrowserTests,
    [switch]$SkipInstall
)

# Windows 7 ships PowerShell 2.0, which lacks $PSScriptRoot, Invoke-WebRequest and
# other things this script needs. Stop early with a clear message instead.
if ($PSVersionTable -and $PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host ""
    Write-Host "This script needs Windows PowerShell 5.1 or newer. Found version $($PSVersionTable.PSVersion)." -ForegroundColor Red
    Write-Host "Windows: $([System.Environment]::OSVersion.VersionString)"
    Write-Host "Windows 7 includes PowerShell 2.0. On older Windows the pinned Node.js and Python"
    Write-Host "versions are also unlikely to install. Use Windows 10 or Windows 11, then run this"
    Write-Host "script again, and tell the project owner which Windows version you used."
    exit 3
}

$ErrorActionPreference = "Continue"
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$root = (Resolve-Path (Join-Path $scriptDir "..")).Path
Set-Location $root

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outDir = Join-Path $root "windows-validation-$stamp"
New-Item -ItemType Directory -Path $outDir | Out-Null
$logFile = Join-Path $outDir "full-output.log"
$reportFile = Join-Path $outDir "report.md"
$apiPort = 8765
$webPort = 3000

$script:results = New-Object System.Collections.ArrayList
$script:lastExit = 0

function Write-Log([string]$Text) {
    $Text | Out-File -FilePath $logFile -Append -Encoding utf8
}

function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect("127.0.0.1", $Port)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

# Runs one native command, streams and logs its output, stores its exit code in
# $script:lastExit. A command that cannot be started gets exit code 9009.
function Invoke-Native([string[]]$Command) {
    $exe = $Command[0]
    $rest = @()
    if ($Command.Length -gt 1) { $rest = $Command[1..($Command.Length - 1)] }
    $line = "> " + ($Command -join " ")
    Write-Host $line -ForegroundColor Cyan
    Write-Log $line
    try {
        & $exe @rest 2>&1 | ForEach-Object {
            $text = "$_"
            Write-Host $text
            Write-Log $text
        }
        $script:lastExit = $LASTEXITCODE
    }
    catch {
        $message = "Could not run '$exe': $($_.Exception.Message)"
        Write-Host $message -ForegroundColor Red
        Write-Log $message
        $script:lastExit = 9009
    }
    if ($null -eq $script:lastExit) { $script:lastExit = 0 }
    Write-Log "(exit code $($script:lastExit))"
}

# Runs a step made of several commands; the step passes only if all exit 0.
function Invoke-Step([string]$Id, [string]$Title, [object[]]$Commands) {
    Write-Host ""
    Write-Host "=== Step $Id : $Title ===" -ForegroundColor Yellow
    Write-Log ""
    Write-Log "=== Step $Id : $Title ==="
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $status = "PASS"
    foreach ($command in $Commands) {
        Invoke-Native $command
        if ($script:lastExit -ne 0) {
            $status = "FAIL (exit code $($script:lastExit))"
            break
        }
    }
    $timer.Stop()
    Add-Result $Id $Title $status ([math]::Round($timer.Elapsed.TotalSeconds, 1))
}

function Add-Result([string]$Id, [string]$Title, [string]$Status, $Seconds) {
    [void]$script:results.Add([pscustomobject]@{
        Id = $Id; Title = $Title; Status = $Status; Seconds = $Seconds
    })
    $color = "Green"
    if ($Status -like "FAIL*") { $color = "Red" } elseif ($Status -like "SKIPPED*") { $color = "DarkYellow" }
    Write-Host "Step $Id : $Status" -ForegroundColor $color
}

function Get-Version([string[]]$Command) {
    try {
        $exe = $Command[0]
        $rest = @()
        if ($Command.Length -gt 1) { $rest = $Command[1..($Command.Length - 1)] }
        $out = & $exe @rest 2>&1 | Select-Object -First 1
        return "$out".Trim()
    }
    catch {
        return "NOT FOUND"
    }
}

# --- Environment ---------------------------------------------------------

Write-Host "Smart Engineer Windows validation" -ForegroundColor Yellow
Write-Host "Output folder: $outDir"

$osText = [System.Environment]::OSVersion.VersionString
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $osText = "$($os.Caption) (build $($os.BuildNumber))"
}
catch { }

$commit = "(not a git checkout)"
if (Test-Path (Join-Path $root ".git")) {
    $commit = Get-Version @("git", "rev-parse", "--short", "HEAD")
}

$tools = @(
    @{ Name = "Node.js"; Command = @("node", "--version"); Expected = "v24.22.3" },
    @{ Name = "pnpm"; Command = @("pnpm", "--version"); Expected = "12.16.1" },
    @{ Name = "uv"; Command = @("uv", "--version"); Expected = "uv 0.13.8" }
)
$toolLines = New-Object System.Collections.ArrayList
$missing = $false
foreach ($tool in $tools) {
    $actual = Get-Version $tool.Command
    $note = "matches expected"
    if ($actual -eq "NOT FOUND" -or $actual -eq "") { $note = "MISSING"; $missing = $true }
    elseif (-not $actual.StartsWith($tool.Expected)) { $note = "differs from expected $($tool.Expected)" }
    [void]$toolLines.Add("| $($tool.Name) | $actual | $note |")
    Write-Log "$($tool.Name): $actual ($note)"
}

function Write-Report([string]$Extra) {
    $lines = New-Object System.Collections.ArrayList
    [void]$lines.Add("# Smart Engineer Windows validation report")
    [void]$lines.Add("")
    [void]$lines.Add("- Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    [void]$lines.Add("- Windows: $osText")
    [void]$lines.Add("- PowerShell: $($PSVersionTable.PSVersion)")
    [void]$lines.Add("- Repository commit: $commit")
    [void]$lines.Add("- Folder: $root")
    [void]$lines.Add("")
    [void]$lines.Add("| Tool | Found | Note |")
    [void]$lines.Add("|---|---|---|")
    foreach ($l in $toolLines) { [void]$lines.Add($l) }
    [void]$lines.Add("")
    if ($Extra) { [void]$lines.Add($Extra); [void]$lines.Add("") }
    [void]$lines.Add("| Step | Result | Seconds |")
    [void]$lines.Add("|---|---|---|")
    foreach ($r in $script:results) {
        [void]$lines.Add("| $($r.Id) $($r.Title) | $($r.Status) | $($r.Seconds) |")
    }
    [void]$lines.Add("")
    [void]$lines.Add("Step 1 (manual install) and step 10 (look at the page) are not covered by this script.")
    $failed = @($script:results | Where-Object { $_.Status -like "FAIL*" })
    if ($failed.Count -gt 0) {
        [void]$lines.Add("")
        [void]$lines.Add("## Last output lines of failed steps")
        [void]$lines.Add("See full-output.log for everything.")
    }
    $lines | Out-File -FilePath $reportFile -Encoding utf8
}

if ($missing) {
    $message = "One or more required tools were not found. Follow README section 'Windows PowerShell' (step 1), open a NEW PowerShell window, and run this script again."
    Write-Host $message -ForegroundColor Red
    Add-Result "1" "Required tools present (node, pnpm, uv)" "FAIL (tool missing)" 0
    Write-Report $message
    Write-Host "Report: $reportFile"
    exit 2
}
Add-Result "1" "Required tools present (node, pnpm, uv) - install itself is manual" "PASS" 0

$busy = @()
foreach ($port in @($webPort, $apiPort)) { if (Test-PortInUse $port) { $busy += $port } }
if ($busy.Count -gt 0) {
    $message = "Port(s) $($busy -join ', ') already in use. Close the program using them and run again."
    Write-Host $message -ForegroundColor Red
    Add-Result "0" "Ports $webPort and $apiPort are free" "FAIL (in use: $($busy -join ', '))" 0
    Write-Report $message
    Write-Host "Report: $reportFile"
    exit 2
}

# --- Steps ---------------------------------------------------------------

$web = "@smart-engineer/web"

if ($SkipInstall) {
    Add-Result "2" "Install dependencies" "SKIPPED (-SkipInstall)" 0
}
else {
    Invoke-Step "2" "Install dependencies (frozen lockfile)" @(
        @("pnpm", "install", "--frozen-lockfile"),
        @("uv", "sync", "--locked", "--all-packages")
    )
}

Invoke-Step "3" "Python lint (ruff)" @(
    ,@("uv", "run", "--package", "smart-engineer-api", "--group", "dev", "ruff", "check", "apps/api")
)

Invoke-Step "4" "API tests" @(
    ,@("uv", "run", "--package", "smart-engineer-api", "--group", "dev", "python", "-m", "unittest", "discover", "-s", "apps/api/tests", "-t", "apps/api")
)

Invoke-Step "5" "Web lint and typecheck" @(
    @("pnpm", "--filter", $web, "run", "lint"),
    @("pnpm", "--filter", $web, "run", "typecheck")
)

Invoke-Step "6" "Web production build and smoke tests" @(
    @("pnpm", "--filter", $web, "run", "build"),
    @("pnpm", "--filter", $web, "run", "test:ci")
)

if ($SkipBrowserTests) {
    Add-Result "7" "Browser tests" "SKIPPED (-SkipBrowserTests)" 0
}
else {
    $previousCi = $env:CI
    $env:CI = "1"
    Invoke-Step "7" "Browser tests (Playwright, Chromium)" @(
        @("pnpm", "--filter", $web, "exec", "playwright", "install", "chromium"),
        @("pnpm", "--filter", $web, "run", "test:e2e")
    )
    $env:CI = $previousCi
}

# Step 8: migrations on a throwaway SQLite file (never touches real data).
$dbFile = Join-Path ([System.IO.Path]::GetTempPath()) "se-validate-$stamp.db"
$previousUrl = $env:SMART_ENGINEER_DATABASE_URL
$env:SMART_ENGINEER_DATABASE_URL = "sqlite:///" + ($dbFile -replace "\\", "/")
Invoke-Step "8" "Database migrations up and down (temporary SQLite file)" @(
    @("uv", "run", "--package", "smart-engineer-api", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"),
    @("uv", "run", "--package", "smart-engineer-api", "alembic", "-c", "apps/api/alembic.ini", "downgrade", "base")
)
$env:SMART_ENGINEER_DATABASE_URL = $previousUrl
Remove-Item -Path $dbFile -Force -ErrorAction SilentlyContinue

# Step 9: start the API on a spare port and check its endpoints.
Write-Host ""
Write-Host "=== Step 9 : API live check (port $apiPort) ===" -ForegroundColor Yellow
Write-Log ""
Write-Log "=== Step 9 : API live check (port $apiPort) ==="
$timer = [System.Diagnostics.Stopwatch]::StartNew()
$apiOut = Join-Path $outDir "api-server.out.log"
$apiErr = Join-Path $outDir "api-server.err.log"
$status = "PASS"
$server = $null
try {
    $server = Start-Process -FilePath "uv" -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr `
        -ArgumentList @("run", "--package", "smart-engineer-api", "--group", "dev", "uvicorn",
            "--app-dir", "apps/api", "--host", "127.0.0.1", "--port", "$apiPort", "smart_engineer_api.main:app")

    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$apiPort/health" -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        }
        catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "API did not answer on /health within 60 seconds." }

    foreach ($path in @("/health", "/api/v1/health", "/docs", "/openapi.json")) {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$apiPort$path" -TimeoutSec 10
        $cid = $r.Headers["X-Correlation-ID"]
        $line = "GET $path -> $($r.StatusCode), X-Correlation-ID present: $([bool]$cid)"
        Write-Host $line
        Write-Log $line
        if ($r.StatusCode -ne 200) { throw "$path returned $($r.StatusCode)" }
        if (-not $cid) { throw "$path has no X-Correlation-ID header" }
        if ($path -like "*health" -and $r.Content.Trim() -ne '{"status":"ok"}') {
            throw "$path returned unexpected body: $($r.Content)"
        }
    }

    $notFound = $null
    try { Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$apiPort/no-such-route" -TimeoutSec 10 | Out-Null }
    catch { $notFound = $_.Exception.Response }
    if ($null -eq $notFound -or [int]$notFound.StatusCode -ne 404) { throw "/no-such-route did not return 404" }
    Write-Host "GET /no-such-route -> 404 (expected)"
    Write-Log "GET /no-such-route -> 404 (expected)"
}
catch {
    $status = "FAIL ($($_.Exception.Message))"
    Write-Host $status -ForegroundColor Red
    Write-Log $status
}
finally {
    if ($server -and -not $server.HasExited) {
        & taskkill /PID $server.Id /T /F 2>&1 | Out-Null
    }
}
$timer.Stop()
Add-Result "9" "API live check (/health, /api/v1/health, /docs, 404)" $status ([math]::Round($timer.Elapsed.TotalSeconds, 1))

# --- Report --------------------------------------------------------------

Write-Report ""
$failedSteps = @($script:results | Where-Object { $_.Status -like "FAIL*" })
if ($failedSteps.Count -gt 0) {
    $tail = Get-Content -Path $logFile -Tail 40 -ErrorAction SilentlyContinue
    Add-Content -Path $reportFile -Value "" -Encoding utf8
    Add-Content -Path $reportFile -Value "Last 40 lines of output overall (see full-output.log):" -Encoding utf8
    Add-Content -Path $reportFile -Value '```' -Encoding utf8
    Add-Content -Path $reportFile -Value $tail -Encoding utf8
    Add-Content -Path $reportFile -Value '```' -Encoding utf8
}

Write-Host ""
Write-Host "================ SUMMARY ================" -ForegroundColor Yellow
$script:results | ForEach-Object { Write-Host ("Step {0,-3} {1,-60} {2}" -f $_.Id, $_.Title, $_.Status) }
Write-Host ""
Write-Host "Report:      $reportFile"
Write-Host "Full output: $logFile"
Write-Host "Send both files back. Step 10 (open http://127.0.0.1:3000 with 'pnpm --filter $web run dev' and look at it) is still manual."

if ($failedSteps.Count -gt 0) { exit 1 }
exit 0
