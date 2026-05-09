from fasthtml.common import *
from monsterui.all import *


def NavBar_(user=None):
    if user:
        auth_section = DivLAligned(
            Span(user.get("name", ""), cls="text-sm"),
            A("Logout", href="/auth/logout", cls="uk-button uk-button-default uk-button-small"),
            cls="gap-2",
        )
    else:
        auth_section = DivLAligned(
            A("Login", href="/login", cls="uk-button uk-button-default uk-button-small"),
            A("Register", href="/register", cls="uk-button uk-button-primary uk-button-small"),
            cls="gap-2",
        )

    return Div(
        A(DivLAligned(
            UkIcon("trending-up", height=22),
            Div(
                Span("MacroHero", cls="text-lg font-bold"),
                Span("beta", style="font-size:0.5rem; color:#9ca3af; vertical-align:super; margin-left:2px;"),
            ),
            cls="gap-2",
        ), href="/", cls="no-underline"),
        DivLAligned(auth_section, cls="gap-3"),
        cls="app-nav",
    )


def page_shell(*content, title="MacroHero"):
    return Title(title), NavBar_(), Container(*content)
