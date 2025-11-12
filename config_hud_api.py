#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HUD API functions (hud_start, hud_push, etc.)
Extracted from config_utils.py (lines 6589-6672)
"""

from config_core import *
from config_auth import HUD_ENABLED, HUD_OPACITY

# Lazy import to avoid circular import issues
def _get_hud_module():
    import config_hud
    return config_hud

def hud_start():
    """Create HUD on main thread (no mainloop yet)."""
    hud_module = _get_hud_module()
    if not HUD_ENABLED:
        print("HUD disabled by configuration, but enforced ON; continuing.", file=sys.stderr)
    if hud_module._hud is None:
        hud_module._hud = hud_module.OldCompactHUD(opacity=HUD_OPACITY)

def hud_run_mainloop_blocking():
    """Enter Tk mainloop (must be called from main thread)."""
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        hud_module._hud.mainloop()

def hud_push(msg: str):
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        level = "muted"
        low = (msg or "").lower()
        if any(x in low for x in ["error", "[err]", "failed", "fail"]): level = "err"
        elif any(x in low for x in ["warn", "[warn]", "skip", "skipping"]): level = "warn"
        elif any(x in low for x in ["connected", "done", "upload ok", "importer ok", "parsed"]): level = "ok"
        hud_module._hud.push(msg, level)
        # Also append to live log pane if present
        try:
            if hasattr(hud_module._hud, "_append_ai_text"):
                hud_module._hud._append_ai_text(msg + "\n", level)
        except Exception:
            pass

def hud_loader_show(msg: str = "Loading…"):
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        try:
            hud_module._hud._inbox.put_nowait(("LOADER_SHOW", msg))
        except Exception:
            pass

def hud_loader_update(msg: str):
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        try:
            hud_module._hud._inbox.put_nowait(("LOADER_MSG", msg))
        except Exception:
            pass

def hud_loader_hide():
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        try:
            hud_module._hud._inbox.put_nowait(("LOADER_HIDE", ""))
        except Exception:
            pass

def hud_counts(q: int, r: int, d: int, e: int):
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        hud_module._hud.set_counts(q, r, d, e)

def hud_set_paused(paused: bool):
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        hud_module._hud.set_paused(paused)

def hud_is_paused() -> bool:
    hud_module = _get_hud_module()
    if hud_module._hud is not None:
        return hud_module._hud.is_paused()
    return False

def hud_is_auto_run_enabled() -> bool:
    """Check if Auto Run is enabled in the queue UI"""
    hud_module = _get_hud_module()
    if hud_module._hud is not None and hasattr(hud_module._hud, '_auto_run_enabled'):
        try:
            return hud_module._hud._auto_run_enabled.get()
        except:
            return False
    return False  # Default to manual mode if not set

def hud_stop():
    # Tk mainloop ends when window is closed; nothing to do here
    pass

# ----------------------------
# Logging & helpers
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
log = logging.getLogger("queue-websites-poller")


