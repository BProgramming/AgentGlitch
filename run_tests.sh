#!/usr/bin/env bash
# Run the Agent Glitch test suite headlessly.
#
#   ./run_tests.sh                 # everything
#   ./run_tests.sh -k trigger      # anything matching "trigger"
#   ./run_tests.sh -m "not slow"   # skip the slower render/playback tests
#   ./run_tests.sh --cov=.         # with a coverage report
#
# Any arguments are passed straight through to pytest.
set -euo pipefail

cd "$(dirname "$0")"

# The game needs Python 3.12+ (PEP 701 f-strings in SteamworksConnection.py).
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
    for candidate in python3.13 python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
                PYTHON="$candidate"
                break
            fi
        fi
    done
fi

if [[ -z "$PYTHON" ]]; then
    echo "No Python 3.12+ interpreter found. Set PYTHON=/path/to/python3.12" >&2
    exit 1
fi

# tests/conftest.py sets these too; exporting them here means an ad-hoc
# `python -c "import Engine"` behaves the same way.
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
export PYGAME_HIDE_SUPPORT_PROMPT=1

exec "$PYTHON" -m pytest "$@"
