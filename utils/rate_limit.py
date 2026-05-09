import time
from collections import defaultdict, deque
from threading import Lock

_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    now = time.time()
    with _lock:
        q = _hits[key]
        cutoff = now - window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= max_requests:
            return False
        q.append(now)
        return True
