@echo off
echo ==========================================
echo   Clinical Document Pipeline - Process
echo ==========================================
echo.
echo Checking Docker is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker Desktop is not running.
    echo Please open Docker Desktop, wait for the green
    echo indicator, then double-click this file again.
    echo.
    pause
    exit /b 1
)
echo Docker is running. Good!
echo.
echo Processing all documents in the "data" folder...
echo.
docker compose run --rm phi-pipeline process-all /app/data --output-dir /app/output --mapping-dir /app/data/phi_mappings
if errorlevel 1 (
    echo.
    echo Something went wrong during processing.
    echo Make sure you have run setup.bat first.
    echo.
    pause
    exit /b 1
)
echo.
echo ==========================================
echo   Done! Opening the output folder...
echo ==========================================
echo.
echo Your de-identified documents are in the "output" folder.
echo Each .txt file contains the document text with all
echo patient information replaced by placeholders like
echo [PATIENT_001], [DATE_003], etc.
echo.
explorer output
pause
