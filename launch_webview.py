#!/usr/bin/env python3
"""
Lanza TermuxCode en WebView con HTTPS usando certificado firmado por CA propia.
"""

from termuxgui import Connection, Activity, WebView


def main() -> None:
    print("🔌 Conectando con Termux:GUI...")
    c = Connection()

    print("📱 Creando Activity...")
    a = Activity(c)
    a.keepscreenon(True)

    print("🌐 Creando WebView...")
    w = WebView(a)
    w.setdimensions("MATCH_PARENT", "MATCH_PARENT")

    print("⚙️  Habilitando JavaScript...")
    w.allowjavascript(True)
    w.allownavigation(True)

    # Usar HTTP (localhost no necesita HTTPS)
    url = "http://localhost:1988"
    print(f"\n🚀 Cargando TermuxCode: {url}")
    print(f"   Modo: HTTP (localhost, sin certificado)")
    w.loaduri(url)

    print("\n✅ TermuxCode cargado en WebView!")
    print("📋 Si instalaste la CA correctamente, deberías ver la interfaz")
    print("📋 Presiona Ctrl+C para salir\n")

    # Loop de eventos
    try:
        event_count = 0
        for event in c.events():
            event_count += 1
            print(f"\n📨 Event #{event_count}: {event.type}")

            # Imprimir TODOS los atributos del evento
            for attr in dir(event):
                if not attr.startswith('_'):
                    try:
                        value = getattr(event, attr)
                        if not callable(value):
                            print(f"  {attr}: {value}")
                    except:
                        pass

            print("-" * 40)

    except KeyboardInterrupt:
        print("\n👋 Cerrando...")
        a.finish()
        c.close()


if __name__ == "__main__":
    main()
