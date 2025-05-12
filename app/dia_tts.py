import base64
import io
import json
import logging
import os
import tempfile
from typing import Dict, Optional, List

import soundfile as sf
import torch
from dia.model import Dia

logger = logging.getLogger(__name__)


class DiaTTS:
    """
    A class to handle text-to-speech using the Dia model.
    """
    def __init__(self, model_id: str = "nari-labs/Dia-1.6B"):
        """
        Initialize the Dia TTS model.
        
        Args:
            model_id (str): The Hugging Face model ID for Dia.
        """
        self.model_id = model_id
        self.sampling_rate = 44100  # Dia uses 44.1kHz
        self._initialize_model()
        
    def _initialize_model(self):
        """
        Initialize the Dia model.
        """
        logger.info(f"Loading Dia model '{self.model_id}'...")
        
        # Check for GPU availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            logger.warning("Running Dia on CPU. This will be very slow and is not officially supported.")
        
        try:
            self.model = Dia.from_pretrained(self.model_id)
            logger.info("Dia model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Dia model: {e}")
            raise
    
    async def text_to_speech(self, text: str) -> List[Dict[str, str]]:
        """
        Convert text to speech using Dia.
        
        Args:
            text (str): The text to convert to speech.
            
        Returns:
            List[Dict[str, str]]: A list of dictionaries containing audio chunks in base64 format.
        """
        # Add speaker tag if not present
        if not text.startswith("[S"):
            text = f"[S1] {text}"
        
        try:
            # Generate audio
            logger.info(f"Generating audio for text: {text[:50]}...")
            audio_chunks = []
            
            # Generate the audio using the correct method
            output_waveform = self.model.generate(text)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Write to file
            sf.write(temp_path, output_waveform, self.sampling_rate)
            
            # Read the generated audio file and convert to base64
            with open(temp_path, 'rb') as f:
                # Here we could chunk the file if needed
                audio_data = f.read()
                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                audio_chunks.append({"audio": base64_audio})
            
            # Clean up temp file
            os.unlink(temp_path)
            
            logger.info("Audio generation successful.")
            return audio_chunks
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return []
            
    async def clone_voice(self, clone_text: str, clone_audio_path: Optional[str] = None):
        """
        Clone a voice using Dia.
        
        Args:
            clone_text (str): Text that describes the voice to clone.
            clone_audio_path (str, optional): Path to audio file for voice cloning.
            
        Note: This would require implementing Dia's voice cloning capabilities.
        """
        logger.info("Voice cloning with Dia is not fully implemented yet.")
        # Future implementation when needed
        pass