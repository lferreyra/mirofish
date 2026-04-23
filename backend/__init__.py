"""MiroFish backend package marker.

Declares `backend` as a Python package so `python -m backend.eval.runner`
resolves and so modules inside `backend/eval/` can reach `backend/app/*`
via relative imports.
"""
