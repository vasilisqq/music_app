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

# "other" often contains the lead for non-vocal tracks. If it's too strict,
# the result becomes sparse and "stretched".
BP_VOCALS_ONSET_THRESHOLD: float = 0.42
BP_VOCALS_FRAME_THRESHOLD: float = 0.25
BP_VOCALS_MIN_NOTE_LENGTH: float = 45.0

BP_BASS_ONSET_THRESHOLD: float = 0.50
BP_BASS_FRAME_THRESHOLD: float = 0.30
BP_BASS_MIN_NOTE_LENGTH: float = 70.0

# soften OTHER even more (keep more notes)
BP_OTHER_ONSET_THRESHOLD: float = 0.48
BP_OTHER_FRAME_THRESHOLD: float = 0.27
BP_OTHER_MIN_NOTE_LENGTH: float = 55.0

# ---------------------------------------------------------------------------
# Piano reduction / musicality knobs
# ---------------------------------------------------------------------------

ENABLE_KEY_LOCK: bool = True
KEY_LOCK_MAX_SHIFT: int = 1

# Melody selection
MELODY_GRID_SUBDIV: int = 4  # 1/16
MELODY_CANDIDATES_PER_SLICE: int = 8
MELODY_VELOCITY_WEIGHT: float = 1.00
MELODY_PITCH_WEIGHT: float = 0.02
MELODY_JUMP_PENALTY: float = 0.08

# Harmony extraction from OTHER
HARMONY_GRID_SUBDIV: int = 2   # 1/8
HARMONY_MAX_NOTES: int = 3

# OTHER post-filters (two levels)
# - MELODY filters: softer to keep lead line
# - HARMONY filters: stricter to avoid noisy chord soup
OTHER_MELODY_MIN_VEL: int = 18
OTHER_MELODY_MIN_DUR: float = 0.03

OTHER_HARMONY_MIN_VEL: int = 22
OTHER_HARMONY_MIN_DUR: float = 0.04

# Left hand texture (from BASS stem)
LH_MAX_NOTES: int = 4
LH_SPAN_LIMIT: int = 19
