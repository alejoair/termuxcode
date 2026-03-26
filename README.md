# termuxcode

> **Claude Code client for Android/Termux** - Servidor WebSocket + App Android

[![PyPI version](https://img.shields.io/pypi/v/termuxcode.svg)](https://pypi.org/project/termuxcode/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Características

- 🚀 Servidor WebSocket para Claude Agent SDK
- 📱 App Android que carga desde `localhost:8000`
- 🔄 Actualizaciones vía GitHub Actions
- 📦 Disponible en PyPI como `termuxcode`

## Instalación

```bash
pip install termuxcode
```

## Uso

### Servidor WebSocket + HTTP

```bash
ccm
# Abre http://localhost:8000/chat
```

### Solo WebSocket

```bash
ccm --ws
```

### Solo HTTP

```bash
ccm --http
```

## App Android

1. Descargar desde [Releases](https://github.com/alejoair/termuxcode/releases)
2. Instalar APK
3. La app carga `http://localhost:8000/chat` automáticamente

## Estructura

```
├── termuxcode/         # Paquete Python
│   ├── cli.py          # Comando ccm
│   ├── ws_server.py    # WebSocket (puerto 8769)
│   ├── serve.py        # HTTP (puerto 8000)
│   └── ...
├── android-project/    # App Android
├── static/             # Archivos web (único lugar)
└── .github/workflows/ # GitHub Actions
```

## Desarrollo

### Publicar nueva versión

```bash
# 1. Actualizar versión en pyproject.toml
# 2. Crear tag y push
git tag v1.1.0
git push origin v1.1.0

# Esto crea:
# - Release en GitHub con APK
# - Paquete en PyPI
```

## Links

- [PyPI](https://pypi.org/project/termuxcode/)
- [GitHub](https://github.com/alejoair/termuxcode)
- [Releases](https://github.com/alejoair/termuxcode/releases)
