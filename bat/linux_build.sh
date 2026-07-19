#!/bin/bash
#=============================================================================
# ZEMmacOS v3.0.0 - Linux Build Script
# Targets: AppImage, .deb (Debian/Ubuntu)
# Publisher: WebSmithDigital
#=============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="3.0.0"
APP_NAME="ZEMmacOS"
PYTHON="${PYTHON:-python3}"

echo "==========================================================================="
echo "  ZEMmacOS v${VERSION} - Linux Build"
echo "  Publisher: WebSmithDigital"
echo "==========================================================================="
echo ""

cd "$PROJECT_DIR"

# ---- Prerequisites ----
echo "[CHECK] Prerequisites..."
command -v $PYTHON >/dev/null 2>&1 || { echo "[FAIL] Python not found"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "[FAIL] pip3 not found"; exit 1; }
command -v pyinstaller >/dev/null 2>&1 || { echo "[INFO] Installing PyInstaller..."; pip3 install pyinstaller; }

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

# ---- PyInstaller Build ----
echo ""
echo "[4/6] Building executable with PyInstaller..."
$PYTHON -m PyInstaller spec/ZEMmacOS.spec --noconfirm

if [ ! -f "dist/$APP_NAME" ] && [ ! -f "dist/$APP_NAME/$APP_NAME" ]; then
    echo "[FAIL] Build failed - executable not found"
    exit 1
fi
echo "[OK] Build complete"

# ---- AppImage Build ----
echo ""
echo "[5/6] Building AppImage..."

APPIMAGE_DIR="installer_output/appimage"
mkdir -p "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/bin"
mkdir -p "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/applications"
mkdir -p "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/$APP_NAME"

# Copy application files
if [ -d "dist/$APP_NAME" ]; then
    cp -r "dist/$APP_NAME/"* "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/$APP_NAME/"
    ln -s "../share/$APP_NAME/$APP_NAME" "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/bin/$APP_NAME"
elif [ -f "dist/$APP_NAME" ]; then
    cp "dist/$APP_NAME" "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/bin/"
fi

# AppRun script
cat > "$APPIMAGE_DIR/$APP_NAME.AppDir/AppRun" << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/ZEMmacOS"
APPRUN
chmod +x "$APPIMAGE_DIR/$APP_NAME.AppDir/AppRun"

# Desktop file
cat > "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/applications/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=ZEMmacOS
Comment=macOS Download Manager
Exec=$APP_NAME
Icon=$APP_NAME
Terminal=false
Categories=Utility;FileTransfer;Development;
Keywords=macOS;downloader;apple;installer;
DESKTOP

# Copy desktop file to AppDir root
cp "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/applications/$APP_NAME.desktop" "$APPIMAGE_DIR/$APP_NAME.AppDir/"

# Icon
if [ -f "public/images/logo.png" ]; then
    cp "public/images/logo.png" "$APPIMAGE_DIR/$APP_NAME.AppDir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    cp "public/images/logo.png" "$APPIMAGE_DIR/$APP_NAME.AppDir/$APP_NAME.png"
fi

# .desktop file with exec path
cat > "$APPIMAGE_DIR/$APP_NAME.AppDir/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=ZEMmacOS
Comment=macOS Download Manager
Exec=AppRun
Icon=$APP_NAME
Terminal=false
Categories=Utility;FileTransfer;Development;
DESKTOP

# Check for appimagetool
if command -v appimagetool >/dev/null 2>&1; then
    cd "$APPIMAGE_DIR"
    appimagetool "$APP_NAME.AppDir"
    echo "[OK] AppImage created"
    cd "$PROJECT_DIR"
else
    echo "[WARN] appimagetool not found. Install it from:"
    echo "       https://github.com/AppImage/AppImageKit/releases"
    echo ""
    echo "  Manual AppImage creation:"
    echo "    appimagetool installer_output/appimage/$APP_NAME.AppDir"
fi

# ---- Debian Package ----
echo ""
echo "      Building .deb package..."

DEB_DIR="installer_output/deb"
DEB_ROOT="$DEB_DIR/${APP_NAME}_${VERSION}_amd64"
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/usr/bin"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$DEB_ROOT/usr/share/doc/$APP_NAME"
mkdir -p "$DEB_ROOT/usr/share/$APP_NAME"

# Control file
cat > "$DEB_ROOT/DEBIAN/control" << CONTROL
Package: zemmacos
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.11), libc6 (>= 2.31)
Maintainer: WebSmithDigital <support@websmithdigital.com>
Description: ZEMmacOS - macOS Download Manager
 Download macOS installer files directly from Apple's servers.
 Features multithreaded downloading, catalog browser,
 and license management.
Homepage: https://www.websmithdigital.com
CONTROL

# Post-installation script
cat > "$DEB_ROOT/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

APP_NAME="ZEMmacOS"
APP_PATH="/usr/share/$APP_NAME"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

echo "$APP_NAME installed successfully."
echo "Run '$APP_NAME' from terminal or launch from application menu."
POSTINST
chmod +x "$DEB_ROOT/DEBIAN/postinst"

# Preremoval script
cat > "$DEB_ROOT/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
set -e
echo "Removing ZEMmacOS..."
PRERM
chmod +x "$DEB_ROOT/DEBIAN/prerm"

# Desktop file
cat > "$DEB_ROOT/usr/share/applications/zemmacos.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=ZEMmacOS
Comment=macOS Download Manager
Exec=/usr/share/ZEMmacOS/ZEMmacOS
Icon=zemmacos
Terminal=false
Categories=Utility;FileTransfer;Development;
Keywords=macOS;downloader;apple;installer;
DESKTOP

# Icon
if [ -f "public/images/logo.png" ]; then
    cp "public/images/logo.png" "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps/zemmacos.png"
fi

# Documentation
cp config/license_agreement.txt "$DEB_ROOT/usr/share/doc/$APP_NAME/copyright"
cp config/terms_of_use.txt "$DEB_ROOT/usr/share/doc/$APP_NAME/"
cp config/privacy_policy.txt "$DEB_ROOT/usr/share/doc/$APP_NAME/"

# Application binary
if [ -d "dist/$APP_NAME" ]; then
    cp -r "dist/$APP_NAME/"* "$DEB_ROOT/usr/share/$APP_NAME/"
elif [ -f "dist/$APP_NAME" ]; then
    cp "dist/$APP_NAME" "$DEB_ROOT/usr/share/$APP_NAME/"
fi

# Symlink in PATH
ln -sf "/usr/share/$APP_NAME/$APP_NAME" "$DEB_ROOT/usr/bin/zemmacos"

# Build .deb
dpkg-deb --build "$DEB_ROOT"
echo "[OK] .deb package created"

# ---- Cleanup ----
echo ""
echo "[6/6] Build complete!"
echo ""
echo "==========================================================================="
echo "  BUILD COMPLETE - ZEMmacOS v${VERSION} Linux"
echo "==========================================================================="
echo ""
echo "  Output:"
ls -lh installer_output/ 2>/dev/null
echo ""

# ---- Verification ----
echo "  Verification:"
echo "    1. Test on clean Linux system"
echo "    2. Verify no pre-activated license"
echo "    3. Test trial and activation flows"
echo "    4. Check AppImage runs on Ubuntu/Fedora"
echo "    5. Test dpkg -i package.deb"
echo ""
