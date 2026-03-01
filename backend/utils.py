"""Shared utilities: JSON-safe values for API responses."""
from __future__ import annotations

import math
from typing import Any

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _to_python_number(obj: Any) -> Any:
    """Convert numpy/pandas scalar to Python type for JSON."""
    if _HAS_NUMPY and hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return obj.item()
        except Exception:
            pass
    if hasattr(obj, "isoformat") and callable(getattr(obj, "isoformat")):  # datetime / Timestamp
        try:
            return obj.isoformat()
        except Exception:
            pass
    return obj


def sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Inf and non-JSON-serializable values so FastAPI can serialize."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return int(obj) if -2**53 <= obj <= 2**53 else None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    # numpy/pandas scalar or datetime
    converted = _to_python_number(obj)
    if converted is not obj:
        return sanitize_for_json(converted)
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if _HAS_NUMPY and type(obj).__module__ == "numpy" and hasattr(obj, "tolist"):
        try:
            return sanitize_for_json(obj.tolist())
        except Exception:
            return None
    return obj
