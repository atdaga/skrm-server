"""Business logic layer for the application.

This module contains the core business logic separated from HTTP concerns.
Logic functions raise domain-specific exceptions that are translated to HTTP
responses by the route handlers.
"""
