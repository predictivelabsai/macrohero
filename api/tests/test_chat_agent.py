from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from macrohero.chat.agent import _build_system_prompt, _make_llm, _to_lc_messages
from macrohero.config import get_settings


def test_chat_llm_uses_deepseek_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-test")
    get_settings.cache_clear()

    llm = _make_llm()

    # bind_tools returns a RunnableBinding wrapping the ChatOpenAI; unwrap to check settings.
    base = getattr(llm, "bound", llm)
    assert base.model_name == "deepseek-test"
    assert base.model_kwargs["parallel_tool_calls"] is False


def test_chat_prompt_is_macrohero_fx_scenario_assistant():
    prompt = _build_system_prompt()

    assert "MacroHero" in prompt
    assert "FX scenario-analysis" in prompt


def test_lc_message_conversion_keeps_system_prompt_first():
    messages = _to_lc_messages(
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
    )

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
