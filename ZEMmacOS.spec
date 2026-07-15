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
        # License SDK (entire package with config/assets)
        ('SDKToolkit_prod_zemmacos', 'SDKToolkit_prod_zemmacos'),
    ],
    # CRITICAL: Hidden imports for PyInstaller to include these modules
    hiddenimports=[
        # Core dependencies
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
        'safe_console',
        'logger',
        'gib_macos_wrapper',
        'idm_downloader',
        'cleaner',
        'main_ui',
        'settings_ui',
        'themes',
        'modern_widgets',
        'gibMacOS',
        # SDK modules
        'SDKToolkit_prod_zemmacos',
        'SDKToolkit_prod_zemmacos.client',
        'SDKToolkit_prod_zemmacos.crypto',
        'SDKToolkit_prod_zemmacos.hardware',
        'SDKToolkit_prod_zemmacos.cache',
        'SDKToolkit_prod_zemmacos.license_engine',
        'SDKToolkit_prod_zemmacos.welcome',
        'SDKToolkit_prod_zemmacos.activation',
        'SDKToolkit_prod_zemmacos.renewal',
        'SDKToolkit_prod_zemmacos.device_replace',
        'SDKToolkit_prod_zemmacos.widgets',
        # Scripts subfolder modules
        'Scripts.run',
        'Scripts.utils',
        'Scripts.plist',
        'Scripts.disk',
        'Scripts.diskwin',
        'Scripts.downloader',
    ] + collect_submodules('Scripts'),
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