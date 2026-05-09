from fasthtml.common import *
from monsterui.all import *


def NavBar_(user=None):
    if user:
        auth_section = DivLAligned(
            Span(user.get("name", ""), cls="text-sm", style="color:#e2e8f0;"),
            A("Logout", href="/auth/logout", style="color:#94a3b8; font-size:0.75rem; text-decoration:none;"),
            cls="gap-3",
        )
    else:
        auth_section = DivLAligned(
            A("Login", href="/login", style="color:#e2e8f0; font-size:0.8rem; text-decoration:none;"),
            A("Register", href="/register",
              style="background:#3b82f6; color:white; font-size:0.75rem; padding:4px 14px; border-radius:20px; text-decoration:none;"),
            cls="gap-3",
        )

    return Div(
        A(DivLAligned(
            UkIcon("trending-up", height=18, style="color:#3b82f6;"),
            Span("MacroHero", style="font-size:1rem; font-weight:700; color:#f8fafc;"),
            cls="gap-2",
        ), href="/", cls="no-underline"),
        DivLAligned(auth_section, cls="gap-3"),
        cls="app-nav",
    )


def page_shell(*content, title="MacroHero"):
    return Title(title), NavBar_(), Container(*content)
