"""Lightweight retrieval-first mentor engine for CareerMate."""
import hashlib
import json
import os
import re
import time
import urllib.request
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "mentor_knowledge.json")
_CACHE = {}


STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "of", "in", "on",
    "to", "for", "and", "or", "with", "how", "why", "when",
    "where", "who", "which", "can", "could", "would", "should",
    "explain", "define", "describe", "tell", "me", "about",
    "please", "does", "do"
}


def _tokens(value):
    words = re.findall(
        r"[a-z0-9+#.]+",
        str(value or "").casefold()
    )
    return {
        word for word in words
        if word not in STOP_WORDS
    }


@lru_cache(maxsize=1)
def _knowledge():
    try:
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = data.get("knowledge_base", [])
        else:
            entries = []

        if not isinstance(entries, list):
            return []

        return [
            item for item in entries
            if isinstance(item, dict) and item.get("answer")
        ]

    except (OSError, json.JSONDecodeError) as error:
        print(f"Knowledge base loading error: {error}")
        return []





def _retrieve(question, limit=1):
    def normalize(text):
        text = re.sub(r"[^a-z0-9\s]", " ", str(text).lower())
        text = " ".join(text.split())

        prefixes = [
            "what is ",
            "what are ",
            "how does ",
            "how do ",
            "how to ",
            "explain ",
            "define ",
            "tell me about ",
            "describe "
        ]

        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break

        return text.strip()

    normalized_query = normalize(question)
    query_terms = set(normalized_query.split())

    if not query_terms:
        return [], 0.0

    ranked = []

    for item in _knowledge():
        keywords = item.get("keywords", [])
        related_topics = item.get("related_topics", [])

        if isinstance(keywords, str):
            keywords = [keywords]

        if isinstance(related_topics, str):
            related_topics = [related_topics]

        question_text = normalize(item.get("question", ""))

        priority_text = " ".join([
            item.get("title", ""),
            item.get("topic", ""),
            item.get("category", ""),
            item.get("question", ""),
            " ".join(keywords),
            " ".join(related_topics)
        ])

        priority_terms = set(normalize(priority_text).split())
        answer_terms = set(normalize(item.get("answer", "")).split())

        all_terms = priority_terms | answer_terms

        overlap = len(query_terms & all_terms)
        priority_overlap = len(query_terms & priority_terms)

        if overlap == 0 or priority_overlap == 0:
            continue

        coverage = priority_overlap / len(query_terms)

        score = (
            0.50 * coverage
            + 0.30 * (overlap / len(query_terms))
        )

        # Give exact question matches a strong priority.
        if question_text == normalized_query:
            score += 3.0

        # Prioritize specific technical phrases.
        for keyword in keywords:
            keyword_text = normalize(keyword)

            if keyword_text and keyword_text in normalized_query:
                score += 1.5

        # Prefer entries covering more specific query terms.
        if len(priority_terms) > 0:
            specificity = priority_overlap / len(priority_terms)
            score += 0.10 * specificity

        ranked.append((score, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)

    if not ranked:
        return [], 0.0

    return (
        [item for _, item in ranked[:limit]],
        min(ranked[0][0], 1.0)
    )


def _profile_summary(context):
    skills = context.get("current_skills", [])
    skill_text = ", ".join(
        f"{item.get('skill')} (Level {item.get('proficiency_level')}/5)" for item in skills[:12]
    ) or "No assessed skills saved yet"
    lines = []
    if context.get("student_name") not in (None, "Not saved"):
        lines.append(f"Hi {context['student_name']}!")
    if context.get("career_interest") not in (None, "Not saved"):
        lines.append(f"Your selected career goal is **{context['career_interest']}**.")
    lines.append(f"**Your current skills:** {skill_text}.")
    if context.get("roadmap_exists"):
        lines.append(
            f"**Roadmap:** {context.get('completed_task_count', 0)} of "
            f"{context.get('total_roadmap_tasks', 0)} tasks completed; "
            f"{context.get('pending_task_count', 0)} pending."
        )
        completed = context.get("completed_tasks", [])
        pending = context.get("pending_tasks", [])
        if completed:
            lines.append("Completed: " + ", ".join(t.get("task_title", "") for t in completed[:5]) + ".")
        if pending:
            lines.append("Next pending tasks: " + ", ".join(t.get("task_title", "") for t in pending[:3]) + ".")
    else:
        lines.append("You do not have a saved learning roadmap yet.")
    return "\n".join(lines)


def generate_hybrid_answer(message, context):
    """Returns (answer, mode, confidence, cache_hit)."""
    ttl = int(os.getenv("MENTOR_CACHE_TTL", "900"))
    fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()[:16]
    key = f"{context.get('student_id', 'student')}:{fingerprint}:{message.casefold().strip()}"
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached["time"] < ttl:
        return cached["answer"], cached["mode"], cached["confidence"], True

    question = message.casefold()
    completed = context.get("completed_tasks", [])
    pending = context.get("pending_tasks", [])
    is_plan_request = (
    "plan" in question
    and any(term in question for term in (
        "7-day", "7 day", "seven-day", "seven day"
    ))
)
    personal_phrases = ("my progress", "my roadmap", "my skills", "what should i learn next", "what have i completed", "my career", "my learning plan")

    if not is_plan_request and any(phrase in question for phrase in personal_phrases):
        answer = _profile_summary(context)
        if pending and ("next" in question or "should i learn" in question):
            answer += "\n\n**Recommended next step:** " + pending[0].get("task_title", "your next pending task") + ". Start with this task, then update your roadmap when finished."
        mode, confidence = "student_context", 1.0
    elif "plan" in question and any(term in question for term in ("7-day", "7 day", "seven-day", "seven day")):
        career = context.get("career_interest") or "your chosen career"
        focus = [task.get("task_title") for task in pending[:7] if task.get("task_title")]
        if not focus:
            focus = ["Review networking fundamentals", "Practise Linux commands and permissions", "Learn core security concepts", "Study log analysis basics", "Practise Python scripting", "Complete a safe hands-on lab", "Review the week's work and prepare interview notes"]
        days = [f"**Day {i + 1}: {topic}**\n- Study for 45–60 minutes.\n- Write short notes and complete one practical exercise." for i, topic in enumerate(focus)]
        while len(days) < 7:
            days.append(f"**Day {len(days) + 1}: Revision and practice**\n- Revise the topics you found difficult.\n- Complete one practical exercise.")
        answer = f"Here is a beginner-friendly 7-day plan for **{career}**, based on your saved CareerMate roadmap.\n\n" + "\n\n".join(days[:7]) + "\n\n**At the end of the week:** review what you completed and update your CareerMate roadmap."
        mode, confidence = "personalized_plan", 1.0
    else:
        matches, confidence = _retrieve(message)
        threshold = float(os.getenv("MENTOR_RETRIEVAL_THRESHOLD", "0.65"))
        if matches and confidence >= threshold:
            answer = "\n\n".join(f"### {item.get('title', 'CareerMate Mentor')}\n{item.get('answer', '')}" for item in matches)
            career = context.get("career_interest")
            if career and career != "Not saved":
                answer += f"\n\n**CareerMate tip:** Since your selected goal is **{career}**, connect this topic to a small hands-on project and add the result to your portfolio."
            if pending:
                answer += f"\n\n**Your roadmap next step:** {pending[0].get('task_title', '')}."
            mode = "knowledge_base"
        elif os.getenv("MENTOR_OLLAMA_ENABLED", "false").casefold() == "true":
            try:
                host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
                model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
                prompt = ("You are CareerMate, a beginner-friendly technical and career mentor. "
                          "Give practical advice and never invent student progress.\n\n"
                          f"Saved student context:\n{_profile_summary(context)}\n\nQuestion: {message}")
                body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                                   "options": {"temperature": 0.3, "num_predict": 600}}).encode()
                request = urllib.request.Request(host + "/api/generate", data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=int(os.getenv("OLLAMA_TIMEOUT", "45"))) as response:
                    answer = (json.loads(response.read().decode()).get("response") or "").strip()
                if not answer:
                    raise RuntimeError("Ollama returned an empty answer")
                mode = "local_ollama"
            except Exception:
                answer = ("I couldn't find a reliable answer in the CareerMate knowledge base, "
                          "and the optional local model is unavailable. Ask about cybersecurity, "
                          "networking, Linux, Python, log analysis, projects or interviews.")
                mode = "knowledge_base_no_match"
        else:
            answer = ("I couldn't find a reliable answer for that in my current CareerMate knowledge base. "
                      "I can help with cybersecurity, networking, Linux, Python, security fundamentals, "
                      "log analysis, projects, interviews and career roadmaps. Try a more specific question, "
                      "such as **'Explain Linux file permissions with examples'**.")
            mode = "knowledge_base_no_match"

    _CACHE[key] = {"answer": answer, "mode": mode, "confidence": confidence, "time": now}
    for old_key in [k for k, v in _CACHE.items() if now - v["time"] >= ttl]:
        _CACHE.pop(old_key, None)
    while len(_CACHE) > 500:
        oldest = min(_CACHE, key=lambda k: _CACHE[k]["time"])
        _CACHE.pop(oldest, None)
    return answer, mode, confidence, False
