# -*- coding: utf-8 -*-
"""
Köprü — Özgün AI Gateway (OmniRoute benzeri)
 Provider management, API key sistemi, auto-fallback.
"""
from .router import Router
from .gateway import create_app, app
from .database import init_db

__version__ = "2.0.0"
__all__ = ["Router", "create_app", "app", "init_db"]
