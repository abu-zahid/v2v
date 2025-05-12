import logging

import os
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr

load_dotenv(override=True)


class Config(BaseModel):
    # Logging
    LOG_LEVEL: ClassVar[SecretStr] = os.environ.get("LOG_LEVEL", "WARN")
    LOG_FORMAT: ClassVar[SecretStr] = os.environ.get("LOG_FORMAT", "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s")
    LOG_DATE_FORMAT: ClassVar[SecretStr] = os.environ.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    LOG_HANDLER: ClassVar[SecretStr] = os.environ.get("LOG_HANDLER", "stream")
    LOG_FILE_PATH: ClassVar[SecretStr] = os.environ.get("LOG_FILE_PATH", "logs/app.log")
 
    # # AWS
    # DEFAULT_AWS_REGION: ClassVar[SecretStr] = os.environ["DEFAULT_AWS_REGION"]

    # # AWS Cognito
    # COGNITO_USER_POOL_REGION_NAME: ClassVar[SecretStr] = os.environ["COGNITO_USER_POOL_REGION_NAME"]

    # # Database Tables
    # USER_DATA_TABLE_NAME: ClassVar[SecretStr] = os.environ["USER_DATA_TABLE_NAME"]
    # USER_DATA_TABLE_REGION_NAME: ClassVar[SecretStr] = os.environ["USER_DATA_TABLE_REGION_NAME"]
    # RECIPIENT_DATA_TABLE: ClassVar[SecretStr] = os.environ["RECIPIENT_DATA_TABLE"]

    # # ElevenLabs
    # ELEVENLABS_API_KEY: ClassVar[SecretStr] = os.environ["ELEVENLABS_API_KEY"]

    # OpenAI
    OPENAI_API_KEY: ClassVar[SecretStr] = os.environ["OPENAI_API_KEY"]


    @classmethod
    def configure_logger(cls):
        handlers = []
        if cls.LOG_HANDLER == "file":
            handlers.append(logging.FileHandler(cls.LOG_FILE_PATH))
        elif cls.LOG_HANDLER == "stream":
            handlers.append(logging.StreamHandler())
        else:
            raise ValueError(f"Invalid log handler: {cls.LOG_HANDLER}")

        logging.basicConfig(
            level=cls.LOG_LEVEL,
            format=cls.LOG_FORMAT, 
            datefmt=cls.LOG_DATE_FORMAT,
            handlers=handlers,
        )


Config.configure_logger()
