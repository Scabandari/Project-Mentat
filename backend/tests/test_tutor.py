from collections.abc import Iterator
from typing import Any, ClassVar

import httpx
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.llm.tutor import get_tutor_model, render_messages
from app.main import app
from tests.test_study import API, _deck_id, _first_of_type, _next, _session


class RecordingFake(FakeListChatModel):
    seen: ClassVar[list[Any]] = []

    async def _agenerate(self, messages: Any, *a: Any, **kw: Any) -> Any:
        RecordingFake.seen.append(messages)
        return await super()._agenerate(messages, *a, **kw)


@pytest.fixture
def fake_tutor() -> Iterator[RecordingFake]:
    model = RecordingFake(responses=["Think of it as **25%** of the final pot."])
    RecordingFake.seen = []
    app.dependency_overrides[get_tutor_model] = lambda: model
    yield model
    app.dependency_overrides.pop(get_tutor_model, None)


async def test_config_reports_tutor(client: httpx.AsyncClient, fake_tutor: RecordingFake) -> None:
    assert (await client.get(f"{API}/config")).json() == {"tutor_enabled": True}


async def test_tutor_requires_answer_then_explains(
    client: httpx.AsyncClient, fake_tutor: RecordingFake
) -> None:
    deck = await _deck_id(client, "pot-odds")
    s = await _session(client, mode="drill", deck_ids=[deck])
    p = await _first_of_type(client, s["id"], "bucket")
    url = f"{API}/instances/{p['instance_id']}/tutor"

    early = await client.post(url, json={})
    assert early.status_code == 409  # never explain before answering (would leak the key)

    await client.post(
        f"{API}/instances/{p['instance_id']}/answer", json={"response": 2, "latency_ms": 5000}
    )
    r = await client.post(url, json={"question": "why not 33%?"})
    assert r.status_code == 200, r.text
    assert "25%" in r.json()["message_md"]

    sent = " ".join(str(m.content) for m in RecordingFake.seen[-1])
    assert p["prompt"].split("**")[0] in sent  # problem included
    assert "why not 33%?" in sent
    assert "Worked solution" in sent


async def test_tutor_disabled_without_key(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_tutor_model] = lambda: None
    try:
        assert (await client.get(f"{API}/config")).json() == {"tutor_enabled": False}
        s = await _session(client, mode="drill")
        p = (await _next(client, s["id"]))["problem"]
        r = await client.post(f"{API}/instances/{p['instance_id']}/tutor", json={})
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_tutor_model, None)


def test_system_prompt_forbids_new_numbers() -> None:
    msgs = render_messages(
        prompt="p", scene="", student_answer="a", correct_answer="b", verdict="v",
        explanation="e", question="q",
    )  # fmt: skip
    assert "Never compute" in str(msgs[0].content)
