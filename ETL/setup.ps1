# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
$ErrorActionPreference = "Stop"
$ProjectFolder = $PSScriptRoot
$VenvFolder = Join-Path $ProjectFolder ".venv"
$VenvPython = Join-Path $VenvFolder "Scripts\python.exe"
$PythonVersion = "3.13"

# Locate requirements.txt (ETL folder or repository root)
$RequirementsFile = Join-Path $ProjectFolder "requirements.txt"
if (-not (Test-Path $RequirementsFile)) {
    $ParentRequirements = Join-Path (Split-Path $ProjectFolder -Parent) "requirements.txt"

    if (Test-Path $ParentRequirements) {
        $RequirementsFile = $ParentRequirements
    }
}
if (-not (Test-Path $RequirementsFile)) {
    throw "Could not find requirements.txt."
}

Write-Host "`n---------------- Setting up Python environment ----------------`n"

# ---------------------------------------------------------
# Find or install uv
# ---------------------------------------------------------
function Find-Uv {

    $Command = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($Command) {
        return $Command.Path
    }

    $DefaultPath = Join-Path $HOME ".local\bin\uv.exe"

    if (Test-Path $DefaultPath) {
        return $DefaultPath
    }

    return $null
}

$UvExe = Find-Uv
if (-not $UvExe) {

    Write-Host "uv not found. Installing uv..."

    try {
        Invoke-RestMethod "https://astral.sh/uv/install.ps1" | Invoke-Expression
    }
    catch {
        throw "Failed to install uv. Check your internet connection."
    }

    $UvExe = Find-Uv
}
if (-not $UvExe) {
    throw "Could not locate uv after installation."
}
Write-Host "Using uv: $UvExe"

# ---------------------------------------------------------
# Check existing virtual environment
# ---------------------------------------------------------
$VenvIsValid = $false
if (Test-Path $VenvPython) {

    try {

        $ExistingVersion = & $VenvPython --version 2>&1
        $VersionExitCode = $LASTEXITCODE

        $VenvCheck = & $VenvPython -c "import sys; print(sys.prefix != sys.base_prefix)" 2>&1
        $VenvCheckExitCode = $LASTEXITCODE

        if (
            $VersionExitCode -eq 0 -and
            $VenvCheckExitCode -eq 0 -and
            "$ExistingVersion" -match "^Python $([regex]::Escape($PythonVersion))(\.|$)" -and
            "$VenvCheck".Trim() -eq "True"
        ) {
            $VenvIsValid = $true
            Write-Host "Existing Python $PythonVersion environment found."
        }

    }
    catch {
        $VenvIsValid = $false
    }
}
# ---------------------------------------------------------
# Create virtual environment if required
# ---------------------------------------------------------

if (-not $VenvIsValid) {

    Write-Host "`nInstalling Python $PythonVersion..."

    & $UvExe python install $PythonVersion

    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed."
    }

    # Remove existing environment if necessary
    if (Test-Path $VenvFolder) {

        Write-Host "Removing existing virtual environment..."

        Remove-Item -Recurse -Force $VenvFolder
    }

    Write-Host "`nCreating virtual environment..."

    & $UvExe venv --python $PythonVersion --seed $VenvFolder

    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed."
    }
}


# ---------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------

Write-Host "`n---------------- Installing Python dependencies ----------------`n"

# Upgrade pip
Write-Host "Upgrading pip..."

& $UvExe pip install --python $VenvPython --upgrade pip

if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

# Install project requirements
Write-Host "`nInstalling requirements..."

& $UvExe pip install --python $VenvPython -r $RequirementsFile

if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}


# ---------------------------------------------------------
# Complete
# ---------------------------------------------------------

Write-Host "`n---------------- Environment built ----------------`n"

Write-Host "Setup complete!"

Write-Host "`nPython environment: $VenvFolder"

Write-Host "`nTo activate your environment, run:"
Write-Host "& `"$VenvFolder\Scripts\Activate.ps1`""