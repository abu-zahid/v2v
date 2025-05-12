from logging import getLogger
logger = getLogger(__name__)

import asyncio
import json
import traceback

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect, WebSocketState

import openai

from websockets.asyncio.client import connect, ClientConnection
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK
from websockets.protocol import State


from config import Config
from .dia_tts import DiaTTS

class V2VPipeline:
    """
    This class is responsible for handling the Voice-to-Voice (V2V) pipeline. \\
    It handles the connections to the client, the transcriber, the LLM and the TTS.

    Pipeline flow:

    - Client --voice chunks, current speaker--> server.
    - Server --voice chunks--> transcriber.

    - Transcriber --voice activities, transcript--> server.
    - Server --voice activities--> client.
    
    - Server --transcript--> LLM.
    - LLM --response--> server.
    - Server --response--> TTS.

    - TTS --speech--> server.
    - Server --speech--> client.

    Communication format:
    - All messages are JSON of the form `{"event": "<event_name>", "data": <data>}`.

    Server events:
    - user.speech_started - No data
    - user.speech_stopped - No data
    - output_audio_buffer.append - Sends a base64 encoded string of the audio chunk

    Client events:
    - input_audio_buffer.append - Expects a base64 encoded string of the audio chunk
    - current_speaker.switch - Expects a string, either "user", "ai" or anything else.
    """
    def __init__(
        self,
        client_ws: WebSocket,
        # user_details: dict,
        # recipient_details: dict,
        scribe_ws: ClientConnection | None = None,
        # tts_ws: ClientConnection | None = None,
    ):
        self.client_ws = client_ws

        # self.user_details = user_details
        # self.voice_id = user_details["cloned_voice_id"]
        # self.recipient_details = recipient_details

        self.scribe_ws = scribe_ws
        
        # Initialize Dia TTS
        self.dia_tts = DiaTTS()

        self.initiate_llm()


    def initiate_llm(self):
        self._was_llm_interrupted = False
        self._current_speaker = None

        # Initialize the LLM context with system prompt focused on voice conversation
        self._llm_context = {
            "messages": [
                {
                    "role": "system", 
                    "content": """
                    You are a helpful and engaging AI voice assistant. You are currently in a real-time voice conversation with a user. You'll receive transcripts of what they say and respond naturally.
                    
                    Guidelines for effective voice conversations:
                    
                    1. Keep responses concise and conversational - shorter than you would in text
                    2. Use natural speech patterns with pauses, emphasis, and occasional verbal fillers
                    3. Be warm and personable while remaining helpful and informative
                    4. Respond directly to the most recent query without unnecessary context repetition
                    5. If you need to list items, keep the list very short (2-3 items) and present them conversationally
                    6. When describing complex topics, use analogies and everyday language
                    
                    Remember that the user hears your response rather than reads it, so optimize for listening comprehension.
                    """
                },
            ],
        }


    async def connect_scribe(self):
        self.scribe_ws = await connect(
            "wss://api.openai.com/v1/realtime?intent=transcription",
            additional_headers={
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",
            }
        )

        turn_detection_config = {
            "type": "semantic_vad",
            "eagerness": "medium",
        }

        scribe_config_session = {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-transcribe",
                # "prompt": "",
                "language": "en",
            },
            "turn_detection": turn_detection_config,
            "input_audio_noise_reduction": {
                "type": "near_field"
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }

        scribe_config = {
            "type": "transcription_session.update",
            "session": scribe_config_session,
        }


        await self.scribe_ws.send(json.dumps(scribe_config))


    async def connect_outbound_websockets(self):
        try:
            await self.connect_scribe()
        except (ConnectionClosed, ConnectionClosedOK) as e:
            if self.client_ws and self.client_ws.client_state == WebSocketState.CONNECTED:
                await self.client_ws.close()
            if self.scribe_ws and self.scribe_ws.state == State.OPEN:
                await self.scribe_ws.close()

            logger.error(f"Scribe disconnected: {e}")
            logger.error(traceback.format_exc())


    async def client_message_handler(self):
        try:
            while True:
                data = await self.client_ws.receive_json()
                if data["event"] == "input_audio_buffer.append":
                    await self.scribe_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": data["data"], # expects a base64 encoded string of the audio chunk
                    }))
                elif data["event"] == "current_speaker.switch":
                    self._current_speaker = data["data"]

        except WebSocketDisconnect as e:
            if self.scribe_ws and self.scribe_ws.state == State.OPEN:
                await self.scribe_ws.close()

            logger.error(f"Client disconnected: {e}")
            logger.error(traceback.format_exc())

        except (ConnectionClosed, ConnectionClosedOK) as e:
            if self.scribe_ws and self.scribe_ws.state == State.OPEN:
                await self.scribe_ws.close()
            if self.client_ws and self.client_ws.client_state == WebSocketState.CONNECTED:
                await self.client_ws.close()

            logger.error(f"Scribe disconnected: {e}")
            logger.error(traceback.format_exc())


    async def scribe_message_handler(self):
        try:
            while True:
                scribe_msg = await self.scribe_ws.recv()
                scribe_msg_obj = json.loads(scribe_msg)

                if scribe_msg_obj["type"] == "conversation.item.input_audio_transcription.completed":
                    transcript = scribe_msg_obj["transcript"]
                    asyncio.create_task(self.llm_n_tts_pipeline(transcript))
                elif scribe_msg_obj["type"] == "input_audio_buffer.speech_started":
                    if self._current_speaker == "ai":
                        self._was_llm_interrupted = True
                    else:
                        self._was_llm_interrupted = False
                    await self.client_ws.send_json({
                        "event": "user.speech_started",
                    })
                elif scribe_msg_obj["type"] == "input_audio_buffer.speech_stopped":
                    await self.client_ws.send_json({
                        "event": "user.speech_stopped",
                    })

        except WebSocketDisconnect as e:
            if self.scribe_ws and self.scribe_ws.state == State.OPEN:
                await self.scribe_ws.close()

            logger.error(f"Client disconnected: {e}")
            logger.error(traceback.format_exc())

        except (ConnectionClosed, ConnectionClosedOK) as e:
            if self.client_ws and self.client_ws.client_state == WebSocketState.CONNECTED:
                await self.client_ws.close()

            logger.error(f"Scribe disconnected: {e}")
            logger.error(traceback.format_exc())


    async def llm_n_tts_pipeline(self, transcript: str):
        # Get response from LLM
        response = self.get_llm_response(transcript)
        
        # Use Dia for TTS
        try:
            audio_chunks = await self.dia_tts.text_to_speech(response)
            
            # Send audio chunks to client
            for chunk in audio_chunks:
                if "audio" in chunk and chunk["audio"]:
                    await self.client_ws.send_json({
                        "event": "output_audio_buffer.append",
                        "data": chunk["audio"],  # Base64 encoded audio
                    })
        except Exception as e:
            logger.error(f"Error in TTS processing: {e}")
            logger.error(traceback.format_exc())


    def get_llm_response(self, transcript: str) -> str:
        # Add interruption context if the last response was interrupted
        if self._was_llm_interrupted:
            self._llm_context["messages"].append({
                "role": "system",
                "content": """Note: Your previous response's TTS was interrupted by the user. So the user did not hear the end of your previous response. Please acknowledge this and continue the conversation appropriately.
                Also, you're already in the middle of the conversation. So, do not start your response with 'Hello', 'Hi' or anything similar. Just start with the response. And if the user asks to continue in the next few messages, you may start your response with 'Continuing from where we left off...', 'As I was saying...' or something similar."""
            })
            self._was_llm_interrupted = False  # Reset the flag
        
        # Add format instructions for Dia TTS
        self._llm_context["messages"].append({
            "role": "system",
            "content": """When generating your response, you can use the following formatting to enhance the speech synthesis:
            
            1. You can use speaker tags [S1] for the primary voice or [S2] for a different voice.
            2. You can include non-verbal elements like (laughs), (sighs), or (pauses) which will be properly rendered.
            3. Your response will be converted directly to speech without any additional processing.
            
            For example:
            [S1] I think that's a great idea! (laughs) Let me tell you why...
            [S2] But have you considered the alternative perspective?
            [S1] That's a good point.
            
            Don't use these features excessively - just when they help create a more natural conversational flow.
            """
        })
        
        self._llm_context["messages"].append({"role": "user", "content": transcript})
        llm_response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=self._llm_context["messages"],
        )
        llm_response_content = llm_response.choices[0].message.content
        
        # Add [S1] tag if not present (ensure it works with Dia)
        if not llm_response_content.strip().startswith("[S"):
            llm_response_content = f"[S1] {llm_response_content}"
            
        self._llm_context["messages"].append({"role": "assistant", "content": llm_response_content})
        return llm_response_content


    async def run(self):
        await self.client_ws.accept()
        await self.connect_outbound_websockets()

        # Create tasks for handling client and scribe messages
        client_task = asyncio.create_task(self.client_message_handler())
        scribe_task = asyncio.create_task(self.scribe_message_handler())
        
        # Wait for either task to complete (which would indicate a disconnect)
        await asyncio.gather(client_task, scribe_task, return_exceptions=True)