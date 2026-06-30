"""Shared SlowAPI limiter instance.

Defined in its own module so that ``main.py`` (which wires the limiter into
``app.state``) and the routers (which decorate endpoints) can both import it
without creating a circular dependency.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
