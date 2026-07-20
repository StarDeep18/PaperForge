"""
API Rate Limiter.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance utilizing client IP addresses as keys
limiter = Limiter(key_func=get_remote_address)
