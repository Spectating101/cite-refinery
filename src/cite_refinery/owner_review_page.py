"""Build an offline, single-file review page from the existing browser assets.

No private registry, receipt, backend endpoint, or external asset is embedded.
Requires the repository's prototype assets (or an explicitly supplied directory).
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
import secrets
from typing import Any

from .owner_review_contract import validate_owner_review_response


def render_owner_review_page(pack: dict[str, Any], *, assets_dir: str | Path | None = None) -> str:
    errors = validate_owner_review_response(pack)
    if errors:
        raise ValueError('invalid review pack: ' + '; '.join(errors))
    assets = Path(assets_dir) if assets_dir is not None else Path(__file__).resolve().parents[2] / 'prototype'
    required = ('review.html', 'review.js', 'owner-review-contract.js', 'styles.css')
    if not all((assets / name).is_file() for name in required):
        raise ValueError('review assets not found; use the repository checkout or --assets-dir pointing to prototype/')
    page = (assets / 'review.html').read_text(encoding='utf-8')
    styles = (assets / 'styles.css').read_text(encoding='utf-8')
    nonce = secrets.token_hex(16)
    policy = ("default-src 'none'; connect-src 'none'; img-src 'none'; font-src 'none'; "
              f"script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")
    page = page.replace('<meta charset="utf-8" />', '<meta charset="utf-8" />\n  <meta http-equiv="Content-Security-Policy" content="' + escape(policy, quote=True) + '" />')
    page = page.replace('<link rel="stylesheet" href="styles.css" />', '<style>' + styles + '</style>')
    # Escape HTML-significant characters even in non-executable JSON script data.
    payload = json.dumps(pack, ensure_ascii=False, allow_nan=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    embedded = f'<script id="preloadedReview" type="application/json" nonce="{nonce}">{payload}</script>\n'
    for name in ('owner-review-contract.js', 'review.js'):
        script = (assets / name).read_text(encoding='utf-8')
        if '</script' in script.lower():
            raise ValueError('review script cannot contain an inline closing-script delimiter')
        replacement = f'<script nonce="{nonce}">{script}</script>'
        if name == 'owner-review-contract.js':
            replacement = embedded + replacement
        page = page.replace(f'<script src="{name}"></script>', replacement)
    page = re.sub(r'<nav>.*?</nav>', '<span class="review-note">Offline review · nothing is sent</span>', page, flags=re.S)
    page = page.replace('href="index.html"', 'href="#reviewApp"')
    return page
