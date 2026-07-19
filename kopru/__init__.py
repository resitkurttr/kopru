# -*- coding: utf-8 -*-
"""
Köprü — Özgün AI Gateway
 Çoklu provider, tek endpoint, otomatik fallback.
"""
from .router import Router
from .gateway import create_app, app

__version__ = "1.0.0"
__all__ = ["Router", "create_app", "app"]
