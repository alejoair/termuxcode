# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building the termuxcode WebSocket server sidecar."""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['termuxcode/desktop_server.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'termuxcode',
        'termuxcode.ws_server',
        'termuxcode.ws_config',
        'termuxcode.message_converter',
        'termuxcode.connection',
        'termuxcode.connection.base',
        'termuxcode.connection.sdk_client',
        'termuxcode.connection.sender',
        'termuxcode.connection.message_processor',
        'termuxcode.connection.ask_handler',
        'termuxcode.connection.tool_approval_handler',
        'websockets',
        'claude_agent_sdk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='termuxcode-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
