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

$Dest = Join-Path (Split-Path -Parent $PSScriptRoot) 'fairino'

# En PowerShell 5.1 la variable $IsWindows no existe, asi que su ausencia ya
# implica Windows. linux/Robot.py y windows/Robot.py son identicos.
$Plataforma = 'windows'
$varIsWindows = Get-Variable -Name IsWindows -ErrorAction SilentlyContinue
if ($varIsWindows -and -not $varIsWindows.Value) {
    $Plataforma = 'linux'
}
Write-Host "Sistema detectado -> usando carpeta '$Plataforma' del SDK"

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null

try {
    # El repositorio completo contiene cientos de MB de binarios que esta demo
    # no usa. Descargar los archivos raw evita clones lentos o interrumpidos.
    # El controlador de este proyecto expone el canal de estado legado 20004,
    # no CNDE 20005. Esta es la ultima revision oficial anterior a CNDE.
    $SdkRef = 'v2.2.4_robot_v3.9.4'
    $BaseUrl = "https://raw.githubusercontent.com/FAIR-INNOVATION/fairino-python-sdk/$SdkRef/$Plataforma/fairino"
    $RobotPy = Join-Path $Tmp 'Robot.py'
    Write-Host 'Descargando Robot.py del SDK oficial ...'
    Invoke-WebRequest -Uri "$BaseUrl/Robot.py" -OutFile $RobotPy -UseBasicParsing

    # Solo Robot.py y README.txt: __pycache__\ y build\ son ~150 MB de
    # binarios de otras plataformas que esta demo no usa.
    Write-Host "Copiando a $Dest ..."
    if (Test-Path -LiteralPath $Dest) {
        Remove-Item -LiteralPath $Dest -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null

    Copy-Item -LiteralPath $RobotPy -Destination $Dest

    $ReadmeTxt = Join-Path $Tmp 'README.txt'
    try {
        Invoke-WebRequest -Uri "$BaseUrl/README.txt" -OutFile $ReadmeTxt -UseBasicParsing
        Copy-Item -LiteralPath $ReadmeTxt -Destination $Dest
    }
    catch {
        Write-Warning 'No se pudo descargar README.txt; Robot.py si esta instalado.'
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
