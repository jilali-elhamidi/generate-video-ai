# exemple_tts.py
from TTS.api import TTS

# 1️⃣ Choisir un modèle TTS pré-entraîné
# Tu peux lister les modèles disponibles avec: TTS.list_models()
model_name = "tts_models/en/ljspeech/tacotron2-DDC"

# 2️⃣ Créer l'instance TTS
tts = TTS(model_name)

# 3️⃣ Texte à convertir en audio
texte = "earning a new skill can be both exciting and challenging. It requires patience, dedication, and consistent practice. At first, progress may seem slow, and mistakes are inevitable, but each error is an opportunity to learn and improve. Over time, the small efforts accumulate, building confidence and competence. By embracing a growth mindset and staying curious, anyone can overcome obstacles and achieve their goals. The journey itself often becomes as rewarding as the outcome."

# 4️⃣ Générer le fichier audio
tts.tts_to_file(text=texte, file_path="output2.wav")

print("Audio généré : output.wav")
