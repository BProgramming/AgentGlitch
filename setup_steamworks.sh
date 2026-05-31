#!/usr/bin/env bash
# setup_steamworks.sh
# -------------------
# Clones the latest SteamworksPy from GitHub, compiles it against the
# Steamworks SDK 1.62, and installs everything into ./steamworks/.
#
# Run from: /brent/Documents/AgentGlitch
# Usage:    ./setup_steamworks.sh <path-to-steamworks-sdk-1.62>
#
# Example:  ./setup_steamworks.sh ~/Downloads/steamworks_sdk_162
#
# Run this script once on each platform you want to support (Linux, macOS).
# For Windows, see the printed instructions at the end — that must be done
# on a Windows machine using the .bat file from the cloned repo.

set -e

# ── Colours for output ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[*]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Arguments ─────────────────────────────────────────────────────────────────
SDK_PATH="${1}"
[ -z "${SDK_PATH}" ] && error "Please provide the path to the Steamworks SDK 1.62.\n    Usage: $0 <path-to-sdk>"
[ ! -d "${SDK_PATH}" ] && error "SDK path '${SDK_PATH}' does not exist."

# ── Paths ─────────────────────────────────────────────────────────────────────
GAME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="${GAME_DIR}/tmp"
REPO_DIR="${TMP_DIR}/steamworkspy"
BUILD_DIR="${REPO_DIR}/library"
OUT_DIR="${GAME_DIR}/steamworks"

# ── Detect platform ───────────────────────────────────────────────────────────
PLATFORM="$(uname -s)"
case "${PLATFORM}" in
    Linux*)  PLATFORM="linux"  ;;
    Darwin*) PLATFORM="macos"  ;;
    *) error "Unsupported platform '${PLATFORM}'. For Windows, see instructions below." ;;
esac
info "Platform: ${PLATFORM}"

# ── Check dependencies ────────────────────────────────────────────────────────
command -v git  >/dev/null 2>&1 || error "'git' is not installed."
command -v g++  >/dev/null 2>&1 || error "'g++' is not installed. On Linux: sudo apt install build-essential"

# ── Locate SDK files ──────────────────────────────────────────────────────────
SDK_HEADERS="${SDK_PATH}/public/steam"
[ ! -d "${SDK_HEADERS}" ] && error "Could not find SDK headers at '${SDK_HEADERS}'.\n    Make sure you're pointing at the SDK root (the folder containing 'public/')."

if [ "${PLATFORM}" = "linux" ]; then
    SDK_LIB_SRC="${SDK_PATH}/redistributable_bin/linux64/libsteam_api.so"
    SDK_LIB_NAME="libsteam_api.so"
    BINARY_NAME="SteamworksPy.so"
elif [ "${PLATFORM}" = "macos" ]; then
    SDK_LIB_SRC="${SDK_PATH}/redistributable_bin/osx/libsteam_api.dylib"
    SDK_LIB_NAME="libsteam_api.dylib"
    BINARY_NAME="SteamworksPy.dylib"
fi

[ ! -f "${SDK_LIB_SRC}" ] && error "Could not find SDK library at '${SDK_LIB_SRC}'."
info "SDK headers: ${SDK_HEADERS}"
info "SDK library: ${SDK_LIB_SRC}"

# ── Create temp directory ─────────────────────────────────────────────────────
info "Creating temporary build directory..."
mkdir -p "${TMP_DIR}"

# ── Clone SteamworksPy ────────────────────────────────────────────────────────
info "Cloning latest SteamworksPy from GitHub..."
git clone --depth=1 https://github.com/philippj/SteamworksPy.git "${REPO_DIR}"

# ── Prepare build directory ───────────────────────────────────────────────────
info "Copying SDK headers into build directory..."
mkdir -p "${BUILD_DIR}/sdk/steam"
cp -r "${SDK_HEADERS}/." "${BUILD_DIR}/sdk/steam/"

info "Copying ${SDK_LIB_NAME} into build directory..."
cp "${SDK_LIB_SRC}" "${BUILD_DIR}/${SDK_LIB_NAME}"

# On macOS the linker flag is -lsteam_api, which looks for libsteam_api.dylib.
# Also create a .so symlink in case anything looks for that name.
if [ "${PLATFORM}" = "macos" ]; then
    ln -sf "libsteam_api.dylib" "${BUILD_DIR}/libsteam_api.so"
fi

# ── Compile ───────────────────────────────────────────────────────────────────
info "Compiling ${BINARY_NAME}..."
cd "${BUILD_DIR}"

if [ "${PLATFORM}" = "linux" ]; then
    g++ -std=c++11 \
        -o "${BINARY_NAME}" \
        -shared -fPIC \
        SteamworksPy.cpp \
        -lsteam_api -L.

elif [ "${PLATFORM}" = "macos" ]; then
    g++ -std=c++11 \
        -o "${BINARY_NAME}" \
        -dynamiclib \
        -install_name @rpath/"${BINARY_NAME}" \
        SteamworksPy.cpp \
        -lsteam_api -L.
fi

info "Compiled successfully: ${BUILD_DIR}/${BINARY_NAME}"

# ── Install into ./steamworks/ ────────────────────────────────────────────────
info "Installing into ${OUT_DIR}/ ..."
mkdir -p "${OUT_DIR}"

# Copy the Python package files from the freshly cloned repo, preserving
# any platform binaries that may already be there (e.g. Windows DLLs from
# a previous build on a Windows machine).
info "Copying Python package..."
cp -r "${REPO_DIR}/steamworks/." "${OUT_DIR}/"

# Copy the compiled binary and runtime library.
info "Copying ${BINARY_NAME} and ${SDK_LIB_NAME}..."
cp "${BUILD_DIR}/${BINARY_NAME}" "${OUT_DIR}/${BINARY_NAME}"
cp "${BUILD_DIR}/${SDK_LIB_NAME}" "${OUT_DIR}/${SDK_LIB_NAME}"

# ── Clean up ──────────────────────────────────────────────────────────────────
info "Cleaning up temporary directory..."
cd "${GAME_DIR}"
rm -rf "${TMP_DIR}"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
info "Done. The following files are now in ${OUT_DIR}/:"
ls "${OUT_DIR}"

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  WINDOWS — build must be done on your Windows PC${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. On your Windows PC, download Steamworks SDK 1.62 and SteamworksPy:"
echo "       git clone https://github.com/philippj/SteamworksPy.git"
echo ""
echo "  2. Copy from the SDK into the repo:"
echo "       SDK\\public\\steam\\            → SteamworksPy\\library\\sdk\\steam\\"
echo "       SDK\\redistributable_bin\\win64\\steam_api64.dll  → SteamworksPy\\library\\sdk\\redist\\"
echo "       SDK\\redistributable_bin\\win64\\steam_api64.lib  → SteamworksPy\\library\\sdk\\redist\\"
echo ""
echo "  3. Open a Native Tools Command Prompt for VS 2022 and run:"
echo "       cd SteamworksPy"
echo "       build_win_64.bat 2022"
echo ""
echo "  4. Copy these files into your game's steamworks\\ folder:"
echo "       SteamworksPy\\redist\\windows\\SteamworksPy64.dll"
echo "       SDK\\redistributable_bin\\win64\\steam_api64.dll"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
