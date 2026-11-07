"""Deterministic tests: no network and no real LLM calls."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.voice_intent import WakeIntent, classify_wake_intent


def fake_client(label):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=label))]
    )
    return client


@pytest.mark.parametrize("label,expected", [
    ("WAKE", WakeIntent.WAKE),
    ("IGNORE", WakeIntent.IGNORE),
    ("UNCERTAIN", WakeIntent.UNCERTAIN),
    ("WAKE because yes", WakeIntent.UNCERTAIN),
    ("```WAKE```", WakeIntent.UNCERTAIN),
    ("", WakeIntent.UNCERTAIN),
])
def test_strict_model_output(label, expected):
    client = fake_client(label)
    decision = classify_wake_intent("TraceDesk, can you help?", client_factory=lambda: client)
    assert decision.intent is expected
    client.chat.completions.create.assert_called_once()


def test_empty_input_does_not_call_llm():
    factory = Mock()
    assert classify_wake_intent("   ", client_factory=factory).intent is WakeIntent.IGNORE
    factory.assert_not_called()


def test_oversized_input_fails_closed():
    factory = Mock()
    result = classify_wake_intent("a" * 501, client_factory=factory)
    assert result.intent is WakeIntent.UNCERTAIN
    assert not result.should_wake
    factory.assert_not_called()


def test_network_error_fails_closed():
    factory = Mock(side_effect=TimeoutError("network down"))
    result = classify_wake_intent("Can you help me?", client_factory=factory)
    assert result.intent is WakeIntent.UNCERTAIN
    assert not result.should_wake


def test_only_transcript_sent_as_user_message():
    client = fake_client("WAKE")
    text = "يا تريس ديسك، عندي مشكلة VPN"
    classify_wake_intent(text, client_factory=lambda: client)
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["messages"][1] == {"role": "user", "content": text}
    assert kwargs["temperature"] == 0
    assert kwargs["max_tokens"] == 8
