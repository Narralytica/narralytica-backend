param(
  [switch]$ForceBrief
)

$ErrorActionPreference = "Stop"

$pythonCandidates = @()
if ($env:PYTHON) {
  $pythonCandidates += $env:PYTHON
}
$pythonCandidates += @(
  "python",
  "py",
  "C:\Users\elias\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
  if ([string]::IsNullOrWhiteSpace($candidate)) {
    continue
  }

  if (Test-Path -LiteralPath $candidate) {
    $python = $candidate
    break
  }

  $command = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($command) {
    $python = $command.Source
    break
  }
}

if (-not $python) {
  throw "Python was not found. Install Python 3.11+ or set the PYTHON environment variable to your python.exe path."
}

$argsList = @("scripts\run_terminal_pipeline.py", "--publish")
if ($ForceBrief) {
  $argsList += "--force-brief"
}

Write-Host "Running Narralytica backend pipeline..." -ForegroundColor Cyan
Write-Host "Python: $python" -ForegroundColor DarkGray
Write-Host "Command: $python $($argsList -join ' ')" -ForegroundColor DarkGray

& $python @argsList

if ($LASTEXITCODE -ne 0) {
  throw "Backend pipeline failed with exit code $LASTEXITCODE."
}

Write-Host "Narralytica backend pipeline completed." -ForegroundColor Green
