#!/usr/bin/env bash
# Descarga el SDK oficial de FAIRINO y copia la carpeta "fairino" al lado
# de demo.py.
#
# Hace falta porque el SDK no es instalable con uv/pip: no esta en PyPI y su
# repo no trae pyproject.toml ni setup.py en la raiz. Hay que vendorizarlo.
#
# Uso:  ./scripts/get_sdk.sh

set -euo pipefail

REPO="https://github.com/FAIR-INNOVATION/fairino-python-sdk.git"
DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/fairino"

# Elegir la carpeta del repo segun el sistema.
# Nota: hoy linux/fairino/Robot.py y windows/fairino/Robot.py son identicos
# (mismo md5) y son Python puro, asi que en macOS usamos la version de linux.
case "$(uname -s)" in
    Linux*)                     PLATAFORMA="linux" ;;
    Darwin*)                    PLATAFORMA="linux" ;;  # macOS: ver nota arriba
    CYGWIN*|MINGW*|MSYS*)       PLATAFORMA="windows" ;;
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

# Copiamos solo lo necesario. Se omiten __pycache__/ y build/, que traen
# binarios compilados de otras plataformas (~150 MB) que esta demo no usa.
echo "Copiando a $DEST ..."
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$ORIGEN/Robot.py" "$DEST/"
[ -f "$ORIGEN/README.txt" ] && cp "$ORIGEN/README.txt" "$DEST/"

echo "Listo. SDK en $DEST ($(du -sh "$DEST" | cut -f1))"
