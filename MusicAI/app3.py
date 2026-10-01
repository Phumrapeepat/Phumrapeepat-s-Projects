import os
import random
import gradio as gr

# --- Import the real classifier engine + the songs folder path ---
from predictff import load_classifier, classify_audio, SONGS_FOLDER

# --- Load the model ONCE at startup (not on every click) ---
print("Loading the trained model... (this happens once)")
MODEL, GENRES = load_classifier()
print(f"Model ready. Genres: {GENRES}")


# ============================================================
#  Recommendations: pick 5 random songs from the genre's folder
# ============================================================
def recommend_from_folder(genre, n=5, exclude_filename=None):
    """
    Look inside songs/<genre>/ and return up to n random song names.
    exclude_filename: skip this file (e.g. the song the user just uploaded).
    """
    genre_path = os.path.join(SONGS_FOLDER, genre)

    if not os.path.isdir(genre_path):
        return [f"(No folder found for genre '{genre}'.)"]

    # All audio files in that genre folder
    songs = [f for f in os.listdir(genre_path)
             if f.lower().endswith((".mp3", ".wav"))]

    # Don't recommend the exact song the user just uploaded
    if exclude_filename:
        songs = [s for s in songs if s != exclude_filename]

    if not songs:
        return ["(No other songs in this genre folder yet.)"]

    # Pick up to n at random (fewer if the folder is small)
    picks = random.sample(songs, min(n, len(songs)))

    # Show the name without the file extension, a bit cleaner
    return [f"🎵 {os.path.splitext(s)[0]}" for s in picks]


# ============================================================
#  The function the UI calls when you submit
# ============================================================
def predict_and_recommend(audio_file):
    if audio_file is None:
        return None, "⬆️ Please upload or drop an audio file first."

    # --- Real prediction from the CNN ---
    predictions = classify_audio(MODEL, GENRES, audio_file)   # {genre: prob}

    top_genre = max(predictions, key=predictions.get)
    top_conf  = predictions[top_genre]

    # --- 5 random songs from that genre's folder ---
    uploaded_name = os.path.basename(audio_file)
    songs = recommend_from_folder(top_genre, n=5, exclude_filename=uploaded_name)

    md  = f"### 🎧 Best guess: **{top_genre}** ({top_conf*100:.1f}%)\n\n"
    md += f"5 random **{top_genre}** tracks from your library:\n\n"
    for s in songs:
        md += f"* {s}\n"

    return predictions, md


# ============================================================
#  Build the interface
# ============================================================
demo = gr.Interface(
    fn=predict_and_recommend,
    inputs=gr.Audio(
        sources=["upload"],
        type="filepath",
        label="Drop your song here (MP3/WAV)"
    ),
    outputs=[
        gr.Label(num_top_classes=5, label="Genre Breakdown"),
        gr.Markdown(label="Recommended Tracks"),
    ],
    title="🎵 AI Music Genre Classifier & Recommender",
    description="Drop an audio file below. The trained CNN predicts its genre "
                "and recommends similar tracks from your own collection.",
    theme=gr.themes.Ocean(primary_hue="violet",
                          secondary_hue="pink",
                          neutral_hue="stone"),
    flagging_mode="never",
)


if __name__ == "__main__":
    demo.launch()
