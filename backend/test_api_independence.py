"""
CareerMate tests for the current retrieval-first AI Mentor.

These tests do not connect to MySQL and do not require Gemini or Ollama.
Run them from the backend folder:

    python -m pytest -v test_api_independence.py

The tests use the real local mentor_knowledge.json file.
"""

import importlib
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def modules():
    os.environ.setdefault("FLASK_SECRET_KEY", "test-only-secret")

    app_module = importlib.import_module("app")
    engine = importlib.import_module("mentor_engine")

    app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-secret",
    )
    return app_module, engine


@pytest.fixture(autouse=True)
def clean_engine_cache(modules, monkeypatch):
    _, engine = modules
    monkeypatch.setenv("MENTOR_OLLAMA_ENABLED", "false")
    monkeypatch.setenv("MENTOR_RETRIEVAL_THRESHOLD", "0.65")
    engine._CACHE.clear()
    engine._knowledge.cache_clear()
    yield
    engine._CACHE.clear()


@pytest.fixture()
def sample_context():
    return {
        "student_id": 987654,
        "student_name": "Test Student",
        "career_interest": "Cybersecurity Analyst",
        "current_skills": [
            {"skill": "Python", "proficiency_level": 3}
        ],
        "roadmap_exists": True,
        "completed_task_count": 1,
        "total_roadmap_tasks": 3,
        "pending_task_count": 2,
        "completed_tasks": [{"task_title": "Learn Networking"}],
        "pending_tasks": [
            {"task_title": "Learn Linux"},
            {"task_title": "Practise Log Analysis"},
        ],
    }


def first_knowledge_question(engine):
    entries = engine._knowledge()
    assert entries, (
        "mentor_knowledge.json did not load any entries. "
        "Check that the expanded JSON file is in the backend folder."
    )
    question = entries[0].get("question")
    assert question, "The first knowledge-base entry has no question field."
    return question


def test_knowledge_base_loads_entries(modules):
    _, engine = modules

    entries = engine._knowledge()

    assert isinstance(entries, list)
    assert len(entries) > 0
    assert all(isinstance(item, dict) and item.get("answer") for item in entries)


def test_known_question_is_answered_without_external_api(modules, sample_context):
    _, engine = modules
    question = first_knowledge_question(engine)

    with patch.object(
        engine.urllib.request,
        "urlopen",
        side_effect=AssertionError("External network call was attempted"),
    ) as network_call:
        answer, mode, confidence, cache_hit = engine.generate_hybrid_answer(
            question, sample_context
        )

    assert answer.strip()
    assert mode == "knowledge_base"
    assert confidence >= 0.65
    assert cache_hit is False
    network_call.assert_not_called()


def test_unknown_question_returns_local_fallback(modules, sample_context):
    _, engine = modules

    with patch.object(
        engine.urllib.request,
        "urlopen",
        side_effect=AssertionError("Ollama must remain disabled in this test"),
    ) as network_call:
        answer, mode, confidence, cache_hit = engine.generate_hybrid_answer(
            "Explain quantum teleportation in interstellar quantum engines",
            sample_context,
        )

    assert answer.strip()
    assert mode == "knowledge_base_no_match"
    assert cache_hit is False
    network_call.assert_not_called()


def test_repeated_question_uses_cache(modules, sample_context):
    _, engine = modules
    question = first_knowledge_question(engine)

    first = engine.generate_hybrid_answer(question, sample_context)
    second = engine.generate_hybrid_answer(question, sample_context)

    assert first[0] == second[0]
    assert first[1] == second[1]
    assert first[3] is False
    assert second[3] is True


def test_cache_is_separated_by_student_context(modules, sample_context):
    _, engine = modules
    question = first_knowledge_question(engine)

    first = engine.generate_hybrid_answer(question, sample_context)

    another_context = dict(sample_context)
    another_context["student_id"] = 987655
    another_context["career_interest"] = "Python Developer"

    second = engine.generate_hybrid_answer(question, another_context)

    assert first[3] is False
    assert second[3] is False
    assert "Cybersecurity Analyst" in first[0]
    assert "Python Developer" in second[0]


def test_student_context_question_uses_saved_profile(modules, sample_context):
    _, engine = modules

    answer, mode, confidence, cache_hit = engine.generate_hybrid_answer(
        "Show my progress and what should I learn next",
        sample_context,
    )

    assert mode == "student_context"
    assert "Cybersecurity Analyst" in answer
    assert "Learn Networking" in answer
    assert "Learn Linux" in answer
    assert confidence == 1.0
    assert cache_hit is False


def test_seven_day_plan_is_generated_locally(modules, sample_context):
    _, engine = modules

    answer, mode, confidence, cache_hit = engine.generate_hybrid_answer(
        "Create a 7-day plan for my career",
        sample_context,
    )

    assert mode == "personalized_plan"
    assert "Day 1" in answer
    assert "Day 7" in answer
    assert "Cybersecurity Analyst" in answer
    assert confidence == 1.0
    assert cache_hit is False


def test_mentor_chat_requires_login(modules):
    app_module, _ = modules
    client = app_module.app.test_client()

    response = client.post(
        "/api/mentor/chat",
        json={"message": "Explain DNS"},
    )

    assert response.status_code == 401
    assert "error" in response.get_json()
