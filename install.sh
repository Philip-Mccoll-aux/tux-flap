#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Instala Tux Flap para el usuario actual, sin root y sin Flatpak:
# copia el juego a ~/.local/share/tuxflap/app, crea el lanzador ~/.local/bin/tuxflap
# y registra el icono y la entrada de menú (Plasma Mobile, Plasma, GNOME...).
#
# Uso:   ./install.sh              instala o actualiza
#        ./install.sh --uninstall  desinstala (conserva tu récord)
set -eu

APP_ID="io.github.philip_mccoll_aux.TuxFlap"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="$HOME/.local/bin"
CODE="$DATA/tuxflap/app"
ICON="$DATA/icons/hicolor/scalable/apps/$APP_ID.svg"
DESKTOP="$DATA/applications/$APP_ID.desktop"
LAUNCHER="$BIN/tuxflap"

refresh_menu() {
    # Que el menú de aplicaciones vea los cambios sin cerrar la sesión
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
    fi
    for k in kbuildsycoca6 kbuildsycoca5; do
        if command -v "$k" >/dev/null 2>&1; then
            "$k" >/dev/null 2>&1 || true
            break
        fi
    done
}

case "${1:-}" in
    -h|--help)
        sed -n '4,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    --uninstall)
        rm -f "$LAUNCHER" "$DESKTOP" "$ICON"
        rm -rf "$CODE"
        refresh_menu
        echo "Tux Flap desinstalado (tu récord queda en $DATA/tuxflap/score.json)."
        exit 0
        ;;
    "") ;;
    *) echo "Opción desconocida: $1 (usa --help)" >&2; exit 2 ;;
esac

# --- comprobaciones
if [ ! -f "$SRC/tuxflap/game.py" ] || [ ! -f "$SRC/data/$APP_ID.desktop" ]; then
    echo "Ejecuta install.sh desde la carpeta del proyecto (la que contiene tuxflap/ y data/)." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Falta python3. Instálalo con: sudo apt install python3" >&2
    exit 1
fi
if ! python3 -c 'import pygame' >/dev/null 2>&1; then
    echo "Falta pygame."
    if command -v apt-get >/dev/null 2>&1 && [ -t 0 ]; then
        read -r -p "¿Instalar python3-pygame con apt (te pedirá la contraseña de sudo)? [S/n] " ans
        case "${ans:-S}" in
            [sSyY]*) sudo apt-get install -y python3-pygame ;;
            *) echo "Instálalo y vuelve a ejecutar: sudo apt install python3-pygame" >&2; exit 1 ;;
        esac
    else
        echo "Instálalo y vuelve a ejecutar: sudo apt install python3-pygame" >&2
        exit 1
    fi
    python3 -c 'import pygame' >/dev/null 2>&1 || { echo "pygame sigue sin poder importarse." >&2; exit 1; }
fi

# --- juego (se reemplaza el código; el récord vive aparte, en $DATA/tuxflap/score.json)
rm -rf "$CODE"
mkdir -p "$CODE" "$BIN" "$(dirname "$ICON")" "$(dirname "$DESKTOP")"
cp -r "$SRC/tuxflap" "$CODE/"
find "$CODE" -name '__pycache__' -type d -prune -exec rm -rf {} +

# --- lanzador
cat > "$LAUNCHER" <<EOF
#!/bin/sh
# Lanzador de Tux Flap (generado por install.sh)
export PYTHONPATH="$CODE\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m tuxflap "\$@"
EOF
chmod 755 "$LAUNCHER"

# --- icono y entrada de menú (con rutas absolutas para no depender del PATH ni de la caché de iconos)
install -m 644 "$SRC/data/$APP_ID.svg" "$ICON"
sed -e "s|^Exec=.*|Exec=$LAUNCHER|" -e "s|^Icon=.*|Icon=$ICON|" "$SRC/data/$APP_ID.desktop" > "$DESKTOP"
chmod 644 "$DESKTOP"
refresh_menu

echo
echo "Tux Flap instalado."
echo "  - Búscalo en el menú de aplicaciones (Juegos) como «Tux Flap»."
echo "  - O ejecútalo desde la terminal: $LAUNCHER"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "  - (Nota: $BIN no está en tu PATH; usa el menú o la ruta completa.)" ;;
esac
echo "  - Para actualizar: git pull && ./install.sh   |   Para quitarlo: ./install.sh --uninstall"
echo "  - Si el toque o el tamaño fallan, prueba: SDL_VIDEODRIVER=wayland tuxflap   o   SDL_VIDEODRIVER=x11 tuxflap"
