import os
import math
import tempfile
import textwrap
from pathlib import Path
import uuid
from typing import List
import moviepy.editor as mpy
import matplotlib.pyplot as plt
from matplotlib import patches
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

def create_sentence_segments(script_text: str, title: str = None, tmp_dir: str = None, explanations: List[str] = None, explanations_display: List[bool] = None):
    sentences = split_to_sentences(script_text)
    if not sentences:
        return []
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="slides_sent_")
    else:
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    explanations = explanations or []
    explanations_display = explanations_display or []
    segments = []
    for idx, s in enumerate(sentences):
        img_path = os.path.join(tmp_dir, f"sent_{idx:03d}.png")
        render_text_slide(s, img_path, title=title if idx == 0 else None)
        atmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio_path = atmp.name
        atmp.close()
        synthesize_audio(s, audio_path)
        # Optionally synthesize explanation audio and concatenate after sentence
        exp_text = explanations[idx] if idx < len(explanations) else None
        if exp_text:
            etmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            exp_audio_path = etmp.name
            etmp.close()
            synthesize_audio(exp_text, exp_audio_path)
            # Concatenate sentence audio + explanation audio
            try:
                a1 = mpy.AudioFileClip(audio_path)
                a2 = mpy.AudioFileClip(exp_audio_path)
                cat = mpy.concatenate_audioclips([a1, a2])
                # Write concatenated temp wav for duration calc and later use
                merged = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                merged_path = merged.name
                merged.close()
                cat.write_audiofile(merged_path, fps=44100, nbytes=2, codec="pcm_s16le", verbose=False, logger=None)
                a1.close(); a2.close(); cat.close()
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
                audio_path = merged_path
            except Exception:
                pass
        audio_clip = mpy.AudioFileClip(audio_path)
        duration = float(audio_clip.duration)
        audio_clip.close()
        if duration <= 0 or math.isnan(duration):
            duration = 1.5
        # Store also the explanation text and display flag for optional on-screen text
        exp_show = None
        if idx < len(explanations_display):
            try:
                exp_show = bool(explanations_display[idx])
            except Exception:
                exp_show = None
        segments.append((img_path, audio_path, duration, exp_text if exp_text else None, exp_show))
    return segments

def assemble_synced_video(segments, output_path: str, show_explanations_text: bool = False, style: dict = None):
    style = style or {}
    overlay_opacity = float(style.get("overlay_opacity", 0.35))
    zoom_strength = float(style.get("zoom_strength", 0.03))
    text_scale = float(style.get("text_scale", 0.78))
    clips = []
    for (img_path, audio_path, duration, exp_text, exp_show) in segments:
        base = mpy.ImageClip(img_path).set_duration(duration)
        base = base.resize(height=VIDEO_SIZE[1])
        # Compose explicitly over a uint8 ColorClip background to avoid float64 arrays
        bg = mpy.ColorClip(size=VIDEO_SIZE, color=BG_COLOR).set_duration(duration)
        base = base.set_position(("center", "center"))
        composed = mpy.CompositeVideoClip([bg, base], size=VIDEO_SIZE).set_duration(duration)
        animated = composed.fx(mpy.vfx.fadein, 0.3).fx(mpy.vfx.fadeout, 0.3)
        aclip = mpy.AudioFileClip(audio_path)
        clip = animated.set_audio(aclip)
        # Optional on-screen explanation text under the main text
        # Per-sentence control: if explanations_display provided, it overrides the global flag.
        show_this_exp = False
        if exp_text:
            if exp_show is None:
                show_this_exp = bool(show_explanations_text)
            else:
                show_this_exp = bool(exp_show)
        if show_this_exp:
            # Split explanation into sentences and display them sequentially, with zoom on the overlay only
            parts = [p.strip() for p in exp_text.replace("?", ".").replace("!", ".").split(".")]
            exp_sentences = [p for p in parts if p]
            if not exp_sentences:
                exp_sentences = [exp_text]
            n = len(exp_sentences)
            per_dur = duration / n if n > 0 else duration
            exp_subclips = []
            for i, sub in enumerate(exp_sentences):
                exp_img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                exp_img_path = exp_img_tmp.name
                exp_img_tmp.close()
                fig = plt.figure(figsize=(VIDEO_SIZE[0] / DPI, VIDEO_SIZE[1] / DPI), dpi=DPI)
                ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
                panel_height = 0.4
                panel_y = 0.3
                rect = patches.Rectangle((0.1, panel_y), 0.8, panel_height,
                                         linewidth=0, edgecolor=None,
                                         facecolor=(0, 0, 0, overlay_opacity))
                ax.add_patch(rect)
                sub_wrapped = textwrap.fill(sub, width=55)
                ax.text(0.5, panel_y + panel_height * 0.5, sub_wrapped,
                        color=TEXT_COLOR, fontsize=int(FONT_SIZE * 0.8),
                        ha='center', va='center', wrap=True)
                fig.savefig(exp_img_path, dpi=DPI, bbox_inches='tight', pad_inches=0.0, transparent=True)
                plt.close(fig)
                sub_clip = mpy.ImageClip(exp_img_path).set_duration(per_dur)
                sub_clip = sub_clip.set_position(("center", "center"))
                # Apply zoom animation only to the explanation overlay
                def sub_zoom(t, _pd=per_dur):
                    return 1.0 + zoom_strength * (t / max(_pd, 1e-6))
                sub_clip = sub_clip.resize(lambda t: sub_zoom(t))
                sub_clip = sub_clip.fx(mpy.vfx.fadein, 0.15).fx(mpy.vfx.fadeout, 0.15)
                exp_subclips.append(sub_clip)
            if exp_subclips:
                exp_seq = mpy.concatenate_videoclips(exp_subclips, method="compose")
                clip = mpy.CompositeVideoClip([clip, exp_seq], size=VIDEO_SIZE).set_duration(duration).set_audio(aclip)
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
        clip_img = mpy.ImageClip(img).set_duration(per_slide_dur)
        clip_img = clip_img.resize(height=VIDEO_SIZE[1])
        bg = mpy.ColorClip(size=VIDEO_SIZE, color=BG_COLOR).set_duration(per_slide_dur)
        clip_img = clip_img.set_position(('center', 'center'))
        clip = mpy.CompositeVideoClip([bg, clip_img], size=VIDEO_SIZE).set_duration(per_slide_dur)
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
def generate_video(script_text: str, title: str = "Explication", output_dir: str = None, explanations: List[str] = None, show_explanations_text: bool = False, style: dict = None, explanations_display: List[bool] = None) -> str:
    """Pipeline complet : TTS → images → vidéo, synchronisée phrase par phrase, avec explications et style facultatifs."""
    if output_dir is None:
        output_dir = os.getcwd()

    segments = create_sentence_segments(
        script_text,
        title=title,
        explanations=explanations or [],
        explanations_display=explanations_display or []
    )
    if not segments:
        raise ValueError("Aucune phrase détectée.")

    output_path = os.path.join(output_dir, f"video_{uuid.uuid4().hex}.mp4")
    assemble_synced_video(segments, output_path, show_explanations_text=show_explanations_text, style=style or {})

    for (_, audio_path, _, *rest) in segments:
        try:
            os.remove(audio_path)
        except Exception:
            pass
    return os.path.abspath(output_path)
