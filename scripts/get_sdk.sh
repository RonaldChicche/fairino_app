#!/usr/bin/env bash
# Descarga el SDK oficial de FAIRINO y copia la carpeta "fairino" al lado de
# demo.py. Hace falta porque el SDK no esta en PyPI ni trae metadatos de
# empaquetado, asi que uv/pip no pueden instalarlo.
#
# Uso:  ./scripts/get_sdk.sh

set -euo pipefail

REPO="https://github.com/FAIR-INNOVATION/fairino-python-sdk.git"
DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/fairino"

# linux/Robot.py y windows/Robot.py son identicos (mismo md5) y Python puro,
# asi que en macOS vale el de linux.
case "$(uname -s)" in
    Linux*|Darwin*)         PLATAFORMA="linux" ;;
    CYGWIN*|MINGW*|MSYS*)   PLATAFORMA="windows" ;;
    *) echo "Sistema no reconocido: $(uname -s). Usando linux." >&2
       PLATAFORMA="linux" ;;
esac
echo "Sistema: $(uname -s) -> usando carpeta '$PLATAFORMA' del SDK"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Clonando el SDK ..."
git clone --depth 1 --quiet "$REPO" "$TMP/sdk"

ORIGEN="$TMP/sdk/$PLATAFORMA/fairino"
if [ ! -f "$ORIGEN/Robot.py" ]; then
    echo "ERROR: no se encontro $ORIGEN/Robot.py" >&2
    echo "La estructura del repo del SDK pudo haber cambiado." >&2
    exit 1
fi

# Solo Robot.py y README.txt: __pycache__/ y build/ son ~150 MB de binarios
# de otras plataformas que esta demo no usa.
echo "Copiando a $DEST ..."
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$ORIGEN/Robot.py" "$DEST/"
[ -f "$ORIGEN/README.txt" ] && cp "$ORIGEN/README.txt" "$DEST/"

echo "Listo. SDK en $DEST ($(du -sh "$DEST" | cut -f1))"
