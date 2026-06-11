"""Common exceptions for AI model adapter providers."""

from __future__ import annotations


class ProviderDependencyError(RuntimeError):
    """Raised when an optional provider dependency is unavailable."""
