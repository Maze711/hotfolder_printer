"""Top‑level package for the hotfolder printer.

Provides a ``PROJECT_ROOT`` constant that points to the repository root.
All sub‑packages (engine, ui, services) can import it via ``from . import PROJECT_ROOT``.
"""
import os

# Two directories up from this file (app/__init__.py) gives the repository root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
