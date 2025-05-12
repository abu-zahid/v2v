from fastapi import APIRouter

from . import endpoints

router = APIRouter()

router.websocket("/ai-voice-chat")(endpoints.dia_voice_chat)