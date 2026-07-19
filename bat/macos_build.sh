#!/bin/bash
#=============================================================================
# ZEMmacOS v3.0.0 - macOS Build Script
# Targets: .app Bundle, .dmg, .pkg
# Publisher: WebSmithDigital
#=============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="3.0.0"
APP_NAME="ZEMmacOS"
BUNDLE_ID="com.websmithdigital.zemmacos"
PYTHON="${PYTHON:-python3}"

echo "==========================================================================="
echo "  ZEMmacOS v${VERSION} - macOS Build"
echo "  Targets: Universal Binary (Intel + Apple Silicon)"
echo "  Publisher: WebSmithDigital"
echo "==========================================================================="
echo ""

cd "$PROJECT_DIR"

# ---- Prerequisites ----
echo "[CHECK] Prerequisites..."
command -v $PYTHON >/dev/null 2>&1 || { echo "[FAIL] Python not found"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "[FAIL] pip3 not found"; exit 1; }
command -v pyinstaller >/dev/null 2>&1 || { pip3 install pyinstaller; }

# ---- Clean ----
echo ""
echo "[1/6] Cleaning old builds..."
rm -rf build dist installer_output

# ---- Dependencies ----
echo ""
echo "[2/6] Installing dependencies..."
pip3 install -r requirements.txt --quiet

# ---- Verify no dev license ----
echo ""
echo "[3/6] Verifying no bundled license..."
if grep -qE '[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}' config/config.json 2>/dev/null; then
    echo "[FAIL] License key found in config.json! Remove before production build."
    exit 1
fi
echo "[OK] No bundled license key"

# ---- Build for macOS (universal2) ----
echo ""
echo "[4/6] Building for macOS (Universal Binary)..."

# Create a macOS-specific PyInstaller spec for universal2
cat > "spec/ZEMmacOS_macos.spec" << SPECEOF
# -*- mode: python ; coding: utf-8 -*-
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'py')],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'config', 'config.json'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'project_manifest.json'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'license_agreement.txt'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'terms_of_use.txt'), 'config'),
        (os.path.join(PROJECT_ROOT, 'config', 'privacy_policy.txt'), 'config'),
        (os.path.join(PROJECT_ROOT, 'public', 'images'), 'public/images'),
        (os.path.join(PROJECT_ROOT, 'help'), 'help'),
        (os.path.join(PROJECT_ROOT, 'WSD_SDKToolkit_ZEMMACOS'), 'WSD_SDKToolkit_ZEMMACOS'),
    ],
    hiddenimports=[
        'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
        'safe_console', 'logger', 'gib_macos_wrapper', 'idm_downloader',
        'cleaner', 'main_ui', 'settings_ui', 'themes', 'modern_widgets', 'gibMacOS',
        'WSD_SDKToolkit_ZEMMACOS', 'WSD_SDKToolkit_ZEMMACOS.client',
        'WSD_SDKToolkit_ZEMMACOS.crypto', 'WSD_SDKToolkit_ZEMMACOS.hardware',
        'WSD_SDKToolkit_ZEMMACOS.cache', 'WSD_SDKToolkit_ZEMMACOS.license_engine',
        'WSD_SDKToolkit_ZEMMACOS.welcome', 'WSD_SDKToolkit_ZEMMACOS.activation',
        'WSD_SDKToolkit_ZEMMACOS.renewal', 'WSD_SDKToolkit_ZEMMACOS.device_replace',
        'WSD_SDKToolkit_ZEMMACOS.widgets',
        'Scripts.run', 'Scripts.utils', 'Scripts.plist', 'Scripts.disk',
    ],
    excludes=['unittest', 'test', 'pdb', 'pytest', 'tkinter.test'],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data)

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

app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ZEMmacOS.app',
    icon=None,
    bundle_identifier='com.websmithdigital.zemmacos',
    info_plist={
        'CFBundleShortVersionString': '$VERSION',
        'CFBundleVersion': '$VERSION',
        'CFBundleName': 'ZEMmacOS',
        'CFBundleDisplayName': 'ZEMmacOS',
        'CFBundleIdentifier': 'com.websmithdigital.zemmacos',
        'NSHumanReadableCopyright': 'Copyright © 2026 WebSmithDigital',
        'LSMinimumSystemVersion': '11.0',
    },
)
SPECEOF

$PYTHON -m PyInstaller "spec/ZEMmacOS_macos.spec" --noconfirm

if [ ! -d "dist/ZEMmacOS.app" ]; then
    echo "[FAIL] .app bundle not created"
    exit 1
fi
echo "[OK] macOS app bundle created"

# ---- Sign the app bundle (if codesign available) ----
echo ""
echo "      Signing application bundle..."
if command -v codesign >/dev/null 2>&1; then
    codesign --deep --force --verify --verbose --sign "Developer ID Application" "dist/ZEMmacOS.app" 2>/dev/null || \
    echo "      [WARN] Code signing not configured. Skipping."
else
    echo "      [SKIP] codesign not available"
fi

# ---- Create DMG ----
echo ""
echo "[5/6] Creating DMG image..."
mkdir -p installer_output

DMG_PATH="installer_output/ZEMmacOS_v${VERSION}.dmg"
DMG_TMP="installer_output/ZEMmacOS_tmp.dmg"
VOLUME_NAME="ZEMmacOS ${VERSION}"

# Create temporary DMG
if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
        --volname "$VOLUME_NAME" \
        --volicon "public/images/logo.ico" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "ZEMmacOS.app" 175 190 \
        --hide-extension "ZEMmacOS.app" \
        --app-drop-link 425 190 \
        "$DMG_PATH" \
        "dist/ZEMmacOS.app"
    echo "[OK] DMG created with create-dmg"
else
    # Fallback: manual DMG creation with hdiutil
    echo "      create-dmg not found. Using hdiutil..."
    mkdir -p "dist/dmg_build"
    cp -r "dist/ZEMmacOS.app" "dist/dmg_build/"
    ln -s "/Applications" "dist/dmg_build/Applications"
    hdiutil create -volname "$VOLUME_NAME" -srcfolder "dist/dmg_build" -ov -format UDZO "$DMG_PATH"
    rm -rf "dist/dmg_build"
    echo "[OK] DMG created with hdiutil"
fi

# ---- Create PKG ----
echo ""
echo "      Creating PKG installer..."

PKG_PATH="installer_output/ZEMmacOS_v${VERSION}.pkg"

if command -v pkgbuild >/dev/null 2>&1; then
    # Create component package
    pkgbuild \
        --root "dist/ZEMmacOS.app" \
        --identifier "$BUNDLE_ID" \
        --version "$VERSION" \
        --install-location "/Applications/ZEMmacOS.app" \
        --sign "Developer ID Installer" \
        "$PKG_PATH" 2>/dev/null || \
    pkgbuild \
        --root "dist/ZEMmacOS.app" \
        --identifier "$BUNDLE_ID" \
        --version "$VERSION" \
        --install-location "/Applications/ZEMmacOS.app" \
        "$PKG_PATH"
    echo "[OK] PKG installer created"
else
    echo "[WARN] pkgbuild not found. PKG creation skipped."
    echo "       Install Command Line Tools for Xcode: xcode-select --install"
fi

# ---- Generate Checksums ----
echo ""
echo "[6/6] Generating checksums..."

cd installer_output
if [ -f "$(basename "$DMG_PATH")" ]; then
    shasum -a 256 "$(basename "$DMG_PATH")" > "$(basename "$DMG_PATH").sha256"
    echo "[OK] SHA256 for DMG"
fi
if [ -f "$(basename "$PKG_PATH")" ]; then
    shasum -a 256 "$(basename "$PKG_PATH")" > "$(basename "$PKG_PATH").sha256"
    echo "[OK] SHA256 for PKG"
fi
cd "$PROJECT_DIR"

# ---- Cleanup temp spec ----
rm -f "spec/ZEMmacOS_macos.spec"

echo ""
echo "==========================================================================="
echo "  BUILD COMPLETE - ZEMmacOS v${VERSION} macOS"
echo "==========================================================================="
echo ""
echo "  Output:"
ls -lh installer_output/ 2>/dev/null
echo ""
echo "  Verification:"
echo "    1. Test on clean macOS (Intel + Apple Silicon)"
echo "    2. Verify no pre-activated license"
echo "    3. Test drag-and-drop installation from DMG"
echo "    4. Test PKG installation"
echo "    5. Verify Gatekeeper acceptance"
echo "    6. Test trial and activation flows"
echo ""

# ---- Notarization (if configured) ----
echo "  Notarization (for distribution outside Mac App Store):"
echo "    xcrun notarytool submit installer_output/ZEMmacOS_v${VERSION}.dmg"
echo "        --apple-id your@email.com"
echo "        --team-id YOUR_TEAM_ID"
echo "        --password @keychain:AC_PASSWORD"
echo "        --wait"
echo ""
echo "    xcrun stapler staple installer_output/ZEMmacOS_v${VERSION}.dmg"
echo ""
