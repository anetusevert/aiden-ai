"""Middleware for Aiden.ai API."""

from src.middleware.request_id import RequestIdMiddleware

__all__ = ["RequestIdMiddleware"]
