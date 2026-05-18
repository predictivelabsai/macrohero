"""Shared pytest fixtures for the numerics service.

The api/'s pytest setup required monkeypatching DATABASE_URL/CLERK_* env vars
because the old Settings class declared them as required fields. The numerics
service's Settings only requires MASSIVE_* (and even those are optional), so no
shared-env-var fixture is needed here. This file exists as a placeholder for
future shared fixtures.
"""
