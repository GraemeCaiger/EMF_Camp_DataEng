# Locate project directory
$ProjectFolder = $PSScriptRoot # Path of currently executing script
$VenvFolder = Join-Path $ProjectFolder ".venv" # add .venv to path to define virtual environment folder location. 
$VenvPython = Join-Path $VenvFolder "Scripts\python.exe" # Specify the expected location of the virtual environment's Python executable.

Write-Host "`n---------------- Setting up Python environment ----------------`n"
# Reuse the project virtual environment when present; otherwise create it.
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment not found. Creating it at $VenvFolder..."
    python -m venv $VenvFolder

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Virtual environment creation failed."
        exit 1
    }
} else {
    Write-Host "Using existing virtual environment at $VenvFolder."
}

Write-Host "`n---------------- Installing Python dependencies ----------------`n"

# Upgrade pip before installing project dependencies.
& $VenvPython -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip upgrade failed."
    exit 1
}
# Install requirements into the project-local virtual environment.
& $VenvPython -m pip install -r (Join-Path $ProjectFolder "requirements.txt") # Expects to find requirments at same folder level as this script. Adjust path if necessary.

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency installation failed."
    exit 1
}
Write-Host "`n---Environment built---`n"


Write-Host "Setup complete!"