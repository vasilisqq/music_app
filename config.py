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
# Piano reduction / musicality knobs
# ---------------------------------------------------------------------------

# Enable "soft" key/scale locking in the final MIDI reduction.
# This tries to reduce chromatic out-of-key artifacts by snapping only 1-semitone
# mistakes to the nearest pitch in the estimated key.
ENABLE_KEY_LOCK: bool = True

# Maximum semitone shift allowed by key-lock (1 == soft).
KEY_LOCK_MAX_SHIFT: int = 1

# If True, do not change pitches if snapping would move a note more than KEY_LOCK_MAX_SHIFT.
# (kept explicit for readability / future extension)
KEY_LOCK_SOFT: bool = True
