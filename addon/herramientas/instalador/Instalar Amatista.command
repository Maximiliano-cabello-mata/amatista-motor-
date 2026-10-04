#!/bin/bash
# Instalador de Amatista para Blender (macOS). Doble clic para ejecutarlo.
# Si macOS lo bloquea: clic derecho › Abrir › Abrir.
cd "$(dirname "$0")" || exit 1

echo
echo "  =============================================="
echo "    AMATISTA para Blender  -  instalador"
echo "  =============================================="
echo

fin() { echo; read -r -n 1 -p "  Pulsa una tecla para cerrar…"; echo; exit "${1:-0}"; }

BLENDER="${AMATISTA_BLENDER:-}"
if [ -z "$BLENDER" ]; then
  # Blender.app primero; si hay varias versiones (Blender 4.2.app…), la más nueva.
  for app in /Applications/Blender.app "$HOME/Applications/Blender.app" \
             $(ls -d /Applications/Blender*.app "$HOME"/Applications/Blender*.app 2>/dev/null | sort -rV); do
    if [ -x "$app/Contents/MacOS/Blender" ]; then BLENDER="$app/Contents/MacOS/Blender"; break; fi
  done
fi
if [ -z "$BLENDER" ]; then
  echo "  No encontré Blender en Aplicaciones."
  echo "  Arrastra aquí Blender.app (o su ejecutable) y pulsa Enter,"
  echo "  o descarga Blender 4.2 o más nuevo en https://www.blender.org/download/"
  read -r -p "  Blender: " BLENDER
  BLENDER="${BLENDER%\"}"; BLENDER="${BLENDER#\"}"; BLENDER="${BLENDER%/}"
  [ -d "$BLENDER" ] && BLENDER="$BLENDER/Contents/MacOS/Blender"
fi
if [ ! -x "$BLENDER" ]; then echo "  No encuentro Blender en «$BLENDER»."; fin 1; fi
echo "  Blender: $BLENDER"

ZIP="$(ls amatista-*.zip 2>/dev/null | sort -V | tail -n 1)"
if [ -z "$ZIP" ]; then echo "  Falta amatista-*.zip junto al instalador."; fin 1; fi

echo
"$BLENDER" --background --python-exit-code 9 --python instalar_en_blender.py -- "$PWD/$ZIP"
codigo=$?
echo
case $codigo in
  0) echo "  ** Listo. Abre Blender: la pestaña Amatista está en la barra lateral (tecla N). **" ;;
  3) echo "  Tu Blender no es compatible: Amatista necesita Blender 4.2 o más nuevo." ;;
  *) echo "  No se pudo instalar (código $codigo). Revisa LEEME.txt para instalarlo a mano." ;;
esac
fin "$codigo"
