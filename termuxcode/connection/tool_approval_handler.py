#!/usr/bin/env python3
"""Manejo de aprobación de herramientas (canUseTool del SDK)."""

import asyncio

from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

from termuxcode.ws_config import logger


class ToolApprovalHandler:
    """Maneja solicitudes de aprobación de herramientas del SDK."""

    def __init__(self, sender, sdk_client=None, on_plan_rejected=None):
        self._sender = sender
        self._sdk_client = sdk_client
        self._ask_handler = None
        self._on_plan_rejected = on_plan_rejected
        self._approval_event = asyncio.Event()
        self._approval_response = None
        self._waiting = False

    @property
    def is_waiting(self) -> bool:
        return self._waiting

    async def can_use_tool(self, tool_name: str, input_data: dict, context):
        """Callback para el SDK. Envía solicitud al frontend y espera respuesta."""
        logger.info(f"=== can_use_tool: {tool_name} ===")

        if tool_name == "AskUserQuestion":
            logger.info("AskUserQuestion: esperando respuesta del usuario")
            questions = input_data.get("questions", [])
            responses, cancelled = await self._ask_handler.handle_questions(questions)
            if cancelled:
                responses = ["Cancelled by user" for _ in questions]
            answers = {q.get("question", ""): r for q, r in zip(questions, responses or [])}
            logger.info(f"AskUserQuestion: respuestas={answers}")
            return PermissionResultAllow(updated_input={**input_data, "answers": answers})

        # ExitPlanMode: mostrar el plan al usuario
        if tool_name == "ExitPlanMode":
            return await self._handle_exit_plan_mode(input_data)

        self._approval_event.clear()
        self._approval_response = None
        self._waiting = True

        try:
            await self._sender.send_tool_approval_request(tool_name, input_data)

            # Esperar respuesta del frontend (llega via _message_loop → handle_response)
            await self._approval_event.wait()

            response = self._approval_response
            if response and response.get("allow"):
                logger.info(f"=== Tool {tool_name} PERMITIDA ===")
                return PermissionResultAllow(updated_input=input_data)
            else:
                message = response.get("message", "Usuario denegó esta acción") if response else "Sin respuesta"
                logger.info(f"=== Tool {tool_name} DENEGADA: {message} ===")
                return PermissionResultDeny(message=message)
        finally:
            self._waiting = False

    async def _handle_exit_plan_mode(self, input_data: dict):
        """Maneja ExitPlanMode: muestra el plan y espera aprobación."""
        # El plan viene directamente en input_data['plan']
        plan_content = input_data.get("plan", "")

        if not plan_content:
            logger.warning("ExitPlanMode: no hay plan en input_data")
            plan_content = "(Plan vacío)"

        logger.info(f"ExitPlanMode: mostrando plan ({len(plan_content)} chars)")

        self._approval_event.clear()
        self._approval_response = None
        self._waiting = True

        try:
            await self._sender.send_file_view("Plan", plan_content)

            await self._approval_event.wait()

            response = self._approval_response
            if response and response.get("allow"):
                logger.info("=== Plan APROBADO ===")
                return PermissionResultAllow(updated_input=input_data)
            else:
                logger.info("=== Plan RECHAZADO - interrumpiendo SDK ===")
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
        logger.info(f"Approval response recibida: allow={data.get('allow')}")

    def reset(self):
        """Resetea el estado del handler."""
        self._approval_response = None
        self._approval_event.clear()
        self._waiting = False
