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

# "other" is the noisiest stem, but making it too strict can delete almost
# everything. These defaults are softer to keep more musical content.
BP_VOCALS_ONSET_THRESHOLD: float = 0.42
BP_VOCALS_FRAME_THRESHOLD: float = 0.25
BP_VOCALS_MIN_NOTE_LENGTH: float = 45.0

BP_BASS_ONSET_THRESHOLD: float = 0.50
BP_BASS_FRAME_THRESHOLD: float = 0.30
BP_BASS_MIN_NOTE_LENGTH: float = 70.0

# softened vs previous commit (to avoid overly sparse MIDI)
BP_OTHER_ONSET_THRESHOLD: float = 0.52
BP_OTHER_FRAME_THRESHOLD: float = 0.30
BP_OTHER_MIN_NOTE_LENGTH: float = 70.0

# ---------------------------------------------------------------------------
# Piano reduction / musicality knobs
# ---------------------------------------------------------------------------

ENABLE_KEY_LOCK: bool = True
KEY_LOCK_MAX_SHIFT: int = 1

# Melody selection
MELODY_GRID_SUBDIV: int = 4  # 1/16 instead of 1/8 => more rhythmic detail
MELODY_CANDIDATES_PER_SLICE: int = 8
MELODY_VELOCITY_WEIGHT: float = 1.00
MELODY_PITCH_WEIGHT: float = 0.02
MELODY_JUMP_PENALTY: float = 0.08

# Harmony extraction from OTHER
HARMONY_GRID_SUBDIV: int = 2   # 1/8 (less "too long" than 1/4)
HARMONY_MAX_NOTES: int = 3
OTHER_MIN_VEL: int = 30
OTHER_MIN_DUR: float = 0.06

# Left hand texture (from BASS stem)
LH_MAX_NOTES: int = 4
LH_SPAN_LIMIT: int = 19
