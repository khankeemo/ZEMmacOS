# -*- mode: python ; coding: utf-8 -*-
# ZEMmacOS - PyInstaller Specification File
# Purpose: Build Windows EXE for macOS Downloader App

from PyInstaller.utils.hooks import collect_submodules

# ============================================================================
# ANALYSIS - Collect all dependencies
# ============================================================================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Project folders
        ('config.json', '.'),
        ('public/images', 'public/images'),
        ('help', 'help'),
        # WSD SDK - config and manifest
        ('ZEMmacOS/wsd_sdk/config', 'ZEMmacOS/wsd_sdk/config'),
        ('ZEMmacOS/wsd_sdk/manifest.json', 'ZEMmacOS/wsd_sdk/'),
    ],
    # CRITICAL: Hidden imports for PyInstaller to include these modules
    hiddenimports=[
        # Core dependencies
        'cryptography',
        'cryptography.fernet',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        # PIL/Pillow for images
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        # Project modules
        'usb_creator',
        'usb_creator_ui',
        'safe_console',
        'console_manager',
        'logger',
        'state_manager',
        'gib_macos_wrapper',
        'idm_downloader',
        'cleaner',
        'main_ui',
        'gibMacOS',
        # WSD SDK modules
        'wsd_sdk',
        'wsd_sdk.client',
        'wsd_sdk.license_engine',
        'wsd_sdk.hardware',
        'wsd_sdk.crypto',
        # Integration layer
        'integration.wsd_license',
        # Scripts subfolder modules
        'Scripts.run',
        'Scripts.utils',
        'Scripts.plist',
        'Scripts.disk',
        'Scripts.diskwin',
        'Scripts.downloader',
    ] + collect_submodules('Scripts'),  # Auto-collect all Scripts/*.py
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ============================================================================
# PYZ - Compressed Python archive
# ============================================================================
pyz = PYZ(a.pure, a.zipped_data)

# ============================================================================
# EXE - Executable output
# ============================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],  # No additional binaries
    name='ZEMmacOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging; set False for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['public\\images\\logo.ico'],  # App icon
)