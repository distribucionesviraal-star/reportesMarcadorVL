@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

rem ============================================================
rem CONFIGURACION - AJUSTAR SOLO SI CAMBIAN LAS RUTAS
rem ============================================================
set "REPO_DIR=C:\Users\Lenovo\Downloads\reporteD\dashboardGit"
set "REPORT_DIR=%REPO_DIR%\reportesDiariosVL"
set "REMOTE=origin"
set "BRANCH=main"
set "MIN_REPORTS=1"
set "LOCK_DIR=%TEMP%\actualizar_reportes_github_diario.lock"

rem ============================================================
rem PREPARAR FECHA, LOG Y BLOQUEO DE EJECUCIONES DUPLICADAS
rem ============================================================
for /f %%I in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TIMESTAMP=%%I"
for /f %%I in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "TODAY=%%I"

set "LOG_DIR=%REPO_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\actualizacion_%TIMESTAMP%.log"

mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 (
    echo [%date% %time%] ERROR: Ya existe otra ejecucion activa.>>"%LOG_FILE%"
    exit /b 20
)

echo ============================================================>>"%LOG_FILE%"
echo Inicio: %date% %time%>>"%LOG_FILE%"
echo Repositorio: %REPO_DIR%>>"%LOG_FILE%"
echo Modo: Publicacion de PDF ya generados>>"%LOG_FILE%"
echo ============================================================>>"%LOG_FILE%"

rem ============================================================
rem VALIDACIONES
rem ============================================================
if not exist "%REPO_DIR%\.git" (
    echo [%date% %time%] ERROR: REPO_DIR no es un repositorio Git.>>"%LOG_FILE%"
    set "EXIT_CODE=21"
    goto :FIN
)

if not exist "%REPORT_DIR%" (
    echo [%date% %time%] ERROR: No existe la carpeta de reportes: %REPORT_DIR%>>"%LOG_FILE%"
    set "EXIT_CODE=23"
    goto :FIN
)

where git.exe >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: Git no esta disponible en PATH.>>"%LOG_FILE%"
    set "EXIT_CODE=24"
    goto :FIN
)

cd /d "%REPO_DIR%"
if errorlevel 1 (
    echo [%date% %time%] ERROR: No se pudo abrir el repositorio.>>"%LOG_FILE%"
    set "EXIT_CODE=26"
    goto :FIN
)

rem ============================================================
rem ACTUALIZAR REPOSITORIO ANTES DE PUBLICAR
rem ============================================================
echo [%date% %time%] Actualizando rama %BRANCH%...>>"%LOG_FILE%"
git.exe pull --ff-only "%REMOTE%" "%BRANCH%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: git pull fallo. No se publicaran reportes.>>"%LOG_FILE%"
    set "EXIT_CODE=30"
    goto :FIN
)

rem ============================================================
rem VALIDAR TODOS LOS PDF DISPONIBLES, SIN IMPORTAR LA FECHA
rem ============================================================
for /f %%I in ('powershell.exe -NoProfile -Command "$f=Get-ChildItem -LiteralPath '%REPORT_DIR%' -Filter 'Resumen_*.pdf' -File -ErrorAction SilentlyContinue; @($f).Count"') do set "REPORT_COUNT=%%I"

if not defined REPORT_COUNT set "REPORT_COUNT=0"
echo [%date% %time%] PDF totales disponibles: %REPORT_COUNT%>>"%LOG_FILE%"

if %REPORT_COUNT% LSS %MIN_REPORTS% (
    echo [%date% %time%] ERROR: No existen PDF disponibles para publicar.>>"%LOG_FILE%"
    set "EXIT_CODE=32"
    goto :FIN
)

powershell.exe -NoProfile -Command "$f=Get-ChildItem -LiteralPath '%REPORT_DIR%' -Filter 'Resumen_*.pdf' -File; $vacios=$f.Where({$_.Length -eq 0}); if($vacios.Count -gt 0){$vacios.FullName; exit 1}" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: Se encontro uno o mas PDF vacios.>>"%LOG_FILE%"
    set "EXIT_CODE=33"
    goto :FIN
)

rem ============================================================
rem DETECTAR Y PUBLICAR PDF PENDIENTES DE CUALQUIER DIA
rem ============================================================
echo [%date% %time%] Preparando cambios Git...>>"%LOG_FILE%"
git.exe add --ignore-removal -- "reportesDiariosVL/*.pdf" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: git add fallo.>>"%LOG_FILE%"
    set "EXIT_CODE=40"
    goto :FIN
)

for /f %%I in ('git.exe diff --cached --name-only --diff-filter^=ACM -- "reportesDiariosVL/*.pdf" ^| find.exe /c /v ""') do set "PENDING_COUNT=%%I"
if not defined PENDING_COUNT set "PENDING_COUNT=0"
echo [%date% %time%] PDF nuevos o modificados pendientes: %PENDING_COUNT%>>"%LOG_FILE%"

git.exe diff --cached --quiet
if not errorlevel 1 (
    echo [%date% %time%] No existen PDF pendientes, incluidos dias anteriores.>>"%LOG_FILE%"
    set "EXIT_CODE=0"
    goto :FIN
)

echo [%date% %time%] Archivos pendientes detectados:>>"%LOG_FILE%"
git.exe diff --cached --name-only --diff-filter=ACM -- "reportesDiariosVL/*.pdf" >>"%LOG_FILE%" 2>&1

git.exe commit -m "Publicacion de reportes pendientes hasta %TODAY%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: git commit fallo.>>"%LOG_FILE%"
    set "EXIT_CODE=41"
    goto :FIN
)

git.exe push "%REMOTE%" "%BRANCH%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: git push fallo. El commit permanece local.>>"%LOG_FILE%"
    set "EXIT_CODE=42"
    goto :FIN
)

echo [%date% %time%] EXITO: Reportes publicados en GitHub.>>"%LOG_FILE%"
set "EXIT_CODE=0"

:FIN
echo Fin: %date% %time% - Codigo: %EXIT_CODE%>>"%LOG_FILE%"
rmdir "%LOCK_DIR%" 2>nul
exit /b %EXIT_CODE%
