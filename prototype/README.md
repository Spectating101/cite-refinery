# Problem Commons browser prototype

This directory is a zero-dependency V0 for the public surface of the larger Problem Commons concept. It is intentionally **problem-first**: users browse living, evidence-backed problems and inspect what remains unsolved, the knowledge frontier, the capability frontier, contribution paths, authority boundaries, active attempts, and problem history.

Run it from any static HTTP server, for example:

```bash
cd prototype
python -m http.server 8000
```

Then open `http://localhost:8000`.

The sample records in `problems.json` are illustrative prototype content, not verified claims about named real organizations or locations.

The backing V0 lifecycle model is in `src/cite_refinery/problem_commons.py`; design boundaries and empirical test criteria are documented in `docs/PROBLEM_COMMONS_V0.md`.
