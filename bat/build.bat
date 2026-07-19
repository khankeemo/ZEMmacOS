@echo off
title ZEMmacOS Build System
echo =====================================
echo   ZEMmacOS BUILD STARTING...
echo =====================================
cd /d "%~dp0.."

REM ---------------- CLEAN OLD BUILD ----------------
echo.
echo [1/5] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo ✓ Clean complete

REM ---------------- BUILD EXE ----------------
echo.
echo [2/5] Building EXE with PyInstaller...
pyinstaller spec\ZEMmacOS.spec

REM ---------------- VERIFY BUILD ----------------
echo.
echo [3/5] Verifying build...
if not exist dist\ZEMmacOS.exe (
    echo.
    echo ❌ ERROR: EXE not created!
    pause
    exit /b 1
)
echo ✓ EXE created successfully

REM ---------------- BUILD INSTALLER ----------------
echo.
echo [4/5] Building installer package...
where iscc >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    iscc installer.iss
) else (
    echo WARNING: Inno Setup compiler not found. Installer build step skipped.
    echo       Install Inno Setup or run installer manually with installer.iss
)

REM ---------------- FINAL VERIFICATION ----------------
echo.
echo [5/5] Final verification...
echo.
echo Files in dist\:
dir dist\
echo.
echo =====================================
echo   BUILD SUCCESSFUL ✅
echo =====================================
echo.
echo Output folder: C:\ZEMmacOS\dist
echo.
echo Installer output folder: C:\ZEMmacOS\installer_output
pause