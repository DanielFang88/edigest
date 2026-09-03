"""Network compatibility helpers for local clients."""
from contextlib import contextmanager
import socket


@contextmanager
def prefer_ipv4():
    """Use IPv4 for one synchronous request when IPv6 has no usable route."""
    original = socket.getaddrinfo

    def ipv4_getaddrinfo(*args, **kwargs):
        return [item for item in original(*args, **kwargs) if item[0] == socket.AF_INET]

    socket.getaddrinfo = ipv4_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original
