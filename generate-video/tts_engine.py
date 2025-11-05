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

def math_to_words(text):
    replacements = {
        '=': ' equals ',
        '+': ' plus ',
        '-': ' minus ',
        '−': ' minus ',
        '*': ' times ',
        '×': ' times ',
        '·': ' times ',
        '/': ' divided by ',
        '÷': ' divided by ',
        '^': ' to the power of ',
        '±': ' plus or minus ',
        '(': ' open parenthesis ',
        ')': ' close parenthesis ',
        '[': ' open bracket ',
        ']': ' close bracket ',
        '{': ' open brace ',
        '}': ' close brace ',
        '<': ' less than ',
        '>': ' greater than ',
        '≤': ' less than or equal to ',
        '≥': ' greater than or equal to ',
        '<=': ' less than or equal to ',
        '>=': ' greater than or equal to ',
        '≠': ' not equal to ',
        '≈': ' approximately equal to ',
        '≡': ' congruent to ',
        '∝': ' proportional to ',
        '√': ' square root of ',
        '∑': ' sum of ',
        '∏': ' product of ',
        '∫': ' integral of ',
        '∞': ' infinity ',
        '∂': ' partial ',
        '∇': ' nabla ',
        'π': ' pi ',
        'θ': ' theta ',
        'λ': ' lambda ',
        'μ': ' mu ',
        'α': ' alpha ',
        'β': ' beta ',
        'γ': ' gamma ',
        'δ': ' delta ',
        'φ': ' phi ',
        'ϕ': ' phi ',
        'σ': ' sigma ',
        'ω': ' omega ',
        'ε': ' epsilon ',
        'η': ' eta ',
        'κ': ' kappa ',
        'ν': ' nu ',
        'ρ': ' rho ',
        'τ': ' tau ',
        'ξ': ' xi ',
        'ζ': ' zeta ',
        'ψ': ' psi ',
        'χ': ' chi ',
        'Ω': ' omega ',
        'Σ': ' sigma ',
        'Γ': ' gamma ',
        'Δ': ' delta ',
        'Φ': ' phi ',
        'Λ': ' lambda ',
        'Θ': ' theta ',
        'Ψ': ' psi ',
        'Π': ' pi ',
        '∈': ' element of ',
        '∉': ' not an element of ',
        '⊂': ' subset of ',
        '⊆': ' subset or equal to ',
        '⊄': ' not a subset of ',
        '⊇': ' superset or equal to ',
        '∪': ' union ',
        '∩': ' intersection ',
        '∧': ' and ',
        '∨': ' or ',
        '⇒': ' implies ',
        '→': ' implies ',
        '↔': ' if and only if ',
        '⇔': ' if and only if ',
        '|': ' divides ',
        '∣': ' divides ',
        '∤': ' does not divide ',
        '…': ' and so on ',
        'ℕ': ' natural numbers ',
        'ℤ': ' integers ',
        'ℚ': ' rational numbers ',
        'ℝ': ' real numbers ',
        'ℂ': ' complex numbers ',
        'gcd': ' greatest common divisor ',
        '_': ' sub ',
        'deg': ' degrees ',
        'mod': ' modulo ',
        # ajoute d'autres symboles si nécessaire
    }

    for symbol, word in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(symbol, word)

    text = ' '.join(text.split())
    return text

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

    processed = math_to_words(text)

    # Try Coqui first
    if TTS_AVAILABLE:
        try:
            return synthesize_audio_coqui(processed, output_path)
        except Exception as e:
            logger.warning("Coqui TTS failed: %s", e)

    # Fallback to pyttsx3
    if PYTTSX3_AVAILABLE:
        try:
            return synthesize_audio_pyttsx3(processed, output_path)
        except Exception as e:
            logger.warning("pyttsx3 failed: %s", e)

    raise RuntimeError("No TTS backend available. Install 'TTS' (Coqui) or 'pyttsx3'.")
