# Locate project directory
$ProjectFolder = $PSScriptRoot # Path of currently executing script
$VenvFolder = Join-Path $ProjectFolder ".venv" # add .venv to path to define virtual environment folder location. 
$VenvPython = Join-Path $VenvFolder "Scripts\python.exe" # Specify the expected location of the virtual environment's Python executable.
$PythonVersion = "3.13"

Write-Host "`n---------------- Setting up Python environment ----------------`n"

# Check that the Python launcher and requested version are available.
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python launcher 'py' was not found. Install Python $PythonVersion and try again."
    exit 1
}
& py "-$PythonVersion" --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python $PythonVersion is not installed. Install it or change `$PythonVersion in this script."
    exit 1
}

# Rebuild the environment if it is missing or uses a different Python version.
$RebuildVenv = -not (Test-Path $VenvPython)
if (-not $RebuildVenv) {
    $ExistingPythonVersion = & $VenvPython --version 2>&1
    if ($ExistingPythonVersion -notlike "Python $PythonVersion*") {
        Write-Host "Existing environment uses $ExistingPythonVersion; rebuilding it with Python $PythonVersion."
        $RebuildVenv = $true
    } else {
        Write-Host "Using existing Python $PythonVersion environment at $VenvFolder."
    }
}
if ($RebuildVenv) {
    if (Test-Path $VenvFolder) {
        Remove-Item -Recurse -Force $VenvFolder
    }

    Write-Host "Creating virtual environment with Python $PythonVersion..."
    & py "-$PythonVersion" -m venv $VenvFolder

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Virtual environment creation failed."
        exit 1
    }
}

Write-Host "`n---------------- Installing Python dependencies ----------------`n"
# Upgrade pip before installing project dependencies.
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip upgrade failed."
    exit 1
}
# Install requirements into the project-local virtual environment.
& $VenvPython -m pip install -r (Join-Path $ProjectFolder "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed."
    exit 1
}
Write-Host "`n--- Environment built ---`n"
Write-Host "Setup complete!"