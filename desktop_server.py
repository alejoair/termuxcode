#!/usr/bin/env python3
"""Entry point for the desktop sidecar - runs only the WebSocket server."""

import asyncio
import sys

from termuxcode.ws_server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
