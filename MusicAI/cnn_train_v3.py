import os
import numpy as np
import pandas as pd
import librosa
import matplotlib.pyplot as plt

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau


# ============================================================
# 1. SETTINGS
# ============================================================
BASE_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")

CLIP_SECONDS = 5       # KEEP at 3. Smaller = more clips = SLOWER (not faster!)
N_MELS       = 128
TIME_STEPS   = 128
SR           = 22050

# ---- SPEED CONTROLS (these are what actually make epochs faster) ----
MAX_CLIPS_PER_SONG = 20    # cap clips per song. Lower = faster. THE main lever.
AUGMENT            = True   # x3 the training clips. Set False for big speedup.
BATCH_SIZE         = 64     # bigger = often faster per epoch on CPU
EPOCHS             = 50

# ---- FAST_MODE: flip to True for quick test runs while developing ----
# It overrides the speed settings above with aggressive values.
FAST_MODE = False
if FAST_MODE:
    MAX_CLIPS_PER_SONG = 3
    AUGMENT            = False
    EPOCHS             = 25
    print("⚡ FAST_MODE on: fewer clips, no augmentation, fewer epochs.")

USE_CACHE = True


# ============================================================
# 2. AUDIO -> CLIPS -> SPECTROGRAM HELPERS
# ============================================================
def split_into_clips(y):
    clip_len = CLIP_SECONDS * SR
    step = clip_len // 2          # 50% overlap -> ~2x the clips
    clips = []
    for start in range(0, len(y) - clip_len + 1, step):
        clips.append(y[start:start + clip_len])
        if len(clips) >= MAX_CLIPS_PER_SONG:
            break
    if not clips and len(y) > 0:
        clips = [np.pad(y, (0, clip_len - len(y)))]
    return clips


def audio_augmentations(y):
    versions = []
    try:
        versions.append(librosa.effects.pitch_shift(y, sr=SR, n_steps=2))
    except Exception:
        pass
    versions.append(y + 0.005 * np.random.randn(len(y)))
    return versions


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
# 3. COLLECT SONGS
# ============================================================
def collect_songs():
    songs = []
    for genre in os.listdir(BASE_DIR):
        genre_path = os.path.join(BASE_DIR, genre)
        if not os.path.isdir(genre_path) or genre.startswith("."):
            continue
        for filename in os.listdir(genre_path):
            if not filename.lower().endswith((".mp3", ".wav")):
                continue
            songs.append((os.path.join(genre_path, filename), genre, filename))
    return songs


# ============================================================
# 4. BUILD SPECTROGRAM SET
# ============================================================
def build_set(song_list, augment=False):
    X, y = [], []
    for file_path, genre, filename in song_list:
        try:
            audio, _ = librosa.load(file_path, sr=SR)
        except Exception as e:
            print(f"  ⚠️ Skipped {filename}: {type(e).__name__}: {e}")
            continue
        for clip in split_into_clips(audio):
            X.append(spectrogram_from_audio(clip))
            y.append(genre)
            if augment:
                for aug_clip in audio_augmentations(clip):
                    X.append(spectrogram_from_audio(aug_clip))
                    y.append(genre)
    X = np.array(X)[..., np.newaxis]
    return X, np.array(y)


# ============================================================
# 5. MODEL
# ============================================================
def build_model(input_shape, num_classes):
    reg = tf.keras.regularizers.l2(0.001)
    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv2D(32, (3, 3), activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(128, activation="relu", kernel_regularizer=reg),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation="softmax")
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model


# ============================================================
# 6. MAIN
# ============================================================
def main():
    if USE_CACHE and os.path.exists("cnn3_X_train.npy"):
        print("Loading cached spectrograms...")
        X_train = np.load("cnn3_X_train.npy")
        X_test  = np.load("cnn3_X_test.npy")
        y_train = np.load("cnn3_y_train.npy", allow_pickle=True)
        y_test  = np.load("cnn3_y_test.npy", allow_pickle=True)
    else:
        songs = collect_songs()
        if len(songs) == 0:
            print("❌ No songs found. Check BASE_DIR and your folders.")
            return

        genres_per_song = [s[1] for s in songs]
        try:
            train_songs, test_songs = train_test_split(
                songs, test_size=0.2, random_state=42, stratify=genres_per_song
            )
        except ValueError:
            train_songs, test_songs = train_test_split(
                songs, test_size=0.2, random_state=42
            )

        print(f"Building TRAINING set ({len(train_songs)} songs, "
              f"augment={AUGMENT}, max {MAX_CLIPS_PER_SONG} clips/song)...")
        X_train, y_train = build_set(train_songs, augment=AUGMENT)

        print(f"Building TEST set ({len(test_songs)} songs, no augment)...")
        X_test, y_test = build_set(test_songs, augment=False)

        np.save("cnn3_X_train.npy", X_train)
        np.save("cnn3_X_test.npy", X_test)
        np.save("cnn3_y_train.npy", y_train)
        np.save("cnn3_y_test.npy", y_test)

    print(f"\nTrain clips: {len(X_train)}   Test clips: {len(X_test)}")
    print("(If this number is huge, lower MAX_CLIPS_PER_SONG or set AUGMENT=False.)")

    le = LabelEncoder()
    le.fit(np.concatenate([y_train, y_test]))
    genres = list(le.classes_)
    y_train_enc = le.transform(y_train)
    y_test_enc  = le.transform(y_test)
    print("Genres:", genres)

    weights = compute_class_weight("balanced",
                                   classes=np.unique(y_train_enc), y=y_train_enc)
    class_weights = dict(enumerate(weights))

    model = build_model(X_train.shape[1:], num_classes=len(genres))
    model.summary()

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-5),
    ]

    history = model.fit(
        X_train, y_train_enc,
        validation_data=(X_test, y_test_enc),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )

    y_pred = model.predict(X_test).argmax(axis=1)
    acc = accuracy_score(y_test_enc, y_pred)
    print("\n============================================")
    print(f"  TEST ACCURACY (per clip): {acc * 100:.1f}%")
    print("============================================")
    print(classification_report(y_test_enc, y_pred, target_names=genres))

    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="train")
    plt.plot(history.history["val_accuracy"], label="test")
    plt.title("Accuracy"); plt.xlabel("epoch"); plt.legend()
    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="train")
    plt.plot(history.history["val_loss"], label="test")
    plt.title("Loss"); plt.xlabel("epoch"); plt.legend()
    plt.tight_layout()
    plt.savefig("cnn3_training_curves.png", dpi=120)
    print("📈 Saved -> cnn3_training_curves.png")

    cm = confusion_matrix(y_test_enc, y_pred)
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap="Blues")
    plt.colorbar()
    plt.xticks(range(len(genres)), genres, rotation=45, ha="right")
    plt.yticks(range(len(genres)), genres)
    plt.xlabel("Predicted"); plt.ylabel("Actual"); plt.title("Confusion Matrix")
    for i in range(len(genres)):
        for j in range(len(genres)):
            plt.text(j, i, cm[i, j], ha="center", va="center")
    plt.tight_layout()
    plt.savefig("cnn3_confusion_matrix.png", dpi=120)
    print("📊 Saved -> cnn3_confusion_matrix.png")

    model.save("genre_cnn_v3.keras")
    np.save("genre_classes_v3.npy", np.array(genres))
    print("💾 Saved -> genre_cnn_v3.keras")


if __name__ == "__main__":
    main()
