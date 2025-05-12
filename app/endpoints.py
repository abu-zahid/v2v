from fastapi import Depends, WebSocket

# from .controllers import get_recipient_details
# from .dependencies import require_cloned_voice

from .v2vpipeline import V2VPipeline


async def dia_voice_chat(
    websocket: WebSocket,
    # recipient_id: str,
    # user_details: dict = Depends(require_cloned_voice),
):
    """
    Voice chat using OpenAI for transcription and Dia for text-to-speech
    
    This endpoint connects to a voice chat WebSocket. It uses the OpenAI real-time API for STT
    and Dia for TTS.
    """
    v2v_pipeline = V2VPipeline(websocket)
    await v2v_pipeline.run()