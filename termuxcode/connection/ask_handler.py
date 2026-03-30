#!/usr/bin/env python3
"""Manejo del flujo AskUserQuestion (SDK ↔ Frontend)."""

import asyncio

from termuxcode.ws_config import logger


class AskUserQuestionHandler:
    """Maneja el flujo bidireccional de AskUserQuestion."""

    def __init__(self, sender=None, session=None):
        """Inicializa el handler.

        Args:
            sender: (DEPRECADO) Instancia de MessageSender para enviar mensajes
            session: Instancia de Session para enviar mensajes (nuevo método)
        """
        self._sender = sender  # Mantener por compatibilidad temporal
        self._session = session
        self._question_response = None
        self._question_cancelled = False
        self._question_event = asyncio.Event()
        self._waiting_for_question_response = False

    @property
    def is_waiting(self) -> bool:
        """Verifica si actualmente se está esperando una respuesta."""
        return self._waiting_for_question_response

    async def handle_questions(self, questions: list) -> tuple:
        """Envía preguntas al frontend y espera las respuestas.

        Args:
            questions: Lista de preguntas con el formato:
                [{
                    "question": "Texto de la pregunta?",
                    "header": "Header",
                    "multiSelect": False,
                    "options": [
                        {"label": "Opcion 1", "description": "Desc", "preview": "codigo"}
                    ]
                }]

        Returns:
            Tupla (respuestas, cancelled)
        """
        self._question_response = None
        self._question_event.clear()
        self._waiting_for_question_response = True

        # Enviar vía Session si está disponible, sino vía sender (compatibilidad)
        if self._session:
            await self._session.send_message({
                "type": "ask_user_question",
                "questions": questions
            })
        elif self._sender:
            await self._sender.send_ask_user_question(questions)
        else:
            raise RuntimeError("AskUserQuestionHandler no tiene session ni sender configurado")

        # message_processor sigue corriendo en paralelo y procesará el question_response
        await self._question_event.wait()

        self._waiting_for_question_response = False
        return self._question_response, self._question_cancelled

    async def handle_response(self, responses: list, cancelled: bool = False):
        """Maneja la respuesta del usuario a una pregunta.

        Args:
            responses: Lista de respuestas del usuario
            cancelled: Si el usuario canceló la pregunta
        """
        self._question_response = responses
        self._question_cancelled = cancelled
        self._question_event.set()
        logger.info(f"Respuesta recibida (cancelled={cancelled}): {responses}")

    def reset(self):
        """Resetea el estado del handler."""
        self._question_response = None
        self._question_cancelled = False
        self._question_event.clear()
        self._waiting_for_question_response = False
