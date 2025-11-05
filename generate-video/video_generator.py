import os
import math
import tempfile
import textwrap
from pathlib import Path
import uuid
from typing import List
import moviepy.editor as mpy
from PIL import Image, ImageDraw, ImageFont
from tts_engine import synthesize_audio

# --- Configuration globale ---
VIDEO_SIZE = (1280, 720)
FONT_SIZE = 36
BG_COLOR = (0, 0, 0)
TEXT_COLOR = "white"
LINE_SPACING = 10

# --- Chargement des polices ---
try:
    FONT_PATH = "arial.ttf"
    MAIN_FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    TITLE_FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE + 6)
    EXP_FONT = ImageFont.truetype(FONT_PATH, int(FONT_SIZE * 0.8))
except IOError:
    print(f"Attention : Police '{FONT_PATH}' non trouvée. Utilisation de la police par défaut.")
    MAIN_FONT = ImageFont.load_default()
    TITLE_FONT = ImageFont.load_default()
    EXP_FONT = ImageFont.load_default()


# --------------------------------------------------------------
# 1️⃣  Splitter le texte du prof en plusieurs "slides" (INCHANGÉ)
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
# 2️⃣  Rendre le texte d’une slide sous forme d’image (INCHANGÉ)
# --------------------------------------------------------------
def render_text_slide(text: str, out_path: str, title: str = None):
    """Crée une image à partir du texte, avec Pillow (PIL)."""
    img = Image.new('RGB', VIDEO_SIZE, color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    margin_x = int(VIDEO_SIZE[0] * 0.05) # 5% de marge
    current_y = int(VIDEO_SIZE[1] * 0.1) # 10% du haut

    if title:
        # Ancre 'ma' = milieu horizontal ('m'), haut vertical ('a' pour ascender)
        draw.text((VIDEO_SIZE[0] / 2, current_y), title, font=TITLE_FONT, fill=TEXT_COLOR, anchor="ma")
        # Estimer la hauteur du titre pour descendre
        title_box = TITLE_FONT.getbbox(title)
        current_y += (title_box[3] - title_box[1]) + int(FONT_SIZE * 0.75)

    wrapped = textwrap.fill(text, width=60)

    # Ancre 'la' = gauche horizontal ('l'), haut vertical ('a')
    draw.text((margin_x, current_y), wrapped, font=MAIN_FONT, fill=TEXT_COLOR, spacing=LINE_SPACING, anchor="la")

    img.save(out_path)


# --------------------------------------------------------------
# 3️⃣  Générer toutes les slides d’un texte (INCHANGÉ)
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

# --------------------------------------------------------------
# 4️⃣  CRÉATION DES SEGMENTS (INCHANGÉ)
# --------------------------------------------------------------
def create_sentence_segments(script_text: str, title: str = None, tmp_dir: str = None, explanations: List[str] = None, explanations_display: List[bool] = None):
    """
    Renvoie les chemins et les durées pour l'audio de la phrase ET l'audio de l'explication.
    """
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
        # 1. Générer l'image (rapide)
        img_path = os.path.join(tmp_dir, f"sent_{idx:03d}.png")
        render_text_slide(s, img_path, title=title if idx == 0 else None)

        # 2. Générer l'audio de la phrase (lent)
        atmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        s_audio_path = atmp.name
        atmp.close()
        synthesize_audio(s, s_audio_path)

        # 3. Obtenir la durée de l'audio de la phrase
        try:
            with mpy.AudioFileClip(s_audio_path) as aclip:
                s_dur = float(aclip.duration)
        except Exception:
            s_dur = 1.5 # Sécurité
        if s_dur <= 0 or math.isnan(s_dur): s_dur = 1.5

        # 4. Gérer l'explication (si elle existe)
        e_audio_path = None
        e_dur = 0.0
        exp_text = explanations[idx] if idx < len(explanations) else None

        if exp_text:
            # 4a. Générer l'audio de l'explication (lent)
            etmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            e_audio_path = etmp.name
            etmp.close()
            synthesize_audio(exp_text, e_audio_path)

            # 4b. Obtenir la durée de l'audio de l'explication
            try:
                with mpy.AudioFileClip(e_audio_path) as eclip:
                    e_dur = float(eclip.duration)
            except Exception:
                e_dur = 1.5 # Sécurité
            if e_dur <= 0 or math.isnan(e_dur): e_dur = 1.5

        # 5. Gérer le flag d'affichage
        exp_show = None
        if idx < len(explanations_display):
            try: exp_show = bool(explanations_display[idx])
            except Exception: exp_show = None

        # 6. Stocker TOUTES les informations
        segments.append((img_path, s_audio_path, s_dur, e_audio_path, e_dur, exp_text, exp_show))

    return segments

#
# --------------------------------------------------------------
# 5️⃣  ASSEMBLAGE VIDÉO (MODIFIÉ : method="chain")
# --------------------------------------------------------------
#
def assemble_synced_video(segments, output_path: str, show_explanations_text: bool = False, style: dict = None):
    """
    MODIFIÉ : Le correctif 'astype('uint8')' est déplacé à la TOUTE FIN
    de la création du segment, APRES les fondus et les superpositions.
    """
    style = style or {}
    overlay_opacity = float(style.get("overlay_opacity", 0.35))
    zoom_strength = float(style.get("zoom_strength", 0.03))

    clips = []

    # Unpack les données de segment
    for (img_path, s_audio, s_dur, e_audio, e_dur, exp_text, exp_show) in segments:

        total_dur = s_dur + e_dur # Durée totale de ce segment

        # 1. Créer le clip vidéo de base (sans la correction ici)
        base_clip = mpy.ImageClip(img_path).set_duration(total_dur)

        # 2. Appliquer les fondus (ceci convertit en float64)
        animated = base_clip.fx(mpy.vfx.fadein, 0.3).fx(mpy.vfx.fadeout, 0.3)

        # 3. Préparer les clips audio (inchangé)
        audioclips = []
        s_aclip = mpy.AudioFileClip(s_audio)
        audioclips.append(s_aclip)

        if e_audio:
            e_aclip = mpy.AudioFileClip(e_audio).set_start(s_dur)
            audioclips.append(e_aclip)

        final_audio = mpy.CompositeAudioClip(audioclips)
        clip = animated.set_audio(final_audio) # 'clip' est maintenant en float64

        # 4. Gérer l'overlay (si nécessaire) (inchangé)
        show_this_exp = False
        if exp_text:
            if exp_show is None:
                show_this_exp = bool(show_explanations_text)
            else:
                show_this_exp = bool(exp_show)

        if show_this_exp:
            parts = [p.strip() for p in exp_text.replace("?", ".").replace("!", ".").split(".")]
            exp_sentences = [p for p in parts if p]
            if not exp_sentences:
                exp_sentences = [exp_text]

            n = len(exp_sentences)
            per_dur = (e_dur / n) if n > 0 else e_dur
            exp_subclips = []

            for i, sub in enumerate(exp_sentences):
                exp_img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                exp_img_path = exp_img_tmp.name
                exp_img_tmp.close()

                # ... (Logique de dessin Pillow inchangée) ...
                img = Image.new('RGBA', VIDEO_SIZE, (255, 255, 255, 0))
                draw = ImageDraw.Draw(img)
                panel_height_ratio = 0.4
                panel_y_ratio = 0.3
                panel_width_ratio = 0.8
                panel_x_ratio = (1 - panel_width_ratio) / 2
                x0 = int(VIDEO_SIZE[0] * panel_x_ratio)
                y0 = int(VIDEO_SIZE[1] * panel_y_ratio)
                x1 = x0 + int(VIDEO_SIZE[0] * panel_width_ratio)
                y1 = y0 + int(VIDEO_SIZE[1] * panel_height_ratio)
                alpha = int(overlay_opacity * 255)
                draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, alpha))
                sub_wrapped = textwrap.fill(sub, width=55)
                center_x = x0 + (x1 - x0) / 2
                center_y = y0 + (y1 - y0) / 2
                draw.text((center_x, center_y), sub_wrapped, font=EXP_FONT,
                          fill=TEXT_COLOR, spacing=LINE_SPACING,
                          anchor="mm", align="center")
                img.save(exp_img_path)

                sub_clip = mpy.ImageClip(exp_img_path).set_duration(per_dur)
                sub_clip = sub_clip.set_position(("center", "center"))

                def sub_zoom(t, _pd=per_dur):
                    return 1.0 + zoom_strength * (t / max(_pd, 1e-6))
                sub_clip = sub_clip.resize(lambda t: sub_zoom(t))
                sub_clip = sub_clip.fx(mpy.vfx.fadein, 0.15).fx(mpy.vfx.fadeout, 0.15)
                exp_subclips.append(sub_clip)

            if exp_subclips:
                exp_seq = mpy.concatenate_videoclips(exp_subclips, method="compose") # 'compose' est OK ici
                exp_seq = exp_seq.set_start(s_dur).set_duration(e_dur)
                exp_seq = exp_seq.fl_image(lambda pic: pic.astype('uint8'))

                # 'clip' est le composite, il est définitivement en float64
                clip = mpy.CompositeVideoClip([clip, exp_seq], size=VIDEO_SIZE).set_duration(total_dur).set_audio(final_audio)

        # --------------------------------------------------------------
        # MODIFICATION FINALE : LE NOUVEAU CORRECTIF
        # --------------------------------------------------------------
        clip = clip.fl_image(lambda pic: pic.astype('uint8'))
        # --------------------------------------------------------------

        clips.append(clip)

    if not clips:
        raise ValueError("Aucune diapositive trouvée.")

    # --------------------------------------------------------------
    # CORRECTION PRINCIPALE : method="chain"
    # --------------------------------------------------------------
    video = mpy.concatenate_videoclips(clips, method="chain")
    # --------------------------------------------------------------

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
    # Fermeture de TOUS les clips audio
    for c in clips:
        try:
            if c.audio: c.audio.close()
        except Exception: pass
        try: c.close()
        except Exception: pass

    return output_path


# --------------------------------------------------------------
# 4️⃣  Assembler (Fonction dépréciée, MODIFIÉE)
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

    # --------------------------------------------------------------
    # CORRECTION PRINCIPALE : method="chain"
    # --------------------------------------------------------------
    video = mpy.concatenate_videoclips(clips, method="chain").set_audio(audio_clip)
    # --------------------------------------------------------------

    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",        # Faute de frappe corrigée
        audio_codec="aac",
        threads=4,
        preset="medium",
        verbose=False,
        logger=None
    )

    audio_clip.close()
    video.close()
    return output_path


#
# --------------------------------------------------------------
# 6️⃣  Fonction principale : générer la vidéo (CORRIGÉE)
# --------------------------------------------------------------
#
def generate_video(script_text: str, title: str = "Explication", output_dir: str = None, explanations: List[str] = None, show_explanations_text: bool = False, style: dict = None, explanations_display: List[bool] = None) -> str:
    """Pipeline complet : TTS → images → vidéo, synchronisée phrase par phrase, avec explications et style facultatifs."""
    if output_dir is None:
        output_dir = os.getcwd()

    segments = create_sentence_segments(
        script_text,
        title=title,
        explanations=explanations or [],
        # --------------------------------------------------------------
        # CORRECTION DE LA SYNTAXE ( : -> = )
        # --------------------------------------------------------------
        explanations_display=explanations_display or [] 
    )
    if not segments:
        raise ValueError("Aucune diapositive trouvée.")

    output_path = os.path.join(output_dir, f"video_{uuid.uuid4().hex}.mp4")
    assemble_synced_video(segments, output_path, show_explanations_text=show_explanations_text, style=style or {})

    # Nettoie les DEUX fichiers audio
    for (_, s_audio, _, e_audio, _, _, _) in segments:
        try:
            if s_audio: os.remove(s_audio)
        except Exception:
            pass
        try:
            if e_audio: os.remove(e_audio)
        except Exception:
            pass

    # Il y avait une petite faute de frappe ici, corrigée
    return os.path.abspath(output_path)