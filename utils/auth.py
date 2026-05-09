import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_client_ip(req) -> str:
    try:
        headers = getattr(req, "headers", {}) or {}
        fwd = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
        if fwd:
            return fwd.split(",")[0].strip()
        real = headers.get("x-real-ip") or headers.get("X-Real-IP") or ""
        if real:
            return real.strip()
        client = getattr(req, "client", None)
        if client and getattr(client, "host", None):
            return client.host
    except Exception:
        pass
    return "unknown"
