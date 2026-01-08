from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent

PROJECT_HUB_DIR = ROOT / ".torch_hub"
PROJECT_HUB_DIR.mkdir(parents=True, exist_ok=True)
torch.hub.set_dir(str(PROJECT_HUB_DIR))

BP_REPO_ROOT = ROOT / "third_party" / "basic_pitch_torch"
sys.path.insert(0, str(BP_REPO_ROOT))

# ---------------------------------------------------------------------------
# Pipeline switches
# ---------------------------------------------------------------------------

USE_ONLY_OTHER: bool = True
OTHER_USE_QUANTIZATION: bool = True

# Quantization settings for OTHER (when OTHER_USE_QUANTIZATION=True)
OTHER_Q_SUBDIVISIONS: int = 8
OTHER_Q_START_MODE: str = "floor"
OTHER_Q_MERGE_GAP: float = 0.0
OTHER_Q_KEEP_REPEATED_NOTES: bool = True

# Dense playable from OTHER
OTHER_DENSE_MODE: bool = True

# Make texture denser (more notes kept)
OTHER_DENSE_GRID_SUBDIV: int = 12
OTHER_DENSE_MAX_NOTES: int = 12
OTHER_DENSE_HAND_SPAN: int | None = None

# Longer hold => more short notes survive slicing
OTHER_DENSE_HOLD_SEC: float = 0.18

# Very low threshold; rely on later limiting instead of pre-filtering
OTHER_DENSE_MIN_VEL: int = 1

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
