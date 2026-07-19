@echo off
title ZEMmacOS Build System v3.0.0
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===========================================================================
echo   ZEMmacOS v3.0.0 - Production Build Pipeline
echo   Publisher: WebSmithDigital
echo ===========================================================================
echo.

cd /d "%~dp0.."
set "PROJECT_DIR=%CD%"

REM ---------------- PREREQUISITES ----------------
echo [CHECK] Prerequisites...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Python not found in PATH. Please install Python 3.11+.
    exit /b 1
)

where pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
)

REM ---------------- CLEAN ----------------
echo.
echo [1/6] Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "D:\Software Installer\ZEMmacOS" rmdir /s /q "D:\Software Installer\ZEMmacOS"
echo [OK] Clean complete

REM ---------------- BUILD EXE ----------------
echo.
echo [2/6] Building EXE with PyInstaller (production mode)...
echo.
echo Using spec: spec\ZEMmacOS.spec
echo Config: config\config.json (no license key bundled)
echo.

pyinstaller spec\ZEMmacOS.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] PyInstaller build failed.
    exit /b 1
)
echo [OK] EXE build complete

REM ---------------- VERIFY BUILD ----------------
echo.
echo [3/6] Verifying build output...
if exist "dist\ZEMmacOS.exe" (
    echo [OK] Main executable: dist\ZEMmacOS.exe
) else (
    echo [WARN] Single EXE mode not used, checking dist\ZEMmacOS\ folder...
    if exist "dist\ZEMmacOS\ZEMmacOS.exe" (
        echo [OK] Main executable: dist\ZEMmacOS\ZEMmacOS.exe
    ) else (
        echo [FAIL] ZEMmacOS.exe not found in dist\
        echo       Build may have failed silently.
        dir dist\
        exit /b 1
    )
)

REM ---------------- VERIFY LICENSE NOT BUNDLED ----------------
echo.
echo [4/6] Verifying no license data bundled...
if exist "config\config.json" (
    findstr /C:"license_key" config\config.json | findstr /C:"\w\{4\}-\w\{4\}" >nul
    if !ERRORLEVEL! EQU 0 (
        echo [WARN] License key detected in config.json! This should be empty for production.
    ) else (
        echo [OK] config.json contains no bundled license key
    )
) else (
    echo [WARN] config.json not found at expected path
)

REM ---------------- BUILD INSTALLER ----------------
echo.
echo [5/6] Building installer package...
set "ISS_PATH=%PROJECT_DIR%\config\installer.iss"

where iscc >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    cd config
    iscc installer.iss
    cd %PROJECT_DIR%
    if exist "D:\Software Installer\ZEMmacOS\ZEMmacOS_Setup.exe" (
        echo [OK] Installer created successfully
    ) else (
        echo [WARN] Installer may not have been created
    )
) else (
    echo [WARN] Inno Setup compiler (iscc) not found.
    echo       Install Inno Setup from: https://jrsoftware.org/isdl.php
    echo       Then run manually: iscc config\installer.iss
)

REM ---------------- FINAL VERIFICATION ----------------
echo.
echo [6/6] Final verification...
echo.

if exist "dist\ZEMmacOS.exe" (
    echo  Executable: dist\ZEMmacOS.exe
) else if exist "dist\ZEMmacOS\ZEMmacOS.exe" (
    echo  Executable: dist\ZEMmacOS\ZEMmacOS.exe
)

if exist "D:\Software Installer\ZEMmacOS\ZEMmacOS_Setup.exe" (
    echo  Installer: D:\Software Installer\ZEMmacOS\ZEMmacOS_Setup.exe
)

echo.
echo ===========================================================================
echo   BUILD SUCCESSFUL
echo   ZEMmacOS v3.0.0 - Production
echo   WebSmithDigital
echo ===========================================================================
echo.

pause
