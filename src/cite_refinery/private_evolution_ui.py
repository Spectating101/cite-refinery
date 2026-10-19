"""Static assets for private evidence-evolution interface.

Only the loopback private API serves these; HTML contains no sensitive data.
"""
from pathlib import Path

STATIC = Path(__file__).with_name("private_evolution_assets")

def load_asset(name: str) -> str:
    if name not in {"index.html", "app.js", "app.css"}:
        raise ValueError("unsupported asset")
    return (STATIC / name).read_text(encoding="utf-8")
