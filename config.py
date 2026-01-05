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
# Basic Pitch tuning (per stem)
# ---------------------------------------------------------------------------

# Idea: "other" is the noisiest stem, so use stricter thresholds there.
# Values are intentionally conservative; tune on your own examples.
BP_VOCALS_ONSET_THRESHOLD: float = 0.42
BP_VOCALS_FRAME_THRESHOLD: float = 0.25
BP_VOCALS_MIN_NOTE_LENGTH: float = 45.0

BP_BASS_ONSET_THRESHOLD: float = 0.50
BP_BASS_FRAME_THRESHOLD: float = 0.30
BP_BASS_MIN_NOTE_LENGTH: float = 70.0

BP_OTHER_ONSET_THRESHOLD: float = 0.62
BP_OTHER_FRAME_THRESHOLD: float = 0.38
BP_OTHER_MIN_NOTE_LENGTH: float = 110.0

# ---------------------------------------------------------------------------
# Piano reduction / musicality knobs
# ---------------------------------------------------------------------------

# Enable "soft" key/scale locking in the final MIDI reduction.
# This tries to reduce chromatic out-of-key artifacts by snapping only 1-semitone
# mistakes to the nearest pitch in the estimated key.
ENABLE_KEY_LOCK: bool = True

# Maximum semitone shift allowed by key-lock (1 == soft).
KEY_LOCK_MAX_SHIFT: int = 1

# Melody selection: smoother (less jumping) lead line.
MELODY_CANDIDATES_PER_SLICE: int = 6
MELODY_VELOCITY_WEIGHT: float = 1.00
MELODY_PITCH_WEIGHT: float = 0.02
MELODY_JUMP_PENALTY: float = 0.10  # higher => smoother but can get stuck

# Harmony extraction from OTHER
HARMONY_GRID_SUBDIV: int = 1   # 1/4 (slower harmonic rhythm)
HARMONY_MAX_NOTES: int = 4
OTHER_MIN_VEL: int = 38
OTHER_MIN_DUR: float = 0.08

# Left hand texture (from BASS stem)
LH_MAX_NOTES: int = 4
LH_SPAN_LIMIT: int = 19
