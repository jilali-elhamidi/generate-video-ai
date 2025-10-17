import os
import math
import tempfile
import textwrap
from pathlib import Path
import uuid
from typing import List
import moviepy.editor as mpy
import matplotlib.pyplot as plt
from tts_engine import synthesize_audio  # ton moteur TTS (par ex. Coqui TTS)

# --- Configuration globale ---
VIDEO_SIZE = (1280, 720)
DPI = 100
FONT_SIZE = 36
BG_COLOR = (0, 0, 0)
TEXT_COLOR = "white"
LINE_HEIGHT = 1.2


# --------------------------------------------------------------
# 1️⃣  Splitter le texte du prof en plusieurs "slides"
# --------------------------------------------------------------
def split_script_to_slides(script: str, max_chars_per_slide: int = 700) -> List[str]:
    """Divise un script en plusieurs diapositives selon la longueur."""
    script = script.replace("\r\n", "\n").strip()
    if not script:
        return []

    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    slides = []

    for p in paragraphs:
        if len(p) <= max_chars_per_slide:
            slides.append(p)
        else:
            # Découpe par phrases
            sentences = [s.strip() for s in p.replace("!", ".").replace("?", ".").split(".") if s.strip()]
            cur = ""
            for s in sentences:
                if len(cur) + len(s) + 1 <= max_chars_per_slide:
                    cur += (" " + s + ".")
                else:
                    slides.append(cur.strip())
                    cur = s + "."
            if cur:
                slides.append(cur.strip())

    # Si trop de slides, les regrouper
    if len(slides) > 40:
        ratio = math.ceil(len(slides) / 40)
        new = []
        for i in range(0, len(slides), ratio):
            new.append(" ".join(slides[i:i + ratio]))
        slides = new

    return slides


# --------------------------------------------------------------
# 2️⃣  Rendre le texte d’une slide sous forme d’image
# --------------------------------------------------------------
def render_text_slide(text: str, out_path: str, title: str = None):
    """Crée une image à partir du texte, avec Matplotlib."""
    plt.rcParams['figure.facecolor'] = BG_COLOR
    fig = plt.figure(figsize=(VIDEO_SIZE[0] / DPI, VIDEO_SIZE[1] / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    wrapped = textwrap.fill(text, width=60)

    y = 0.9
    if title:
        ax.text(0.5, y, title, color=TEXT_COLOR, fontsize=FONT_SIZE + 6,
                ha='center', va='center')
        y -= 0.12

    ax.text(0.05, y, wrapped, color=TEXT_COLOR, fontsize=FONT_SIZE,
            ha='left', va='top', wrap=True)

    fig.savefig(out_path, dpi=DPI, bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)


# --------------------------------------------------------------
# 3️⃣  Générer toutes les slides d’un texte
# --------------------------------------------------------------
def create_slides_from_script(script: str, title: str = None, tmp_dir: str = None) -> List[str]:
    slides = split_script_to_slides(script)
    if not slides:
        return []

    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="slides_")
    else:
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    image_paths = []
    for idx, s in enumerate(slides):
        out_path = os.path.join(tmp_dir, f"slide_{idx:03d}.png")
        render_text_slide(s, out_path, title=title if idx == 0 else None)
        image_paths.append(out_path)
    return image_paths

def split_to_sentences(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    parts = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".")]
    sentences = [s + "." for s in parts if s]
    return sentences

def create_sentence_segments(script_text: str, title: str = None, tmp_dir: str = None):
    sentences = split_to_sentences(script_text)
    if not sentences:
        return []
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="slides_sent_")
    else:
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    segments = []
    for idx, s in enumerate(sentences):
        img_path = os.path.join(tmp_dir, f"sent_{idx:03d}.png")
        render_text_slide(s, img_path, title=title if idx == 0 else None)
        atmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio_path = atmp.name
        atmp.close()
        synthesize_audio(s, audio_path)
        audio_clip = mpy.AudioFileClip(audio_path)
        duration = float(audio_clip.duration)
        audio_clip.close()
        if duration <= 0 or math.isnan(duration):
            duration = 1.5
        segments.append((img_path, audio_path, duration))
    return segments

def assemble_synced_video(segments, output_path: str):
    clips = []
    for (img_path, audio_path, duration) in segments:
        base = mpy.ImageClip(img_path).set_duration(duration)
        base = base.resize(height=VIDEO_SIZE[1])
        base = base.on_color(size=VIDEO_SIZE, color=BG_COLOR, pos=("center", "center"))
        animated = base.fx(mpy.vfx.fadein, 0.3).fx(mpy.vfx.fadeout, 0.3)
        def zoom(t):
            return 1.0 + 0.03 * (t / max(duration, 1e-6))
        animated = animated.resize(lambda t: zoom(t))
        aclip = mpy.AudioFileClip(audio_path)
        clip = animated.set_audio(aclip)
        clips.append(clip)
    if not clips:
        raise ValueError("Aucune diapositive trouvée.")
    video = mpy.concatenate_videoclips(clips, method="compose")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        verbose=False,
        logger=None,
    )
    for c in clips:
        try:
            if c.audio:
                c.audio.close()
        except Exception:
            pass
        try:
            c.close()
        except Exception:
            pass
    return output_path


# --------------------------------------------------------------
# 4️⃣  Assembler audio + slides en vidéo
# --------------------------------------------------------------
def assemble_video_from_slides_and_audio(image_paths: List[str], audio_path: str, output_path: str):
    """Crée la vidéo à partir des slides et de l’audio généré."""
    if not image_paths:
        raise ValueError("Aucune diapositive trouvée.")

    audio_clip = mpy.AudioFileClip(audio_path)
    audio_duration = float(audio_clip.duration)
    num_slides = len(image_paths)

    per_slide_dur = float(audio_duration) / float(num_slides) if num_slides > 0 else float(audio_duration)
    if math.isnan(per_slide_dur) or per_slide_dur <= 0:
        per_slide_dur = 2.0  # durée minimale par slide

    clips = []
    for img in image_paths:
        clip = mpy.ImageClip(img).set_duration(per_slide_dur)
        clip = clip.resize(height=VIDEO_SIZE[1])
        clip = clip.on_color(size=VIDEO_SIZE, color=BG_COLOR, pos=('center', 'center'))
        clips.append(clip)

    video = mpy.concatenate_videoclips(clips, method="compose").set_audio(audio_clip)

    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        verbose=False,
        logger=None
    )

    audio_clip.close()
    video.close()
    return output_path


# --------------------------------------------------------------
# 5️⃣  Fonction principale : générer la vidéo complète
# --------------------------------------------------------------
def generate_video(script_text: str, title: str = "Explication", output_dir: str = None) -> str:
    """Pipeline complet : TTS → images → vidéo, synchronisée phrase par phrase."""
    if output_dir is None:
        output_dir = os.getcwd()

    segments = create_sentence_segments(script_text, title=title)
    if not segments:
        raise ValueError("Aucune phrase détectée.")

    output_path = os.path.join(output_dir, f"video_{uuid.uuid4().hex}.mp4")
    assemble_synced_video(segments, output_path)

    for (_, audio_path, _) in segments:
        try:
            os.remove(audio_path)
        except Exception:
            pass
    return os.path.abspath(output_path)
