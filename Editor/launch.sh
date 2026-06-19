#!/bin/bash
# Launch Agent Glitch Level Editor.
#
# Starts a local web server, opens the editor in Chrome, and shuts the
# server down again once you close that window — so double-clicking this
# doesn't leave a python process running in the background afterward.
#
# How the "wait for Chrome to close" part works: launching Chrome with a
# brand-new --user-data-dir (one this script owns, not your normal Chrome
# profile) makes Chrome start as its own standalone process rather than
# just opening a tab in whatever Chrome window you already have open — so
# the shell command genuinely blocks until that specific window is closed.
# As a safety net in case that ever isn't true on some Chrome version, this
# also polls the profile's lock file as a fallback signal.

EDITOR_DIR="/home/brent/Documents/AgentGlitch/Editor"
PORT=8765
URL="http://localhost:${PORT}/index.html"
PROFILE_DIR="/tmp/agent-glitch-editor-chrome-profile"

cd "$EDITOR_DIR" || {
    echo "Could not find editor folder at $EDITOR_DIR"
    read -p "Press Enter to close..."
    exit 1
}

# Find a Chrome-family browser. The editor needs Chrome or Edge specifically
# (Firefox doesn't support the File System Access API it relies on for
# opening and saving your project folder).
BROWSER=""
for candidate in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge microsoft-edge-stable; do
    if command -v "$candidate" > /dev/null 2>&1; then
        BROWSER="$candidate"
        break
    fi
done

if [ -z "$BROWSER" ]; then
    echo "Could not find Chrome, Chromium, or Edge installed."
    echo "This editor needs one of those installed to run."
    read -p "Press Enter to close..."
    exit 1
fi

# Reuse an already-running server on this port if one exists; otherwise
# start a fresh one in the background.
SERVER_STARTED_BY_US=0
if ! curl -s -o /dev/null "$URL" 2>/dev/null; then
    python3 -m http.server "$PORT" > /tmp/agent-glitch-editor-server.log 2>&1 &
    SERVER_PID=$!
    SERVER_STARTED_BY_US=1
    sleep 0.5
fi

mkdir -p "$PROFILE_DIR"

# This blocks until the Chrome window closes, because --user-data-dir points
# at a dedicated profile rather than your everyday one.
"$BROWSER" --new-window "$URL" --user-data-dir="$PROFILE_DIR" > /dev/null 2>&1

# Fallback safety net: if for some reason the line above returned instantly
# without actually blocking (e.g. a Chrome version that behaves differently
# than expected), wait until the profile's lock file is gone before
# tearing down the server — capped at 12 hours so this can never hang
# forever if something odd happens.
LOCK_FILE="$PROFILE_DIR/SingletonLock"
WAITED=0
while [ -e "$LOCK_FILE" ] || [ -L "$LOCK_FILE" ]; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ "$WAITED" -ge 43200 ]; then
        break
    fi
done

if [ "$SERVER_STARTED_BY_US" = "1" ]; then
    kill "$SERVER_PID" 2>/dev/null
fi
