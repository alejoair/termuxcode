#!/usr/bin/env python3
"""Manejo de aprobación de herramientas (canUseTool del SDK)."""

import asyncio

from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

from termuxcode.ws_config import logger


class ToolApprovalHandler:
    """Maneja solicitudes de aprobación de herramientas del SDK."""

    AUTO_APPROVE_MODES = {"bypassPermissions", "acceptEdits"}

    def __init__(self, sender=None, sdk_client=None, on_plan_rejected=None, session=None, agent_options=None):
        self._sender = sender  # Mantener por compatibilidad temporal
        self._sdk_client = sdk_client
        self._ask_handler = None
        self._on_plan_rejected = on_plan_rejected
        self._session = session  # Nuevo: referencia a Session
        self._agent_options = agent_options or {}
        self._approval_event = asyncio.Event()
        self._cancel_event = asyncio.Event()
        self._approval_response = None
        self._waiting = False

    @property
    def is_waiting(self) -> bool:
        return self._waiting

    async def _wait_for_approval(self):
        """Espera respuesta del frontend con soporte de cancelación (sin timeout)."""
        # Limpiar cancel stale de desconexiones previas
        self._cancel_event.clear()
        approval_task = asyncio.ensure_future(self._approval_event.wait())
        cancel_task = asyncio.ensure_future(self._cancel_event.wait())

        done, pending = await asyncio.wait(
            {approval_task, cancel_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if cancel_task in done:
            return None  # Cancelado
        return self._approval_response

    async def can_use_tool(self, tool_name: str, input_data: dict, context):
        """Callback para el SDK. Envía solicitud al frontend y espera respuesta."""
        if tool_name == "AskUserQuestion":
            questions = input_data.get("questions", [])
            responses, cancelled = await self._ask_handler.handle_questions(questions)
            if cancelled:
                responses = ["Cancelled by user" for _ in questions]
            answers = {q.get("question", ""): r for q, r in zip(questions, responses or [])}
            return PermissionResultAllow(updated_input={**input_data, "answers": answers})

        # ExitPlanMode: mostrar el plan al usuario
        if tool_name == "ExitPlanMode":
            return await self._handle_exit_plan_mode(input_data)

        # Auto-aprobar si el permission_mode lo indica
        permission_mode = self._agent_options.get("permission_mode", "bypassPermissions")
        if permission_mode in self.AUTO_APPROVE_MODES:
            return PermissionResultAllow(updated_input=input_data)

        self._approval_event.clear()
        self._approval_response = None
        self._waiting = True

        try:
            # Enviar vía Session si está disponible, sino vía sender (compatibilidad)
            if self._session:
                await self._session.send_message({
                    "type": "tool_approval_request",
                    "tool_name": tool_name,
                    "input": input_data
                })
            elif self._sender:
                await self._sender.send_tool_approval_request(tool_name, input_data)
            else:
                raise RuntimeError("ToolApprovalHandler no tiene session ni sender configurado")

            # Esperar respuesta del frontend (llega via _message_loop → handle_response)
            response = await self._wait_for_approval()

            if response and response.get("allow"):
                return PermissionResultAllow(updated_input=input_data)
            else:
                message = response.get("message", "Usuario denegó esta acción") if response else "Sin respuesta"
                return PermissionResultDeny(message=message)
        finally:
            self._waiting = False

    async def _handle_exit_plan_mode(self, input_data: dict):
        """Maneja ExitPlanMode: muestra el plan y espera aprobación."""
        # El plan viene directamente en input_data['plan']
        plan_content = input_data.get("plan", "")

        if not plan_content:
            plan_content = "(Plan vacío)"

        self._approval_event.clear()
        self._approval_response = None
        self._waiting = True

        try:
            # Enviar vía Session si está disponible, sino vía sender (compatibilidad)
            if self._session:
                await self._session.send_message({
                    "type": "file_view",
                    "file_path": "Plan",
                    "content": plan_content
                })
            elif self._sender:
                await self._sender.send_file_view("Plan", plan_content)
            else:
                raise RuntimeError("ToolApprovalHandler no tiene session ni sender configurado")

            response = await self._wait_for_approval()
            if response and response.get("allow"):
                return PermissionResultAllow(updated_input=input_data)
            else:
                # Interrumpir el SDK para devolver el control al usuario
                if self._sdk_client:
                    try:
                        await self._sdk_client.interrupt()
                    except Exception as e:
                        logger.warning(f"Error al interrumpir SDK tras rechazo de plan: {e}")
                if self._on_plan_rejected:
                    await self._on_plan_rejected()
                return PermissionResultDeny(message="Usuario rechazó el plan")
        finally:
            self._waiting = False

    def handle_response(self, data: dict):
        """Recibe la respuesta del frontend y desbloquea el callback."""
        self._approval_response = data
        self._approval_event.set()

    def cancel(self):
        """Cancela la espera activa (llamado al desconectar WebSocket)."""
        self._approval_response = None
        self._cancel_event.set()
        self._waiting = False

    def reset(self):
        """Resetea el estado del handler."""
        self._approval_response = None
        self._approval_event.clear()
        self._cancel_event.clear()
        self._waiting = False
