"""Syntax backend — server-authoritative FastAPI service.

The client is treated as hostile (see GDD §8): correct answers, the score clock,
and attempt enforcement all live here and never ship to the browser.
"""

__version__ = "0.1.0"
