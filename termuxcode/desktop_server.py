#!/usr/bin/env python3
"""Entry point for the desktop sidecar - runs only the WebSocket server."""

import asyncio
import sys

# En Windows, patchear subprocess para que no abra ventanas de consola
if sys.platform == "win32":
    import subprocess
    _original_popen_init = subprocess.Popen.__init__

    def _no_window_popen_init(self, *args, **kwargs):
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW
        _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _no_window_popen_init

from termuxcode.ws_server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
