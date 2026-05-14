"""
Pruebas básicas para TERMUXCODE.
"""


class TestBasic:
    """Pruebas básicas de funcionalidad."""

    def test_import_termuxcode(self):
        """Verifica que el paquete se puede importar."""
        import termuxcode
        assert termuxcode is not None

    def test_version_exists(self):
        """Verifica que existe la versión del paquete."""
        from termuxcode import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_simple_math(self):
        """Prueba simple para verificar que las pruebas funcionan."""
        assert 1 + 1 == 2
        assert 2 * 2 == 4

    def test_string_operations(self):
        """Prueba de operaciones de strings."""
        text = "termuxcode"
        assert text.upper() == "TERMUXCODE"
        assert len(text) == 10


class TestConnection:
    """Pruebas relacionadas con la conexión WebSocket."""

    def test_session_registry_import(self):
        """Verifica que session_registry se puede importar."""
        from termuxcode.connection import session_registry
        assert session_registry is not None
        assert hasattr(session_registry, 'register')
        assert hasattr(session_registry, 'unregister')
        assert hasattr(session_registry, 'get')

    def test_message_sender_import(self):
        """Verifica que MessageSender se puede importar."""
        from termuxcode.connection.sender import MessageSender
        assert MessageSender is not None
