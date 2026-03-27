#!/usr/bin/env python3
"""Generate placeholder icons for Tauri from the existing PWA icon."""

import shutil
from pathlib import Path

# Paths
ROOT = Path(__file__).parent.parent
ICONS_DIR = ROOT / "src-tauri" / "icons"
SOURCE_ICON = ROOT / "static" / "icon-512.png"

ICONS_DIR.mkdir(parents=True, exist_ok=True)

# For CI, we just copy the source icon to all required sizes
# In production, you'd resize properly with Pillow
required = [
    "32x32.png",
    "128x128.png",
    "128x128@2x.png",
    "icon.png",
]

for name in required:
    shutil.copy2(SOURCE_ICON, ICONS_DIR / name)
    print(f"  Created {name}")

# For .ico and .icns we also copy the PNG (Tauri CLI handles conversion in CI)
shutil.copy2(SOURCE_ICON, ICONS_DIR / "icon.ico")
shutil.copy2(SOURCE_ICON, ICONS_DIR / "icon.icns")
print("  Created icon.ico and icon.icns (placeholders)")
print("Done! Icons are in src-tauri/icons/")
