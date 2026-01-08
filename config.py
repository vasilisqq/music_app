from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent

# Torch hub cache inside repo
PROJECT_HUB_DIR = ROOT / ".torch_hub"
PROJECT_HUB_DIR.mkdir(parents=True, exist_ok=True)
torch.hub.set_dir(str(PROJECT_HUB_DIR))

# basic-pitch-torch as vendored dependency
BP_REPO_ROOT = ROOT / "third_party" / "basic_pitch_torch"
sys.path.insert(0, str(BP_REPO_ROOT))

# ---------------------------------------------------------------------------
# Pipeline switches
# ---------------------------------------------------------------------------

USE_ONLY_OTHER: bool = True

OTHER_USE_QUANTIZATION: bool = True

# Quantization settings for OTHER (when OTHER_USE_QUANTIZATION=True)
OTHER_Q_SUBDIVISIONS: int = 8
OTHER_Q_START_MODE: str = "floor"   # safer for repeated notes
OTHER_Q_MERGE_GAP: float = 0.0      # avoid merging repeated same-pitch notes
OTHER_Q_KEEP_REPEATED_NOTES: bool = True

# If True, build playable more directly from OTHER (dense texture).
OTHER_DENSE_MODE: bool = True

# Dense mode: more notes per slice for a fuller transcription.
OTHER_DENSE_GRID_SUBDIV: int = 8
OTHER_DENSE_MAX_NOTES: int = 8
OTHER_DENSE_HAND_SPAN: int | None = None  # disable span collapsing

# When True, keep more notes by extending each chosen note by "hold" seconds.
# This increases the chance a note stays active at the probe time in the slice.
OTHER_DENSE_HOLD_SEC: float = 0.08

# Filter out extremely low-velocity junk in dense mode.
OTHER_DENSE_MIN_VEL: int = 6

# ---------------------------------------------------------------------------
# Stem silence detection
# ---------------------------------------------------------------------------

STEM_SILENCE_RMS_DBFS: float = -62.0
STEM_SILENCE_PEAK_DBFS: float = -52.0

# ---------------------------------------------------------------------------
# Basic Pitch tuning (per stem)
# ---------------------------------------------------------------------------

BP_VOCALS_ONSET_THRESHOLD: float = 0.42
BP_VOCALS_FRAME_THRESHOLD: float = 0.25
BP_VOCALS_MIN_NOTE_LENGTH: float = 45.0

BP_BASS_ONSET_THRESHOLD: float = 0.50
BP_BASS_FRAME_THRESHOLD: float = 0.30
BP_BASS_MIN_NOTE_LENGTH: float = 70.0

BP_OTHER_ONSET_THRESHOLD: float = 0.48
BP_OTHER_FRAME_THRESHOLD: float = 0.27
BP_OTHER_MIN_NOTE_LENGTH: float = 55.0

# ---------------------------------------------------------------------------
# Piano reduction / musicality knobs
# ---------------------------------------------------------------------------

# Key-lock can push notes to the nearest scale tone. If the key estimate is wrong
# (very common on dense/polyphonic MIDI), it produces "wrong harmony".
ENABLE_KEY_LOCK: bool = False
KEY_LOCK_MAX_SHIFT: int = 1

MELODY_GRID_SUBDIV: int = 4
MELODY_CANDIDATES_PER_SLICE: int = 10
MELODY_VELOCITY_WEIGHT: float = 1.00
MELODY_PITCH_WEIGHT: float = 0.015
MELODY_JUMP_PENALTY: float = 0.06

HARMONY_GRID_SUBDIV: int = 2
HARMONY_MAX_NOTES: int = 4

OTHER_MELODY_MIN_VEL: int = 10
OTHER_MELODY_MIN_DUR: float = 0.015

OTHER_HARMONY_MIN_VEL: int = 14
OTHER_HARMONY_MIN_DUR: float = 0.02

LH_MAX_NOTES: int = 4
LH_SPAN_LIMIT: int = 19
