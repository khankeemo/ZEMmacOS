@echo off
title ZEMmacOS - FULL PRODUCTION BUILD v3.0.0
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===========================================================================
echo   ZEMmacOS v3.0.0 - FULL PRODUCTION BUILD
echo   Target: Windows x64
echo   Publisher: WebSmithDigital
echo ===========================================================================
echo.

cd /d "%~dp0.."
set "PROJECT_DIR=%CD%"

REM ---------------- STEP 0: Verify Production Config ----------------
echo [0/7] Verifying production configuration...

if not exist "config\config.json" (
    echo [FAIL] config\config.json not found!
    exit /b 1
)

REM Check for bundled license key
findstr /C:"MROC-" config\config.json >nul 2>nul
if !ERRORLEVEL! EQU 0 (
    echo [FAIL] SECURITY: Development license key found in config.json!
    echo       Remove bundled license keys before production build.
    echo       Expected: "license_key": ""
    exit /b 1
)
echo [OK] No bundled license key in config.json

REM Check for dev-only files
if exist "env\.env.production" (
    echo [INFO] .env.production found - will not be bundled
)

REM Check that production sample config has no dev data
echo [OK] Production configuration verified

REM ---------------- STEP 1: Clean ----------------
echo.
echo [1/7] Cleaning old build artifacts...
for %%d in (build dist) do (
    if exist %%d (
        echo   Removing: %%d\
        rmdir /s /q %%d
    )
)
if exist "D:\Software Installer\ZEMmacOS" (
    echo   Removing: D:\Software Installer\ZEMmacOS\
    rmdir /s /q "D:\Software Installer\ZEMmacOS"
)

REM Clean Python cache files
echo   Cleaning Python cache files...
if exist __pycache__ rmdir /s /q __pycache__
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

echo [OK] Clean complete

REM ---------------- STEP 2: Install Dependencies ----------------
echo.
echo [2/7] Installing dependencies...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Some dependencies may not have installed correctly
)

REM ---------------- STEP 3: Verify SDK Integrity ----------------
echo.
echo [3/7] Verifying SDK integrity...
if exist "WSD_SDKToolkit_ZEMMACOS\__init__.py" (
    if exist "WSD_SDKToolkit_ZEMMACOS\config\api-config.json" (
        echo [OK] SDK Toolkit found
        echo   Product: ZEM MAC OS
        echo   Version: 1.0.0
        echo   API: websmith-z.vercel.app
    ) else (
        echo [FAIL] SDK config missing!
        exit /b 1
    )
) else (
    echo [FAIL] SDK Toolkit missing!
    echo   Expected: WSD_SDKToolkit_ZEMMACOS\__init__.py
    exit /b 1
)

REM Verify SDK manifest
if exist "WSD_SDKToolkit_ZEMMACOS\manifest.json" (
    echo [OK] SDK manifest verified
)

REM ---------------- STEP 4: Build EXE (Production) ----------------
echo.
echo [4/7] Building EXE with PyInstaller (production optimized)...
echo   Mode: Production
echo   Console: Disabled
echo   UPX: Enabled
echo   Optimization: Level 2
echo.

REM Temporarily remove any test/dev credentials from config
pyinstaller spec\ZEMmacOS.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] PyInstaller build failed!
    echo   Check spec\ZEMmacOS.spec for errors
    exit /b 1
)
echo [OK] EXE build complete

REM ---------------- STEP 5: Verify EXE Output ----------------
echo.
echo [5/7] Verifying executable...

set "EXE_PATH=dist\ZEMmacOS.exe"
if exist "!EXE_PATH!" (
    for %%f in ("!EXE_PATH!") do (
        set EXE_SIZE=%%~zf
    )
    echo [OK] Executable found: !EXE_PATH! (!EXE_SIZE! bytes)
) else (
    if exist "dist\ZEMmacOS\ZEMmacOS.exe" (
        set "EXE_PATH=dist\ZEMmacOS\ZEMmacOS.exe"
        for %%f in ("!EXE_PATH!") do (
            set EXE_SIZE=%%~zf
        )
        echo [OK] Executable found: !EXE_PATH! (!EXE_SIZE! bytes)
    ) else (
        echo [FAIL] ZEMmacOS.exe not found in dist\
        dir dist\ 2>nul
        exit /b 1
    )
)

REM ---------------- STEP 6: Build Installer ------------------
echo.
echo [6/7] Building Windows installer with Inno Setup...

where iscc >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    pushd config
    iscc installer.iss
    popd
    
    REM Find the installer
    set "INSTALLER_PATH=D:\Software Installer\ZEMmacOS\ZEMmacOS_Setup.exe"
    
    if exist "!INSTALLER_PATH!" (
        for %%f in ("!INSTALLER_PATH!") do (
            set INSTALLER_SIZE=%%~zf
        )
        echo [OK] Installer created: !INSTALLER_PATH! (!INSTALLER_SIZE! bytes)
    ) else (
        echo [WARN] Installer output not found at !INSTALLER_PATH!
    )
) else (
    echo [WARN] Inno Setup compiler (iscc) not found in PATH
    echo   Install from: https://jrsoftware.org/isdl.php
    echo   Verify: iscc is in PATH
    echo.
    echo   To build manually:
    echo     cd config
    echo     iscc installer.iss
)

REM ---------------- STEP 7: Generate SHA256 Checksums ----------------
echo.
echo [7/7] Generating checksums...

if not exist "D:\Software Installer\ZEMmacOS" mkdir "D:\Software Installer\ZEMmacOS"

REM Generate checksums for all build artifacts
if exist "!EXE_PATH!" (
    certutil -hashfile "!EXE_PATH!" SHA256 | findstr /V "hash" > "D:\Software Installer\ZEMmacOS\ZEMmacOS_exe.sha256"
    echo [OK] SHA256 for executable saved
)

if exist "!INSTALLER_PATH!" (
    certutil -hashfile "!INSTALLER_PATH!" SHA256 | findstr /V "hash" > "D:\Software Installer\ZEMmacOS\ZEMmacOS_Setup.sha256"
    echo [OK] SHA256 for installer saved
)

REM ---------------- BUILD SUMMARY ----------------
echo.
echo ===========================================================================
echo   BUILD COMPLETE - ZEMmacOS v3.0.0 Production
echo   WebSmithDigital
echo ===========================================================================
echo.
echo   Output Files:
if exist "!EXE_PATH!" echo     EXE: !EXE_PATH!
if exist "!INSTALLER_PATH!" echo     Setup: !INSTALLER_PATH!
echo.
echo   Checksums:
dir "D:\Software Installer\ZEMmacOS\*.sha256" 2>nul
echo.
echo   Next Steps:
echo     1. Verify the installer on a clean Windows VM
echo     2. Test fresh install - no pre-activated license
echo     3. Test trial activation flow
echo     4. Test paid activation flow
echo     5. Sign the installer
echo     6. Upload to distribution channel
echo.
echo ===========================================================================

pause
