@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Instalar Amatista en Blender
cd /d "%~dp0"

echo.
echo   ==============================================
echo     AMATISTA para Blender  -  instalador
echo   ==============================================
echo.

rem 1. Buscar Blender (el mas nuevo de Archivos de programa, Steam o el PATH).
set "BLENDER="
if defined AMATISTA_BLENDER set "BLENDER=%AMATISTA_BLENDER%"
set "PF=%ProgramFiles%"
set "PF86=%ProgramFiles(x86)%"
if not defined BLENDER (
  for /d %%D in ("%PF%\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
if not defined BLENDER (
  if exist "%PF86%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%PF86%\Steam\steamapps\common\Blender\blender.exe"
)
if not defined BLENDER (
  for /f "delims=" %%B in ('where blender 2^>nul') do if not defined BLENDER set "BLENDER=%%B"
)
if not defined BLENDER (
  echo   No encontre Blender automaticamente.
  echo   Arrastra aqui el archivo blender.exe y pulsa Enter
  echo   ^(o descarga Blender 4.2 o mas nuevo en https://www.blender.org/download/^).
  echo.
  set /p "BLENDER=  blender.exe: "
  set "BLENDER=!BLENDER:"=!"
)
if not exist "!BLENDER!" (
  echo.
  echo   No encuentro "!BLENDER!". Instala Blender y vuelve a abrir este instalador.
  goto :fin
)
echo   Blender: !BLENDER!

rem 2. La extension viene junto a este archivo.
set "ZIP="
for %%Z in ("%~dp0amatista-*.zip") do set "ZIP=%%~fZ"
if not defined ZIP (
  echo   Falta el archivo amatista-*.zip junto al instalador. Descarga el paquete otra vez.
  goto :fin
)

rem 3. Blender comprueba su version e instala la extension.
echo.
"!BLENDER!" --background --python-exit-code 9 --python "%~dp0instalar_en_blender.py" -- "!ZIP!"
set "CODIGO=!ERRORLEVEL!"
echo.
if "!CODIGO!"=="0" (
  echo   ** Listo. Abre Blender: la pestana Amatista esta en la barra lateral ^(tecla N^). **
) else if "!CODIGO!"=="3" (
  echo   Tu Blender no es compatible: Amatista necesita Blender 4.2 o mas nuevo.
) else (
  echo   No se pudo instalar ^(codigo !CODIGO!^). Revisa LEEME.txt para instalarlo a mano.
)

:fin
echo.
pause
