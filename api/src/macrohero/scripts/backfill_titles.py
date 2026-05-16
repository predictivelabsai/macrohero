"""Backfill ChatSession.title with LLM-summarized titles.

Existing sessions written under the old 60-char `…` truncation have the
original message text discarded — only the truncated string was stored. This
script walks every session, fetches its first user message from
ChatMessage(ordinal=0, role='user'), and calls the same `summarize_title`
helper the live chat router uses for new sessions.

Usage (from the api/ directory):

    uv run python -m macrohero.scripts.backfill_titles            # apply
    uv run python -m macrohero.scripts.backfill_titles --dry-run  # preview
    uv run python -m macrohero.scripts.backfill_titles --all      # ignore the
        # "looks-already-summarized" heuristic and re-title every session
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import asc, select

from macrohero.chat.title import summarize_title
from macrohero.db.models import ChatMessage, ChatSession
from macrohero.db.session import make_session

logger = logging.getLogger("backfill_titles")


def _looks_already_summarized(title: str) -> bool:
    """Skip sessions whose title is clearly a clean LLM output already — no
    trailing ellipsis, not the literal placeholder, not empty."""
    if not title:
        return False
    if title == "New chat":
        return False
    if title.endswith("…") or title.endswith("..."):
        return False
    return True


async def _first_user_message(db, session_id) -> str | None:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        .order_by(asc(ChatMessage.ordinal))
        .limit(1)
    )
    row = (await db.execute(stmt)).scalars().first()
    return row.content if row is not None else None


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the DB.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-title every session (default skips ones that already look clean).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    async with make_session() as db:
        sessions = (await db.execute(select(ChatSession).order_by(ChatSession.created_at))).scalars().all()

    total = len(sessions)
    logger.info("found %d sessions; dry_run=%s all=%s", total, args.dry_run, args.all)

    updated = 0
    skipped = 0
    failed = 0

    for i, session in enumerate(sessions, start=1):
        if not args.all and _looks_already_summarized(session.title):
            skipped += 1
            logger.info("[%d/%d] skip %s (title already clean): %r", i, total, session.id, session.title)
            continue

        async with make_session() as db:
            content = await _first_user_message(db, session.id)

        if not content:
            skipped += 1
            logger.info("[%d/%d] skip %s (no user message)", i, total, session.id)
            continue

        try:
            new_title = await summarize_title(content)
        except Exception:
            failed += 1
            logger.exception("[%d/%d] summarize failed for %s", i, total, session.id)
            continue

        if new_title is None:
            failed += 1
            logger.warning("[%d/%d] summarizer returned None for %s", i, total, session.id)
            continue

        logger.info("[%d/%d] %s: %r -> %r", i, total, session.id, session.title, new_title)

        if args.dry_run:
            continue

        try:
            async with make_session() as db:
                row = await db.get(ChatSession, session.id)
                if row is None:
                    continue
                row.title = new_title
                await db.commit()
            updated += 1
        except Exception:
            failed += 1
            logger.exception("[%d/%d] DB update failed for %s", i, total, session.id)

    logger.info("done: updated=%d skipped=%d failed=%d total=%d", updated, skipped, failed, total)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
