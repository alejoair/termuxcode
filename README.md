# Claude Code Mobile

Proyecto para convertir PWA en App Android + Servidor WebSocket para Claude.

## Estructura

```
├── android-project/      # App Android (WebView)
│   └── app/src/main/assets/  # HTML/JS/CSS
├── claude_code_mobile/  # Servidor WebSocket Python
│   ├── cli.py           # Comando: ccm
│   ├── ws_server.py     # WebSocket (puerto 8769)
│   ├── serve.py         # HTTP (puerto 8000)
│   └── message_converter.py
└── static/              # Archivos web compartidos
    ├── index.html
    ├── app.js
    └── manifest.json
```

## Instalación

### Python (WebSocket Server)

```bash
pip install -e .
ccm  # Inicia servidores
```

### Android App

Ver docs/bubblewrap-termux-manual.md para instrucciones completas.

## Flujo de Desarrollo

1. Editar archivos en `static/` o `android-project/`
2. `git push` → GitHub Actions compila APK automáticamente
3. Descargar APK desde GitHub Actions

## Uso

1. Ejecutar `ccm` en Termux
2. Abrir http://localhost:8000/chat en el navegador
3. La app Android también puede cargar estos archivos

## Comandos

```bash
ccm           # HTTP + WebSocket
ccm --ws      # Solo WebSocket
ccm --http    # Solo HTTP
```
