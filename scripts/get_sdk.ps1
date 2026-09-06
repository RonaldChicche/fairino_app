#Requires -Version 5.1
<#
.SYNOPSIS
    Descarga el SDK oficial de FAIRINO y copia la carpeta "fairino" al lado
    de demo.py. Equivalente PowerShell de scripts/get_sdk.sh.

    Hace falta porque el SDK no esta en PyPI ni trae metadatos de
    empaquetado, asi que uv/pip no pueden instalarlo.

.EXAMPLE
    .\scripts\get_sdk.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/FAIR-INNOVATION/fairino-python-sdk.git'
$Dest = Join-Path (Split-Path -Parent $PSScriptRoot) 'fairino'

# En PowerShell 5.1 la variable $IsWindows no existe, asi que su ausencia ya
# implica Windows. linux/Robot.py y windows/Robot.py son identicos.
$Plataforma = 'windows'
$varIsWindows = Get-Variable -Name IsWindows -ErrorAction SilentlyContinue
if ($varIsWindows -and -not $varIsWindows.Value) {
    $Plataforma = 'linux'
}
Write-Host "Sistema detectado -> usando carpeta '$Plataforma' del SDK"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "No se encontro 'git' en el PATH. Instalalo desde https://git-scm.com/download/win"
}

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null

try {
    Write-Host 'Clonando el SDK ...'
    git clone --depth 1 --quiet $Repo (Join-Path $Tmp 'sdk')
    # $ErrorActionPreference no cubre el codigo de salida de comandos nativos.
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el 'git clone' de $Repo (codigo $LASTEXITCODE). Revisa tu conexion."
    }

    $Origen = Join-Path (Join-Path (Join-Path $Tmp 'sdk') $Plataforma) 'fairino'
    $RobotPy = Join-Path $Origen 'Robot.py'
    if (-not (Test-Path -LiteralPath $RobotPy)) {
        throw "No se encontro $RobotPy. La estructura del repo del SDK pudo haber cambiado."
    }

    # Solo Robot.py y README.txt: __pycache__\ y build\ son ~150 MB de
    # binarios de otras plataformas que esta demo no usa.
    Write-Host "Copiando a $Dest ..."
    if (Test-Path -LiteralPath $Dest) {
        Remove-Item -LiteralPath $Dest -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null

    Copy-Item -LiteralPath $RobotPy -Destination $Dest

    $ReadmeTxt = Join-Path $Origen 'README.txt'
    if (Test-Path -LiteralPath $ReadmeTxt) {
        Copy-Item -LiteralPath $ReadmeTxt -Destination $Dest
    }

    $Kb = [math]::Round(
        (Get-ChildItem -LiteralPath $Dest -Recurse -File |
            Measure-Object -Property Length -Sum).Sum / 1KB
    )
    Write-Host "Listo. SDK en $Dest ($Kb KB)"
}
finally {
    if (Test-Path -LiteralPath $Tmp) {
        Remove-Item -LiteralPath $Tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
