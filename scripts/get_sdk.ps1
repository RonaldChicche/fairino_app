#Requires -Version 5.1
<#
.SYNOPSIS
    Descarga el SDK oficial de FAIRINO y copia la carpeta "fairino" al lado
    de demo.py.

.DESCRIPTION
    Hace falta porque el SDK no es instalable con uv/pip: no esta publicado
    en PyPI y su repo no trae pyproject.toml ni setup.py en la raiz. Hay que
    vendorizarlo a mano.

    Equivalente PowerShell de scripts/get_sdk.sh.

.EXAMPLE
    .\scripts\get_sdk.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/FAIR-INNOVATION/fairino-python-sdk.git'
$Dest = Join-Path (Split-Path -Parent $PSScriptRoot) 'fairino'

# Elegir la carpeta del repo segun el sistema.
# En Windows PowerShell 5.1 la variable $IsWindows no existe, asi que su
# ausencia ya implica Windows. En PowerShell 7 (multiplataforma) si existe.
# Nota: hoy linux/fairino/Robot.py y windows/fairino/Robot.py son identicos
# (mismo md5) y son Python puro, asi que en macOS/Linux vale la de linux.
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
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el 'git clone' de $Repo (codigo $LASTEXITCODE). Revisa tu conexion."
    }

    $Origen = Join-Path (Join-Path (Join-Path $Tmp 'sdk') $Plataforma) 'fairino'
    $RobotPy = Join-Path $Origen 'Robot.py'
    if (-not (Test-Path -LiteralPath $RobotPy)) {
        throw "No se encontro $RobotPy. La estructura del repo del SDK pudo haber cambiado."
    }

    # Copiamos solo lo necesario. Se omiten __pycache__\ y build\, que traen
    # binarios compilados de otras plataformas (~150 MB) que esta demo no usa.
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
