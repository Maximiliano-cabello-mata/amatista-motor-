#!/usr/bin/env bash
# Instalador de Amatista para Blender (Linux).
#   bash instalar-amatista.sh            # busca Blender
#   AMATISTA_BLENDER=/ruta/blender bash instalar-amatista.sh
cd "$(dirname "$0")" || exit 1

echo
echo "  =============================================="
echo "    AMATISTA para Blender  -  instalador"
echo "  =============================================="
echo

BLENDER=()
if [ -n "${AMATISTA_BLENDER:-}" ]; then
  BLENDER=("$AMATISTA_BLENDER")
elif command -v blender >/dev/null 2>&1; then
  BLENDER=("$(command -v blender)")
elif [ -x /snap/bin/blender ]; then
  BLENDER=(/snap/bin/blender)
else
  # Descargas de blender.org descomprimidas en la carpeta personal u /opt (la más nueva).
  suelto="$(ls -d "$HOME"/blender-*/blender "$HOME"/Descargas/blender-*/blender "$HOME"/Downloads/blender-*/blender \
                  /opt/blender*/blender 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$suelto" ]; then
    BLENDER=("$suelto")
  elif command -v flatpak >/dev/null 2>&1 && flatpak info org.blender.Blender >/dev/null 2>&1; then
    BLENDER=(flatpak run org.blender.Blender)
  fi
fi
if [ ${#BLENDER[@]} -eq 0 ]; then
  echo "  No encontré Blender. Instálalo (4.2 o más nuevo) desde https://www.blender.org/download/"
  echo "  o indica la ruta:  AMATISTA_BLENDER=/ruta/a/blender bash $0"
  exit 1
fi
echo "  Blender: ${BLENDER[*]}"

ZIP="$(ls amatista-*.zip 2>/dev/null | sort -V | tail -n 1)"
if [ -z "$ZIP" ]; then echo "  Falta amatista-*.zip junto al instalador."; exit 1; fi

echo
"${BLENDER[@]}" --background --python-exit-code 9 --python "$PWD/instalar_en_blender.py" -- "$PWD/$ZIP"
codigo=$?
echo
case $codigo in
  0) echo "  ** Listo. Abre Blender: la pestaña Amatista está en la barra lateral (tecla N). **" ;;
  3) echo "  Tu Blender no es compatible: Amatista necesita Blender 4.2 o más nuevo." ;;
  *) echo "  No se pudo instalar (código $codigo). Revisa LEEME.txt para instalarlo a mano." ;;
esac
exit "$codigo"
