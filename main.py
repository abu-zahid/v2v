from fastapi import FastAPI

from app.routes import router as voice_chat_router

app = FastAPI()

app.include_router(voice_chat_router)
