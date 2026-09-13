"""Replaces the two ``Helpers`` functions that would otherwise end the test process.

``Helpers.handle_exception`` calls ``pygame.quit()``, writes a crash log, opens a Tk
message box and then ``sys.exit()``.  ``Helpers.display_text`` renders to the display
and spins in ``time.sleep`` loops for as long as the text takes to read.  Both are
called from deep inside ordinary code paths -- ``EntityFactory.build_level`` calls
``display_text`` once per row -- so a test suite cannot run with either in place.

Both replacements are installed on the ``Helpers`` module *before* any other game
module is imported, so modules that do ``from Helpers import handle_exception`` bind
the replacement rather than the original.  The originals stay reachable as
``Helpers.real_handle_exception`` / ``Helpers.real_display_text`` for the handful of
tests that want to drive the genuine article.

``handle_exception`` raises :class:`HandledError` rather than returning.  That is the
faithful choice: the real function never returns either, so any ``return None`` that
follows a ``handle_exception`` call in the game is dead code, and a stub that returned
would let tests assert on behaviour the game can never actually reach.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any


class HandledError(RuntimeError):
    """Raised in place of the ``sys.exit()`` inside ``Helpers.handle_exception``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DisplayTextCall:
    """One recorded ``display_text`` invocation."""

    __slots__ = ("output", "kwargs")

    def __init__(self, output: Any, kwargs: dict[str, Any]) -> None:
        self.output = output
        self.kwargs = kwargs

    @property
    def lines(self) -> list[str]:
        """``output`` normalised to a list, the way ``display_text`` normalises it."""
        if self.output is None:
            return []
        return list(self.output) if isinstance(self.output, list) else [self.output]

    @property
    def text(self) -> str:
        return "\n".join(str(line) for line in self.lines)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DisplayTextCall {self.text!r} {self.kwargs!r}>"


#: every ``display_text`` call made since the last :func:`reset`
display_text_calls: list[DisplayTextCall] = []

#: every message passed to ``handle_exception`` since the last :func:`reset`
handled_errors: list[str] = []


def _recording_handle_exception(msg: str) -> None:
    handled_errors.append(msg)
    raise HandledError(msg)


def _recording_display_text(output: Any, controller: Any = None, **kwargs: Any) -> None:
    display_text_calls.append(DisplayTextCall(output, kwargs))
    return None


def install(helpers: ModuleType) -> None:
    """Swap the two functions on the ``Helpers`` module.  Idempotent."""
    if not hasattr(helpers, "real_handle_exception"):
        helpers.real_handle_exception = helpers.handle_exception  # type: ignore[attr-defined]
        helpers.real_display_text     = helpers.display_text      # type: ignore[attr-defined]
    helpers.handle_exception = _recording_handle_exception  # type: ignore[assignment]
    helpers.display_text     = _recording_display_text      # type: ignore[assignment]


def reset() -> None:
    """Clear both recorders.  Called between tests by an autouse fixture."""
    display_text_calls.clear()
    handled_errors.clear()
