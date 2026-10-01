"""
============================================================
  PREDICT ENGINE — classify a song with the trained CNN
============================================================
Can be used two ways:

1. From the command line (types a filename):
       python predict_final.py "วัดใจ.mp3"

2. Imported by app2.py (the Gradio UI):
       from predict_final import load_classifier, classify_audio
   -> load_classifier() loads the model ONCE
   -> classify_audio(model, genres, path) returns {genre: probability}
============================================================
"""

import os
import sys
import numpy as np
import librosa
from tensorflow.keras.models import load_model

# ---- MUST match the settings used during training ----
CLIP_SECONDS = 5
N_MELS       = 128
TIME_STEPS   = 128
SR           = 22050
MAX_CLIPS_PER_SONG = 20

MODEL_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "genre_cnn_v3.keras")
CLASSES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "genre_classes_v3.npy")

# ---- Folder where your songs live (for the command-line lookup) ----
SONGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")

# Used if you run the script without typing a filename:
DEFAULT_SONG = "วัดใจ.mp3"


# ---- Audio helpers (must be identical to training) ----
def split_into_clips(y):
    clip_len = CLIP_SECONDS * SR
    clips = []
    for start in range(0, len(y) - clip_len + 1, clip_len):
        clips.append(y[start:start + clip_len])
        if len(clips) >= MAX_CLIPS_PER_SONG:
            break
    if not clips and len(y) > 0:
        clips = [np.pad(y, (0, clip_len - len(y)))]
    return clips


def spectrogram_from_audio(y):
    mel = librosa.feature.melspectrogram(y=y, sr=SR, n_mels=N_MELS)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    if mel_db.shape[1] < TIME_STEPS:
        pad = TIME_STEPS - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad)), mode="constant")
    else:
        mel_db = mel_db[:, :TIME_STEPS]
    mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-9)
    return mel_db


# ============================================================
#  REUSABLE FUNCTIONS (used by both CLI and the Gradio app)
# ============================================================
def load_classifier():
    """Load the trained model and genre list ONCE. Returns (model, genres)."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. Train the model first."
        )
    model  = load_model(MODEL_PATH)
    genres = list(np.load(CLASSES_PATH, allow_pickle=True))
    return model, genres


def classify_audio(model, genres, file_path):
    """
    Classify one audio file.
    Returns a dict {genre: probability} — ready for Gradio's gr.Label
    and easy to sort/print elsewhere.
    """
    audio, _ = librosa.load(file_path, sr=SR)
    clips = split_into_clips(audio)
    specs = np.array([spectrogram_from_audio(c) for c in clips])[..., np.newaxis]
    probs = model.predict(specs, verbose=0).mean(axis=0)   # average across clips
    return {genre: float(p) for genre, p in zip(genres, probs)}


def find_song(filename):
    """Search SONGS_FOLDER and all subfolders for `filename`."""
    direct = os.path.join(SONGS_FOLDER, filename)
    if os.path.exists(direct):
        return direct
    for root, _, files in os.walk(SONGS_FOLDER):
        if filename in files:
            return os.path.join(root, filename)
    return None


# ============================================================
#  COMMAND-LINE MODE (only runs when called directly)
# ============================================================
if __name__ == "__main__":
    model, genres = load_classifier()

    filename = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SONG
    song_path = find_song(filename)
    if song_path is None:
        print(f"❌ Could not find '{filename}' anywhere inside:\n   {SONGS_FOLDER}")
        sys.exit()

    predictions = classify_audio(model, genres, song_path)
    results = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

    print(f"\n🎵 {os.path.basename(song_path)}")
    print("-" * 40)
    for genre, p in results:
        bar = "█" * int(p * 30)
        print(f"  {genre:<12} {p*100:5.1f}%  {bar}")
    print(f"\n  → Best guess: {results[0][0]} ({results[0][1]*100:.1f}%)")
