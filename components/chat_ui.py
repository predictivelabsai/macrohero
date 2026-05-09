from fasthtml.common import *
from monsterui.all import *


def ChatMessageBubble(role: str, content: str):
    cls = "chat-user" if role == "user" else "chat-assistant"
    return Div(
        Div(NotStr(content) if role == "assistant" else content, cls="text-sm"),
        cls=cls,
    )
