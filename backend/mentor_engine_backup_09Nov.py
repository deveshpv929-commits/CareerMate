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
    "what", "is", "are", "the", "a", "an", "of", "in", "on", "i", "become", "to",
    "for", "and", "or", "with", "how", "why", "when", "where", "who",
    "which", "can", "could", "would", "should", "explain", "define",
    "describe", "tell", "me", "about", "please", "does", "do", "give", "show"
}
def _normalize(text):
    text = str(text or "").casefold()
    text = re.sub(r"\bjava\s+script\b", "javascript", text)
    text = re.sub(r"\bcyber\s+security\b", "cybersecurity", text)
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    words = re.findall(r"[a-z0-9+#]+(?:\.[a-z0-9+#]+)*", text)
    result = []
    for word in words:
        if word in STOP_WORDS:
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = word[:-1]
        result.append(word)
    return " ".join(result)
def _tokens(value):
    return set(_normalize(value).split())
def _strip_question_prefix(text):
    text = str(text or "").casefold().strip()

    prefixes = (
        "what is ", "what are ", "who is ", "who are ",
        "how does ", "how do i learn ", "how do learn ",
        "how to learn ", "how can i learn ",
        "how do ", "how to ",
        "explain ", "define ", "tell me about ",
        "describe "
    )

    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):].strip()

    return text

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
        return [item for item in entries if isinstance(item, dict) and item.get("answer")]
    except (OSError, json.JSONDecodeError) as error:
        print(f"Knowledge base loading error: {error}")
        return []
def _as_list(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []

def _retrieve(question, limit=1):
    """
    Retrieve knowledge using topic matching and question intent.
    Definition questions prefer definition entries.
    Learning questions prefer learning-roadmap entries.
    """
    raw_question = str(question or "").casefold().strip()
    query = _normalize(_strip_question_prefix(raw_question))

    ignored_terms = {
        "example", "examples", "beginner", "basic",
        "basics", "simple", "please", "kindly",
        "build", "create", "write", "make", "become",
        "type", "all", "include", "includes", "including"
    }

    query_terms = _tokens(query) - ignored_terms

    if not query_terms:
        return [], 0.0

    # Identify what the user wants.
    learning_phrases = (
        "how do i learn", "how to learn", "learning roadmap",
        "roadmap", "learning plan", "steps to learn",
        "how can i learn", "where should i start"
    )

    definition_phrases = (
        "what is", "what are", "define",
        "explain", "meaning of", "tell me about"
    )

    if any(p in raw_question for p in learning_phrases):
        intent = "learning"
    elif any(p in raw_question for p in definition_phrases):
        intent = "definition"
    else:
        intent = None

    ranked = []

    for item in _knowledge():
        anchor_phrases = [
            str(item.get("title", "")),
            str(item.get("topic", "")),
            str(item.get("category", "")),
            str(item.get("question", ""))
        ]

        keyword_phrases = _as_list(item.get("keywords", []))

        anchor_terms = _tokens(" ".join(anchor_phrases))
        keyword_terms = _tokens(" ".join(keyword_phrases))

        anchor_overlap = query_terms & anchor_terms
        keyword_overlap = query_terms & keyword_terms

        if not anchor_overlap and not keyword_overlap:
            continue

        weighted_matches = sum(
            1.0 if term in anchor_terms
            else 0.65 if term in keyword_terms
            else 0.0
            for term in query_terms
        )

        coverage = weighted_matches / len(query_terms)

        if keyword_overlap:
            coverage += 0.10 * (
                len(keyword_overlap) / len(query_terms)
            )

        coverage = min(coverage, 1.0)

        all_phrases = anchor_phrases + keyword_phrases

        phrase_match = any(
            (phrase := _normalize(value)) and
            (
                phrase == query
                or f" {phrase} " in f" {query} "
            )
            for value in all_phrases
        )

        confidence = coverage

        if phrase_match:
            confidence += 0.15

        confidence = min(confidence, 1.0)

        # Determine the intent represented by this entry.
        entry_text = " ".join(anchor_phrases).casefold()

        entry_intent = None

        if any(word in entry_text for word in (
            "learn", "learning", "roadmap", "study plan"
        )):
            entry_intent = "learning"
        elif any(word in entry_text for word in (
            "what is", "what are", "definition", "introduction"
        )):
            entry_intent = "definition"

        # Reward entries matching the user's intent.
        intent_score = 0

        if intent and entry_intent == intent:
            intent_score = 1
        elif intent and entry_intent and entry_intent != intent:
            intent_score = -1

        exact_question_match = (
            _normalize(item.get("question", "")) ==
            _normalize(raw_question)
        )
        

        ranked.append((
            1 if exact_question_match else 0,
            confidence,
            intent_score,
            coverage,
            len(anchor_overlap),
            item
        ))

    if not ranked:
        return [], 0.0

    ranked.sort(
    key=lambda row: (
        row[0],
        row[2],
        row[1],
        row[3],
        row[4]
    ),
    reverse=True
)

    best_confidence = ranked[0][1]

    min_coverage = float(
        os.getenv("MENTOR_MIN_QUERY_COVERAGE", "0.75")
    )

    min_confidence = float(
        os.getenv("MENTOR_RETRIEVAL_THRESHOLD", "0.78")
    )

    if (
        ranked[0][3] < min_coverage
        or best_confidence < min_confidence
    ):
        return [], best_confidence

    limit = max(1, int(limit))

    qualified = [
        row[5]
        for row in ranked
        if row[3] >= min_coverage
        and row[1] >= min_confidence
    ]

    return qualified[:limit], best_confidence


def _profile_summary(context):
    skills = context.get("current_skills", [])
    skill_text = ", ".join(
        f"{item.get('skill')} (Level {item.get('proficiency_level')}/5)"
        for item in skills[:12]
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
            lines.append("Completed: " + ", ".join(
                t.get("task_title", "") for t in completed[:5]
            ) + ".")
        if pending:
            lines.append("Next pending tasks: " + ", ".join(
                t.get("task_title", "") for t in pending[:3]
            ) + ".")
    else:
        lines.append("You do not have a saved learning roadmap yet.")
    return "\n".join(lines)
def _resolve_follow_up(message, context):
    """Find the last main topic, even across multiple follow-up questions."""
    history = context.get("conversation_history", [])
    if not history:
        return message, False
    follow_up_patterns = (
        "give me an example",
        "give an example",
        "another example",
        "show me an example",
        "explain it",
        "explain this",
        "explain more",
        "explain in detail",
        "explain simply",
        "explain it simply",
        "what are its advantages",
        "what are the advantages",
        "what are its disadvantages",
        "what are the disadvantages",
        "tell me more",
        "more details",
        "simplify it",
        "what about its uses",
        "what are its uses",
    )
    normalized_message = message.casefold().strip()
    is_follow_up = any(
        phrase in normalized_message
        for phrase in follow_up_patterns
    )
    if not is_follow_up:
        return message, False
    # Search backwards for the most recent main question.
    for exchange in reversed(history):
        previous_message = exchange.get("user_message", "").strip()
        if not previous_message:
            continue
        previous_normalized = previous_message.casefold().strip()
        previous_is_follow_up = any(
            phrase in previous_normalized
            for phrase in follow_up_patterns
        )
        if not previous_is_follow_up:
            return previous_message, True
    return message, False
def generate_hybrid_answer(message, context):
    """Returns (answer, mode, confidence, cache_hit)."""
    ttl = int(os.getenv("MENTOR_CACHE_TTL", "900"))
    fingerprint = hashlib.sha256(
        json.dumps(context, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    key = f"{context.get('student_id', 'student')}:{fingerprint}:{message.casefold().strip()}"
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached["time"] < ttl:
        return cached["answer"], cached["mode"], cached["confidence"], True
    resolved_message, is_follow_up = _resolve_follow_up(message, context)
    question = message.casefold()
    pending = context.get("pending_tasks", [])
    is_plan_request = (
        "plan" in question and any(term in question for term in
        ("7-day", "7 day", "seven-day", "seven day"))
    )
    personal_phrases = (
        "my progress", "my roadmap", "my skills", "what should i learn next",
        "what have i completed", "my career", "my learning plan"
    )
    if not is_plan_request and any(p in question for p in personal_phrases):
        answer = _profile_summary(context)
        if pending and ("next" in question or "should i learn" in question):
            answer += (
                "\n\n**Recommended next step:** "
                + pending[0].get("task_title", "your next pending task")
                + ". Start with this task, then update your roadmap when finished."
            )
        mode, confidence = "student_context", 1.0
    elif is_plan_request:
        career = context.get("career_interest") or "your chosen career"
        focus = [task.get("task_title") for task in pending[:7] if task.get("task_title")]
        if not focus:
            focus = [
                "Review networking fundamentals",
                "Practise Linux commands and permissions",
                "Learn core security concepts",
                "Study log analysis basics",
                "Practise Python scripting",
                "Complete a safe hands-on lab",
                "Review the week's work and prepare interview notes"
            ]
        days = [
            f"**Day {i + 1}: {topic}**\n- Study for 45–60 minutes.\n"
            "- Write short notes and complete one practical exercise."
            for i, topic in enumerate(focus)
        ]
        while len(days) < 7:
            days.append(
                f"**Day {len(days) + 1}: Revision and practice**\n"
                "- Revise the topics you found difficult.\n"
                "- Complete one practical exercise."
            )
        answer = (
            f"Here is a beginner-friendly 7-day plan for **{career}**, "
            "based on your saved CareerMate roadmap.\n\n"
            + "\n\n".join(days[:7])
            + "\n\n**At the end of the week:** review what you completed "
            "and update your CareerMate roadmap."
        )
        mode, confidence = "personalized_plan", 1.0
    else:
        matches, confidence = _retrieve(resolved_message)
        if matches:
            item = matches[0]

            # Identify the topic for both initial answers and follow-ups.
            topic = item.get("title")

            if not topic or topic.strip().casefold() in (
                "careermate mentor",
                "mentor",
            ):
                topic = (
                    item.get("topic")
                    or item.get("question")
                    or resolved_message
                )

            topic = topic.strip().rstrip("?.!")

            for prefix in ("what is ", "what are ", "explain ", "introduction to "):
                if topic.casefold().startswith(prefix):
                    topic = topic[len(prefix):].strip()
                    break

            topic = topic[:1].upper() + topic[1:]
            if is_follow_up:
                follow_up = message.casefold()
                if "example" in follow_up:
                    if "array" in topic.casefold():
                        if "another" in follow_up:
                            answer = (
                                "**Another Array Example:**\n\n"
                                "Imagine storing daily temperatures:\n\n"
                                "`temperatures = [28, 30, 29, 31]`\n\n"
                                "- Index 0 = 28°C\n"
                                "- Index 1 = 30°C\n"
                                "- Index 2 = 29°C\n"
                                "- Index 3 = 31°C\n\n"
                                "Each temperature is stored at a specific index."
                            )
                        else:
                            answer = (
                                "**Example of an Array:**\n\n"
                                "Imagine storing the marks of four students:\n\n"
                                "`marks = [85, 90, 78, 92]`\n\n"
                                "- Index 0 = 85\n"
                                "- Index 1 = 90\n"
                                "- Index 2 = 78\n"
                                "- Index 3 = 92\n\n"
                                "You can access each student's marks using its index."
                            )
                    else:
                        answer = (
                            f"Here's an example related to **{topic}**:\n\n"
                            f"{item.get('answer', '')}"
                        )
                
                elif any(word in follow_up for word in ("simply", "simple")):
                    if "array" in topic.casefold():
                        answer = (
                            "**Array explained simply:**\n\n"
                            "An array is like a row of boxes. Each box stores one value, "
                            "and every box has a position called an index.\n\n"
                            "Example:\n"
                            "`marks = [85, 90, 78, 92]`\n\n"
                            "- Position 0 stores 85.\n"
                            "- Position 1 stores 90.\n"
                            "- Position 2 stores 78.\n"
                            "- Position 3 stores 92.\n\n"
                            "You use the index to find a value quickly."
                        )
                    else:
                        answer = (
                            f"**{topic}, explained simply:**\n\n"
                            f"{item.get('answer', '')}"
                        )

                elif "detail" in follow_up:
                    answer = (
                        f"**More details about {topic}:**\n\n"
                        f"{item.get('answer', '')}"
                    )
                elif "advantage" in follow_up:
                    if "array" in topic.casefold():
                        answer = (
                            "**Advantages of Arrays:**\n\n"
                            "1. **Fast access:** Elements can be accessed directly using their index.\n"
                            "2. **Easy to use:** Arrays store multiple values under one variable.\n"
                            "3. **Memory efficiency:** Elements are stored in contiguous memory locations.\n"
                            "4. **Easy traversal:** You can process elements using loops.\n"
                            "5. **Useful for sorting:** Arrays support common searching and sorting algorithms."
                        )
                    else:
                        answer = (
                            f"**Advantages of {topic}:**\n\n"
                            f"{item.get('answer', '')}"
                        )
                elif "disadvantage" in follow_up:
                    disadvantages = item.get("disadvantages", [])

                    if disadvantages:
                        answer = (
                            f"**Disadvantages of {topic}:**\n\n"
                            + "\n".join(f"- {point}" for point in disadvantages)
                        )
                    else:
                        answer = (
                            f"I don't have specific disadvantages of {topic} "
                            "in my knowledge base yet."
                        )
                else:
                    answer = (
                        f"Here's more information about **{topic}**:\n\n"
                        f"{item.get('answer', '')}"
                    )
            else:
                answer = (
                    f"### {topic}\n\n"
                    f"{item.get('answer', '')}"
                )
            career = context.get("career_interest")
            if career and career != "Not saved":
                answer += (
                    f"\n\n**CareerMate tip:** Since your selected goal is "
                    f"**{career}**, connect this topic to a small hands-on "
                    "project and add the result to your portfolio."
                )
            if pending:
                next_task = pending[0].get("task_title", "")
                if next_task:
                    answer += f"\n\n**Your roadmap next step:** {next_task}."
            mode = "knowledge_base"
        elif os.getenv("MENTOR_OLLAMA_ENABLED", "false").casefold() == "true":
            try:
                host = os.getenv(
                    "OLLAMA_HOST", "http://localhost:11434"
                ).rstrip("/")
                model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
                prompt = (
                    "You are CareerMate, a beginner-friendly technical and "
                    "career mentor. Give practical advice and never invent "
                    "student progress.\n\n"
                    f"Saved student context:\n{_profile_summary(context)}"
                    f"\n\nQuestion: {message}"
                )
                body = json.dumps({
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 600}
                }).encode()
                request = urllib.request.Request(
                    host + "/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(
                    request,
                    timeout=int(os.getenv("OLLAMA_TIMEOUT", "45"))
                ) as response:
                    answer = (
                        json.loads(response.read().decode()).get("response") or ""
                    ).strip()
                if not answer:
                    raise RuntimeError("Ollama returned an empty answer")
                mode = "local_ollama"
            except Exception:
                answer = (
                    "I couldn't find a reliable answer in the CareerMate "
                    "knowledge base, and the optional local model is "
                    "unavailable. Try asking about a topic covered by "
                    "the current knowledge base."
                )
                mode = "knowledge_base_no_match"
        else:
            answer = (
                "I couldn't find a reliable answer for that in my current "
                "CareerMate knowledge base. I can help with cybersecurity, "
                "networking, Linux, Python, security fundamentals, log "
                "analysis, projects, interviews and career roadmaps. "
                "Try a more specific question, such as "
                "**'Explain Linux file permissions with examples'**."
            )
            mode = "knowledge_base_no_match"
    _CACHE[key] = {
        "answer": answer, "mode": mode, "confidence": confidence, "time": now
    }
    for old_key in [k for k, v in _CACHE.items() if now - v["time"] >= ttl]:
        _CACHE.pop(old_key, None)
    while len(_CACHE) > 500:
        oldest = min(_CACHE, key=lambda k: _CACHE[k]["time"])
        _CACHE.pop(oldest, None)
    return answer, mode, confidence, False