"""Servidor web personalizado con soporte para DPI alto"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

import aiohttp_jinja2
from aiohttp import web
from aiohttp import WSMsgType
from aiohttp.web_runner import GracefulExit
import jinja2

from rich.console import Console
from rich.logging import RichHandler
from rich.highlighter import RegexHighlighter

import textual_serve
from textual_serve.download_manager import DownloadManager
from textual_serve.app_service import AppService

log = logging.getLogger("termuxcode-web")


class LogHighlighter(RegexHighlighter):
    base_style = "repr."
    highlights = [
        r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
        r"(?P<path>\[.*?\])",
        r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
    ]


def to_int(value: str, default: int) -> int:
    """Convert to an integer, or return a default if that's not possible."""
    try:
        return int(value)
    except ValueError:
        return default


class WebServer:
    """Servidor web personalizado para termuxcode con soporte DPI alto."""

    def __init__(
        self,
        command: str,
        host: str = "0.0.0.0",
        port: int = 8000,
        title: str | None = None,
        public_url: str | None = None,
        font_size: int = 16,
        statics_path: str | os.PathLike = "./static",
        templates_path: str | os.PathLike = "./templates",
    ):
        self.command = command
        self.host = host
        self.port = port
        self.title = title or command
        self.font_size = font_size
        self.debug = False

        if public_url is None:
            if self.port == 80:
                self.public_url = f"http://{self.host}"
            elif self.port == 443:
                self.public_url = f"https://{self.host}"
            else:
                self.public_url = f"http://{self.host}:{self.port}"
        else:
            self.public_url = public_url

        # Usar paths customizados en lugar de los de textual_serve
        base_path = Path(__file__).parent.resolve().absolute()
        self.statics_path = base_path / "web" / "static"  # Usar nuestros estáticos
        self.templates_path = base_path / "web" / "templates"  # Usar nuestros templates
        self.console = Console()
        self.download_manager = DownloadManager()

    def initialize_logging(self) -> None:
        """Initialize logging."""
        FORMAT = "%(message)s"
        logging.basicConfig(
            level="DEBUG" if self.debug else "INFO",
            format=FORMAT,
            datefmt="[%X]",
            handlers=[
                RichHandler(
                    show_path=False,
                    show_time=False,
                    rich_tracebacks=True,
                    tracebacks_show_locals=True,
                    highlighter=LogHighlighter(),
                    console=self.console,
                )
            ],
        )

    def request_exit(self) -> None:
        """Gracefully exit the app."""
        raise GracefulExit()

    async def _make_app(self) -> web.Application:
        """Make the aiohttp web Application."""
        app = web.Application()

        aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(self.templates_path))

        ROUTES = [
            web.get("/", self.handle_index, name="index"),
            web.get("/ws", self.handle_websocket, name="websocket"),
            web.get("/download/{key}", self.handle_download, name="download"),
            web.static("/static", self.statics_path, show_index=True, name="static"),
        ]
        app.add_routes(ROUTES)

        app.on_startup.append(self.on_startup)
        app.on_shutdown.append(self.on_shutdown)
        return app

    async def handle_download(self, request: web.Request) -> web.StreamResponse:
        """Handle a download request."""
        key = request.match_info["key"]

        try:
            download_meta = await self.download_manager.get_download_metadata(key)
        except KeyError:
            raise web.HTTPNotFound(text=f"Download with key {key!r} not found")

        response = web.StreamResponse()
        mime_type = download_meta.mime_type

        content_type = mime_type
        if download_meta.encoding:
            content_type += f"; charset={download_meta.encoding}"

        response.headers["Content-Type"] = content_type
        disposition = (
            "inline" if download_meta.open_method == "browser" else "attachment"
        )
        response.headers["Content-Disposition"] = (
            f"{disposition}; filename={download_meta.file_name}"
        )

        await response.prepare(request)

        async for chunk in self.download_manager.download(key):
            await response.write(chunk)

        await response.write_eof()
        return response

    async def on_shutdown(self, app: web.Application) -> None:
        """Called on shutdown."""
        pass

    async def on_startup(self, app: web.Application) -> None:
        """Called on startup."""
        self.console.print(f"[bold magenta]termuxcode[/bold magenta] Web Server")
        self.console.print(f"Serving {self.command!r} on {self.public_url}")
        self.console.print(f"[cyan]Font size: {self.font_size}px[/cyan]")
        self.console.print("\n[cyan]Press Ctrl+C to quit")

    def serve(self, debug: bool = False) -> None:
        """Serve the Textual application."""
        self.debug = debug
        self.initialize_logging()

        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, self.request_exit)
            loop.add_signal_handler(signal.SIGTERM, self.request_exit)
        except NotImplementedError:
            pass

        if self.debug:
            log.info("Running in debug mode. You may use textual dev tools.")

        web.run_app(
            self._make_app(),
            host=self.host,
            port=self.port,
            handle_signals=False,
            loop=loop,
            print=lambda *args: None,
        )

    @aiohttp_jinja2.template("app_index.html")
    async def handle_index(self, request: web.Request) -> dict[str, Any]:
        """Serves the HTML for an app."""
        router = request.app.router

        # Usar el font_size configurado, pero permitir override por query param
        font_size = to_int(request.query.get("fontsize", str(self.font_size)), self.font_size)

        def get_url(route: str, **kwargs) -> str:
            """Get a URL from the aiohttp router."""
            path = router[route].url_for(**kwargs)
            return f"{self.public_url}{path}"

        def get_websocket_url(route: str, **kwargs) -> str:
            """Get a URL with a websocket prefix."""
            url = get_url(route, **kwargs)

            if self.public_url.startswith("https"):
                return "wss:" + url.split(":", 1)[1]
            else:
                return "ws:" + url.split(":", 1)[1]

        context = {
            "font_size": font_size,
            "app_websocket_url": get_websocket_url("websocket"),
        }
        context["config"] = {
            "static": {
                "url": get_url("static", filename="/").rstrip("/") + "/",
            },
        }
        context["application"] = {
            "name": self.title,
        }
        return context

    async def _process_messages(
        self, websocket: web.WebSocketResponse, app_service: AppService
    ) -> None:
        """Process messages from the client browser websocket."""
        TEXT = WSMsgType.TEXT

        async for message in websocket:
            if message.type != TEXT:
                continue
            envelope = message.json()
            assert isinstance(envelope, list)
            type_ = envelope[0]
            if type_ == "stdin":
                data = envelope[1]
                await app_service.send_bytes(data.encode("utf-8"))
            elif type_ == "resize":
                data = envelope[1]
                await app_service.set_terminal_size(data["width"], data["height"])
            elif type_ == "ping":
                data = envelope[1]
                await websocket.send_json(["pong", data])
            elif type_ == "blur":
                await app_service.blur()
            elif type_ == "focus":
                await app_service.focus()

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle the websocket that drives the remote process."""
        websocket = web.WebSocketResponse(heartbeat=15)

        width = to_int(request.query.get("width", "80"), 80)
        height = to_int(request.query.get("height", "24"), 24)

        app_service: AppService | None = None
        try:
            await websocket.prepare(request)
            app_service = AppService(
                self.command,
                write_bytes=websocket.send_bytes,
                write_str=websocket.send_str,
                close=websocket.close,
                download_manager=self.download_manager,
                debug=self.debug,
            )
            await app_service.start(width, height)
            try:
                await self._process_messages(websocket, app_service)
            finally:
                await app_service.stop()

        except asyncio.CancelledError:
            await websocket.close()

        except Exception as error:
            log.exception(error)

        finally:
            if app_service is not None:
                await app_service.stop()

        return websocket


def run_web_server(
    command: str,
    font_size: int = 16,
    host: str = "localhost",
    port: int = 8000,
    debug: bool = False,
) -> None:
    """Ejecutar el servidor web con tamaño de fuente personalizado."""
    server = WebServer(
        command=command,
        font_size=font_size,
        host=host,
        port=port,
    )
    server.serve(debug=debug)
