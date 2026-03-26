# Claude Code Mobile - Servidor WebSocket

Servidor WebSocket para comunicarse con Claude Agent SDK.

## Instalación

```bash
pip install -e .
```

## Uso

```bash
# Iniciar todo (HTTP + WebSocket)
ccm

# Solo WebSocket
ccm --ws

# Solo HTTP  
ccm --http
```

## Archivos

- `cli.py` - Punto de entrada
- `ws_server.py` - Servidor WebSocket
- `ws_connection.py` - Manejo de conexiones
- `serve.py` - Servidor HTTP
- `message_converter.py` - Conversión de mensajes
