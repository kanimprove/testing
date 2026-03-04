@echo off
echo ==========================================
echo   Clinical Document Pipeline - Setup
echo ==========================================
echo.
echo Checking Docker is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker Desktop is not running.
    echo.
    echo How to fix:
    echo   1. Open Docker Desktop from your Start menu
    echo   2. Wait until the bottom-left shows a green "Engine running" indicator
    echo   3. Then double-click this file again
    echo.
    echo If you haven't installed Docker Desktop yet:
    echo   Go to https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
echo Docker is running. Good!
echo.
echo ==========================================
echo   Building the pipeline...
echo   This takes about 5 minutes the first time.
echo   (It downloads Python, OCR tools, and the
echo    language model. Please be patient.)
echo ==========================================
echo.
docker compose build
if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    echo Check your internet connection and try again.
    echo If this keeps happening, try restarting Docker Desktop.
    echo.
    pause
    exit /b 1
)
echo.
echo ==========================================
echo   Setup complete!
echo.
echo   Next steps:
echo   1. Put your scanned documents (PDF, PNG,
echo      JPG, TIFF) in the "data" folder
echo   2. Double-click "process.bat" to run
echo ==========================================
echo.
pause
