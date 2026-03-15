# Plan: Ejecución Paralela de Sesiones

## 🎯 Objetivo
Permitir que las queries de una sesión sigan ejecutándose en background mientras el usuario cambia a otra sesión.

## 📊 Análisis de Complejidad: **Media-Alta** (6-8 horas de desarrollo)

### Complejidad estimada por componente:

| Componente | Complejidad | Tiempo estimado | Riesgo |
|------------|-------------|-----------------|--------|
| Sistema de notificaciones | Media | 2-3 horas | Medio |
| Modificar cancelación de tasks | Baja | 1 hora | Bajo |
| Indicador visual de "corriendo" | Baja | 1 hora | Bajo |
| Botón "Stop" por sesión | Media | 1-2 horas | Medio |
| Persistencia de estado "running" | Media | 1 hora | Medio |

---

## 🏗️ Arquitectura Propuesta

### Enfoque más elegante: **Background Tasks + Notificaciones No-Obstructivas**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ClaudeChat App (Textual)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Session A  │  │  Session B  │  │  Session C  │              │
│  │  [● Running]│  │  [● Running]│  │             │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                    │
│         ▼                ▼                ▼                    │
│  ┌──────────────────────────────────────────────┐               │
│  │         BackgroundTaskManager                 │               │
│  │  - Mantiene tasks por session_id             │               │
│  │  - No cancela al cambiar de sesión          │               │
│  │  - Callback cuando task termina             │               │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
│  ┌──────────────────────────────────────────────┐               │
│  │         NotificationQueue                     │               │
│  │  - Cola de notificaciones pendientes          │               │
│  │  - Muestra cuando vuelves a la sesión        │               │
│  │  - Toast/sistema no obstructivo              │               │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Plan de Implementación

### Fase 1: Infraestructura de Background Tasks (2 horas)

#### 1.1 Crear `background_manager.py`
```python
# src/termuxcode/tui/background_manager.py

from typing import Dict, Callable, Optional
import asyncio

class BackgroundTaskManager:
    """Gestiona tasks de asyncio por sesión sin cancelar al cambiar"""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(
        self,
        session_id: str,
        coro,
        on_complete: Callable[[str, Exception | None], None] = None
    ) -> None:
        """Iniciar task para una sesión"""
        # Cancelar task anterior si existe
        if session_id in self._tasks:
            self.cancel_task(session_id)

        async def wrapped():
            try:
                await coro
            except Exception as e:
                if on_complete:
                    on_complete(session_id, e)
            else:
                if on_complete:
                    on_complete(session_id, None)

        task = asyncio.create_task(wrapped())
        self._tasks[session_id] = task

    def cancel_task(self, session_id: str) -> bool:
        """Cancelar task de una sesión explícitamente"""
        if session_id in self._tasks:
            self._tasks[session_id].cancel()
            del self._tasks[session_id]
            return True
        return False

    def is_running(self, session_id: str) -> bool:
        """Verificar si una sesión tiene task activo"""
        if session_id not in self._tasks:
            return False
        return not self._tasks[session_id].done()

    def get_running_sessions(self) -> list[str]:
        """Obtener todas las sesiones con tasks activos"""
        return [
            sid for sid, task in self._tasks.items()
            if not task.done()
        ]
```

#### 1.2 Integrar en `app.py`
```python
from .background_manager import BackgroundTaskManager

class ClaudeChat(App):
    def __init__(self):
        super().__init__()
        self.background_manager = BackgroundTaskManager()
        # ... resto del init
```

---

### Fase 2: Modificar cancelación de tasks (1 hora)

#### 2.1 Eliminar cancelación automática en `_switch_to_session`
```python
# En session_handlers.py, línea 70-80

async def _switch_to_session(self, session_id: str, update_tabs: bool = True) -> None:
    # ... código existente ...

    # ❌ REMOVER ESTAS LÍNEAS:
    # if state and state.pending_task and not state.pending_task.done():
    #     state.pending_task.cancel()

    # En su lugar, solo guardar que la sesión está corriendo
    # El background_manager ya tiene control
```

#### 2.2 Mantener cancelación solo en `action_close_session`
```python
# En session_handlers.py, línea 120-130

async def action_close_session(self) -> None:
    # ... código existente ...

    # Solo cancelar si se cierra la sesión explícitamente
    if self._current_session_id:
        state = self._session_states.get(self._current_session_id)
        if state and state.pending_task and not state.pending_task.done():
            state.pending_task.cancel()  # ← Mantener esto

    # ... resto del código ...
```

---

### Fase 3: Sistema de Notificaciones (2-3 horas)

#### 3.1 Crear `notification_system.py`
```python
# src/termuxcode/tui/notification_system.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

class NotificationType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"

@dataclass
class Notification:
    session_id: str
    session_name: str
    message: str
    notification_type: NotificationType
    timestamp: datetime
    read: bool = False

class NotificationQueue:
    """Cola de notificaciones para tareas que terminaron en background"""

    def __init__(self):
        self._notifications: List[Notification] = []

    def add(
        self,
        session_id: str,
        session_name: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO
    ) -> None:
        notif = Notification(
            session_id=session_id,
            session_name=session_name,
            message=message,
            notification_type=notification_type,
            timestamp=datetime.now(),
        )
        self._notifications.append(notif)

    def get_for_session(self, session_id: str) -> List[Notification]:
        return [n for n in self._notifications if n.session_id == session_id and not n.read]

    def get_unread(self) -> List[Notification]:
        return [n for n in self._notifications if not n.read]

    def mark_as_read(self, session_id: str) -> None:
        for notif in self._notifications:
            if notif.session_id == session_id:
                notif.read = True

    def clear(self) -> None:
        self._notifications.clear()
```

#### 3.2 Integrar notificaciones en tabs
```python
# En session_handlers.py, en _update_tabs

async def _update_tabs(self) -> None:
    """Actualizar tabs con indicador de notificaciones"""
    await self.tabs.clear()
    running_sessions = self.background_manager.get_running_sessions()
    unread_notifs = self.notification_queue.get_for_session

    for session in self.session_manager.list_sessions():
        tab_id = f"tab-{session.id}"

        # Construir label del tab
        label = session.name

        # Agregar indicador "●" si está corriendo
        if session.id in running_sessions:
            label = f"[dim]●[/dim] {label}"

        # Agregar indicador "!" si tiene notificaciones no leídas
        if self.notification_queue.get_for_session(session.id):
            label = f"[yellow]![/yellow] {label}"

        await self.tabs.add_tab(Tab(label, id=tab_id))
```

#### 3.3 Mostrar notificaciones al cambiar de sesión
```python
# En session_handlers.py, en _switch_to_session

async def _switch_to_session(self, session_id: str, update_tabs: bool = True) -> None:
    # ... código existente ...

    # Mostrar notificaciones pendientes de esta sesión
    notifs = self.notification_queue.get_for_session(session_id)
    if notifs:
        for notif in notifs:
            style = {
                NotificationType.SUCCESS: "[green]✓[/green]",
                NotificationType.ERROR: "[red]✗[/red]",
                NotificationType.INFO: "[blue]ℹ[/blue]"
            }.get(notif.notification_type, "")

            self.chat_log.write(f"{style} {notif.message}")

        # Marcar como leídas
        self.notification_queue.mark_as_read(session_id)

    # ... resto del código ...
```

---

### Fase 4: Indicador visual de "corriendo" (1 hora)

#### 4.1 Agregar widget de estado de sesión
```python
# En app.py

from textual.widgets import Static

class ClaudeChat(App):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal():
                yield Tabs(id="sessions-tabs")
                yield Static(id="session-status")  # ← Nuevo widget
            yield ChatLog(id="chat-log")
            yield Input(placeholder="Mensaje...", id="input")
        yield Footer()
```

#### 4.2 Actualizar status cuando cambia de sesión
```python
# En session_handlers.py, en _switch_to_session

async def _switch_to_session(self, session_id: str, update_tabs: bool = True) -> None:
    # ... código existente ...

    # Actualizar status widget
    status_widget = self.query_one("#session-status", Static)
    if self.background_manager.is_running(session_id):
        status_widget.update("[dim green]● Corriendo en background[/dim]")
    else:
        status_widget.update("")

    # ... resto del código ...
```

---

### Fase 5: Botón "Stop" por sesión (1-2 horas)

#### 5.1 Agregar botón en la UI
```python
# En app.py

from textual.widgets import Button

class ClaudeChat(App):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal():
                yield Tabs(id="sessions-tabs")
                yield Button("Stop", id="stop-btn", disabled=True)
            yield ChatLog(id="chat-log")
            yield Input(placeholder="Mensaje...", id="input")
        yield Footer()

    def on_mount(self) -> None:
        # ... código existente ...
        self._update_stop_button()

    def _update_stop_button(self) -> None:
        """Habilitar/deshabilitar botón Stop según estado"""
        stop_btn = self.query_one("#stop-btn", Button)
        if self._current_session_id:
            is_running = self.background_manager.is_running(self._current_session_id)
            stop_btn.disabled = not is_running
        else:
            stop_btn.disabled = True

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop-btn":
            await self.action_stop_query()
```

#### 5.2 Acción para detener query explícitamente
```python
# En session_handlers.py

async def action_stop_query(self) -> None:
    """Detener query de la sesión actual explícitamente"""
    if not self._current_session_id:
        return

    state = self._session_states.get(self._current_session_id)
    if state and state.pending_task and not state.pending_task.done():
        state.pending_task.cancel()
        self.background_manager.cancel_task(self._current_session_id)
        self.chat_log.write("[dim]Query detenida[/dim]")
        self._update_stop_button()
```

---

### Fase 6: Callback cuando task termina (1 hora)

#### 6.1 Integrar callback en `query_handlers.py`
```python
# En query_handlers.py, en _handle_query

def _handle_query(self, prompt: str) -> None:
    # ... código existente ...

    # Crear callback para cuando termine
    def on_complete(session_id: str, error: Exception | None):
        session = self.session_manager.get_session(session_id)
        if not session:
            return

        if error:
            # Solo mostrar error si estamos en esa sesión
            if session_id == self._current_session_id:
                self.chat_log.write_error(f"Error: {error}")
            else:
                # Guardar notificación para cuando vuelva
                self.notification_queue.add(
                    session_id=session_id,
                    session_name=session.name,
                    message=f"Query terminó con error: {error}",
                    notification_type=NotificationType.ERROR
                )
        else:
            # Notificar que terminó si no estamos en esa sesión
            if session_id != self._current_session_id:
                self.notification_queue.add(
                    session_id=session_id,
                    session_name=session.name,
                    message="Query completada",
                    notification_type=NotificationType.SUCCESS
                )

    # Iniciar task con callback
    state.pending_task = asyncio.create_task(self._run_query_safe(state, prompt))

    # Registrar en background_manager con callback
    self.background_manager.start_task(
        session_id=self._current_session_id,
        coro=state.pending_task,
        on_complete=on_complete
    )
```

---

## 🔧 Archivos a modificar/crear

### Archivos nuevos:
| Archivo | Líneas estimadas | Descripción |
|---------|------------------|-------------|
| `background_manager.py` | ~80 | Gestor de tasks por sesión |
| `notification_system.py` | ~60 | Sistema de notificaciones |

### Archivos modificados:
| Archivo | Cambios | Complejidad |
|---------|---------|-------------|
| `app.py` | Integrar BackgroundTaskManager, NotificationQueue, botón Stop | Media |
| `session_handlers.py` | Eliminar cancelación automática, mostrar notificaciones | Media |
| `query_handlers.py` | Agregar callback on_complete | Baja |
| `session_state.py` | No requiere cambios (mantiene pending_task) | N/A |

---

## 🧪 Testing Plan

### Casos de prueba:
1. ✅ Iniciar query en sesión A, cambiar a sesión B, verificar que sigue corriendo
2. ✅ Volver a sesión A, verificar que la query terminó y se muestra resultado
3. ✅ Iniciar query en sesión A, cambiar a B, iniciar otra query en B
4. ✅ Verificar que ambas queries corren en paralelo
5. ✅ Hacer clic en botón Stop, verificar que se cancela solo esa query
6. ✅ Cerrar sesión con query corriendo, verificar que se cancela
7. ✅ Verificar notificaciones cuando queries terminan en background
8. ✅ Verificar indicadores en tabs (● para corriendo, ! para notificaciones)

---

## ⚠️ Consideraciones y Riesgos

### Riesgos:
1. **Concurrencia de historial**: Si dos queries escriben al mismo tiempo al historial de la misma sesión → Mitigación: Una query a la vez por sesión (ya existe esta lógica)
2. **Consumo de memoria**: Muchas queries corriendo en paralelo → Mitigación: SDK ya gestiona esto, pero podríamos agregar límite
3. **Confusión de usuario**: Puede no notar que queries siguen corriendo → Mitigación: Indicadores claros en tabs

### Limitaciones:
- No se pueden tener múltiples queries **en la misma sesión** (sigue siendo una a la vez)
- Solo se puede ejecutar una query por sesión en paralelo con otras sesiones

---

## 🎁 Extras opcionales (no en plan principal):

1. **Toast notifications flotantes**: Notificaciones que aparecen en la esquina de la pantalla
2. **Sonido cuando query termina**: Beep o vibración en móvil
3. **Badge de notificaciones**: Número de notificaciones no leídas en tabs
4. **Historial de queries**: Lista de queries completadas por sesión
5. **Límite de queries paralelas**: Configurar máximo de 2-3 queries simultáneas

---

## 📝 Resumen de Tiempos

| Fase | Tiempo | Acumulado |
|------|--------|-----------|
| Fase 1: BackgroundTaskManager | 2h | 2h |
| Fase 2: Modificar cancelación | 1h | 3h |
| Fase 3: Sistema de notificaciones | 2-3h | 5-6h |
| Fase 4: Indicador visual | 1h | 6-7h |
| Fase 5: Botón Stop | 1-2h | 7-9h |
| Fase 6: Callback on_complete | 1h | 8-10h |
| Testing y debug | 2h | **10-12h** |

**Tiempo total estimado: 8-12 horas**

---

## ✅ Criterios de Completado

- [ ] Las queries siguen corriendo al cambiar de sesión
- [ ] Indicador visual en tabs para sesiones corriendo (●)
- [ ] Notificaciones cuando queries terminan en background
- [ ] Botón "Stop" para cancelar queries explícitamente
- [ ] Solo cancela queries al cerrar sesión explícitamente
- [ ] Tests pasan todos los casos de prueba
- [ ] No rompe funcionalidad existente
