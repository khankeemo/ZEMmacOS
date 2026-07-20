# -*- mode: python ; coding: utf-8 -*-
# ZEMmacOS - PyInstaller Specification File (Production Build)
# Purpose: Build Windows EXE for macOS Downloader App

import os
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd(), '..')) if '__file__' in dir() else os.getcwd()

# ============================================================================
# ANALYSIS - Collect all dependencies
# ============================================================================
a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'py')],
    binaries=[],
    datas=[
        # Project config (NO license_key bundled)
        (os.path.join(PROJECT_ROOT, 'config', 'config.json'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'project_manifest.json'), 'config'),
        # License agreement, terms, privacy for installer pages
        (os.path.join(PROJECT_ROOT, 'config', 'license_agreement.txt'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'terms_of_use.txt'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'privacy_policy.txt'), 'config'),
        # Public images
        (os.path.join(PROJECT_ROOT, 'public', 'images'), 'public/images'),
        # Help files
        (os.path.join(PROJECT_ROOT, 'help'), 'help'),
        # License SDK (entire package with config/assets)
        (os.path.join(PROJECT_ROOT, 'WSD_SDKToolkit_ZEMMACOS'), 'WSD_SDKToolkit_ZEMMACOS'),
    ],
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
        'WSD_SDKToolkit_ZEMMACOS',
        'WSD_SDKToolkit_ZEMMACOS.client',
        'WSD_SDKToolkit_ZEMMACOS.crypto',
        'WSD_SDKToolkit_ZEMMACOS.hardware',
        'WSD_SDKToolkit_ZEMMACOS.cache',
        'WSD_SDKToolkit_ZEMMACOS.license_engine',
        'WSD_SDKToolkit_ZEMMACOS.welcome',
        'WSD_SDKToolkit_ZEMMACOS.activation',
        'WSD_SDKToolkit_ZEMMACOS.renewal',
        'WSD_SDKToolkit_ZEMMACOS.device_replace',
        'WSD_SDKToolkit_ZEMMACOS.widgets',
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
    excludes=[
        # Remove development/test tools
        'unittest',
        'test',
        'pdb',
        'pydevd',
        'pytest',
        # Remove unused UI toolkits
        'tkinter.test',
        'tkinter.tix',
        'tkinter.dnd',
    ],
    noarchive=False,
    optimize=2,
)

# ============================================================================
# PYZ - Compressed Python archive
# ============================================================================
pyz = PYZ(a.pure, a.zipped_data)

# ============================================================================
# EXE - Executable output (production: no console, stripped)
# ============================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZEMmacOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(PROJECT_ROOT, 'public', 'images', 'logo.ico')],
)

# ============================================================================
# COLLECT - Bundle all files into dist/
# ============================================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZEMmacOS',
)
