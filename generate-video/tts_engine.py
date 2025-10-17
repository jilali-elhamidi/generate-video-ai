import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# Try to import Coqui TTS
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except Exception as e:
    TTS_AVAILABLE = False
    logger.warning("Coqui TTS not available: %s", e)

# Fallback pyttsx3
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except Exception:
    PYTTSX3_AVAILABLE = False

def synthesize_audio_coqui(text, output_path):
    """
    Synthesize using Coqui TTS (if available).
    This will download the model on first run if not present.
    """
    # Select a lightweight model if available; adjust model name if you want another
    model_name = "tts_models/en/ljspeech/tacotron2-DDC"
    tts = TTS(model_name, progress_bar=False, gpu=False)  # gpu=True if tu as GPU
    tts.tts_to_file(text=text, file_path=output_path)
    return output_path

def synthesize_audio_pyttsx3(text, output_path):
    """
    Offline fallback using pyttsx3 (less natural but reliable).
    pyttsx3 can output only to speakers by default; to write to file we use temporary wave via save_to_file.
    """
    engine = pyttsx3.init()
    # Optionally set voice/rate properties:
    rate = engine.getProperty('rate')
    engine.setProperty('rate', int(rate * 0.95))
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path

def synthesize_audio(text, output_path=None):
    """
    Unified interface. Returns path to WAV file.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        output_path = tmp.name
        tmp.close()

    # Try Coqui first
    if TTS_AVAILABLE:
        try:
            return synthesize_audio_coqui(text, output_path)
        except Exception as e:
            logger.warning("Coqui TTS failed: %s", e)

    # Fallback to pyttsx3
    if PYTTSX3_AVAILABLE:
        try:
            return synthesize_audio_pyttsx3(text, output_path)
        except Exception as e:
            logger.warning("pyttsx3 failed: %s", e)

    raise RuntimeError("No TTS backend available. Install 'TTS' (Coqui) or 'pyttsx3'.")
