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

# Quantization for OTHER makes timing/durations more uniform and often removes
# micro-rhythm details. For denser + more varied results, keep it off by default.
OTHER_USE_QUANTIZATION: bool = False

# Quantization settings for OTHER (when OTHER_USE_QUANTIZATION=True)
OTHER_Q_SUBDIVISIONS: int = 16
OTHER_Q_START_MODE: str = "floor"
OTHER_Q_MERGE_GAP: float = 0.0
OTHER_Q_KEEP_REPEATED_NOTES: bool = True

# ---------------------------------------------------------------------------
# NEW: Event-based OTHER (attack-preserving)
# ---------------------------------------------------------------------------

# If True, OTHER in dense mode is produced by:
# - quantizing note *starts* to the beat grid
# - keeping note ends mostly intact (only fixed when end <= start)
# - limiting polyphony using event-based pruning (no probe_t slicing)
OTHER_EVENT_MODE: bool = True
OTHER_EVENT_MIN_DUR_STEPS: int = 1
# Grid used to quantize starts for OTHER_EVENT_MODE
OTHER_EVENT_GRID_SUBDIV: int = 24

# How to quantize note starts to the grid
OTHER_EVENT_START_MODE: str = "floor"  # 'nearest' | 'floor' | 'ceil'

# Max simultaneously active notes (polyphony cap) for OTHER_EVENT_MODE
OTHER_EVENT_MAX_POLY: int = 10

# When pruning, prefer louder notes (default) or higher notes
OTHER_EVENT_PREFER: str = "max_velocity"  # 'max_velocity' | 'max_pitch'

# Event-mode cleaning: drop ultra-short notes early (seconds)
OTHER_EVENT_MIN_DUR_SEC: float = 0.1

# ---------------------------------------------------------------------------
# Dense playable from OTHER (legacy slicing)
# ---------------------------------------------------------------------------

OTHER_DENSE_MODE: bool = True

# Make texture denser (more notes kept)
OTHER_DENSE_GRID_SUBDIV: int = 24
OTHER_DENSE_MAX_NOTES: int = 24
OTHER_DENSE_HAND_SPAN: int | None = 16

# Longer hold => fewer gaps when sampling active notes on a dense time grid.
OTHER_DENSE_HOLD_SEC: float = 0.5

# Very low threshold; rely on later limiting instead of pre-filtering
OTHER_DENSE_MIN_VEL: int = 1

# In dense mode still drop ultra-short "dust" notes (helps reduce gaps after re-slicing)
OTHER_DENSE_MIN_DUR_SEC: float = 0.03

# probe inside each time slice (too-large eps can miss very short notes)
OTHER_DENSE_PROBE_EPS_SEC: float = 1e-4

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

BP_OTHER_ONSET_THRESHOLD: float = 0.46
BP_OTHER_FRAME_THRESHOLD: float = 0.25

# Lower min note length to keep short notes that were previously dropped.
BP_OTHER_MIN_NOTE_LENGTH: float = 8.0

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
