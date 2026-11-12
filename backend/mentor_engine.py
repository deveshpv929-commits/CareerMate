"""Lightweight retrieval-first mentor engine for CareerMate."""

import difflib
import hashlib
import json
import os
import re
import time
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

    # Normalize common topic variations.
    text = re.sub(r"\bjava\s+script\b", "javascript", text)
    text = re.sub(r"\bcyber\s+security\b", "cybersecurity", text)

    # Normalize networking terms and a common spelling mistake.
    text = re.sub(r"\bnettworking\b", "network", text)
    text = re.sub(r"\bnetworking\b", "network", text)
    text = re.sub(r"\bnetworks\b", "network", text)

    text = re.sub(r"[^a-z0-9+#.]", " ", text)
    words = re.findall(r"[a-z0-9+#.]+", text)

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
    """Remove common conversational wrappers without removing the topic."""
    text = str(text or "").casefold().strip()
    text = re.sub(r"\bcyber\s+security\b", "cybersecurity", text)

    prefixes = (
        "can you please ", "could you please ", "would you please ",
        "can you ", "could you ", "would you ", "please ",
        "what is ", "what are ", "what does ", "what do ",
        "how does ", "how do ", "how can ", "how to ",
        "why is ", "why are ", "why does ", "why do ",
        "explain ", "define ", "describe ", "tell me about ",
        "tell me ", "give me an explanation of ", "give me "
    )

    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _detect_intent(message):
    """Identify the small set of question intents handled directly by CareerMate."""
    question = re.sub(r"\s+", " ", str(message or "").casefold()).strip()
    plan_terms = ("7-day", "7 day", "seven-day", "seven day")
    if "plan" in question and any(term in question for term in plan_terms):
        return "learning_plan"

    personal_patterns = (
        r"\bmy\s+(?:progress|roadmap|skills|career|learning plan)\b",
        r"\bwhat have i completed\b",
        r"\bwhat should i learn next\b",
        r"\bwhat do i learn next\b",
        r"\bshow me my\s+(?:progress|roadmap|skills)\b",
    )
    if any(re.search(pattern, question) for pattern in personal_patterns):
        return "student_context"
    return "knowledge"


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
    Retrieve only from the local knowledge base using topic anchors,
    keywords, categories and related-topic metadata.
    """
    query = _normalize(_strip_question_prefix(question))
    ignored_terms = {
        "example", "examples", "beginner", "basic", "basics",
        "simple", "simply", "word", "words", "language",
        "please", "kindly", "build", "create", "write", "make",
        "become", "important", "importance", "data", "analysis",
        "use", "used", "using", "help", "helps", "explain",
        "define", "describe", "tell", "give", "show", "me",
        "about", "it", "that", "this", "can", "could", "would",
        "should", "does", "do", "you", "work", "type", "types",
        "advantage", "advantages", "disadvantage", "disadvantages",
        "benefit", "benefits", "purpose", "purposes", "meaning",
        "difference", "differences", "vs", "compare", "comparison",
        "detail", "details", "more", "overview", "introduction"
    }

    query_terms = _tokens(query) - ignored_terms
    if not query_terms:
        return [], 0.0

    question_text = str(question or "").casefold()
    career_phrases = (
        "how do i become", "how can i become", "career path",
        "career roadmap", "job role", "career in"
    )
    career_terms = {
        "career", "job", "analyst", "engineer", "profession",
        "roadmap", "interview", "qualification", "salary"
    }
    is_career_question = (
        any(phrase in question_text for phrase in career_phrases)
        or bool(query_terms & career_terms)
    )
    career_topic_terms = {
        "career", "job", "analyst", "engineer", "profession",
        "roadmap", "interview", "qualification", "path"
    }

    ranked = []
    for item in _knowledge():
        anchor_phrases = [
            str(item.get("title") or ""),
            str(item.get("topic") or ""),
            str(item.get("question") or ""),
            str(item.get("category") or ""),
        ]
        related_phrases = _as_list(item.get("related_topics", []))
        keyword_phrases = _as_list(item.get("keywords", []))

        anchor_terms = _tokens(" ".join(anchor_phrases + related_phrases))
        keyword_terms = _tokens(" ".join(keyword_phrases))
        candidate_terms = anchor_terms | keyword_terms

        if is_career_question and not (candidate_terms & career_topic_terms):
            # Keep explicit career/role questions from matching a generic topic.
            if not ({"career", "job", "analyst", "engineer"} & candidate_terms):
                continue

        anchor_overlap = query_terms & anchor_terms
        keyword_overlap = query_terms & keyword_terms
        matched_terms = anchor_overlap | keyword_overlap
        if not matched_terms:
            continue

        weighted_matches = sum(
            1.0 if term in anchor_terms else 0.75
            for term in query_terms
            if term in candidate_terms
        )
        coverage = weighted_matches / max(1, len(query_terms))

        all_phrases = anchor_phrases + related_phrases + keyword_phrases
        normalized_query = f" {query} "
        normalized_phrases = [
            _normalize(value) for value in all_phrases if _normalize(value)
        ]
        def exact_key(value):
            cleaned = _strip_question_prefix(value)
            cleaned = re.sub(r"[^a-z0-9+#.]", " ", cleaned)
            words = re.sub(r"\s+", " ", cleaned).strip().split()
            # Ignore grammatical filler while preserving topic word forms.
            words = [word for word in words if word not in STOP_WORDS]
            return " ".join(words)

        # Exact matching preserves distinctions such as "networking" vs
        # "networks" and does not treat a shared category as an exact match.
        exact_anchor_match = any(
            exact_key(value) == exact_key(question)
            for value in anchor_phrases[:3]
            if value and exact_key(value)
        )
        phrase_match = any(
            phrase == query
            or f" {phrase} " in normalized_query
            or f" {query} " in f" {phrase} "
            for phrase in normalized_phrases
        )

        confidence = coverage
        if phrase_match:
            confidence += 0.15
        if exact_anchor_match:
            confidence += 0.30
        if keyword_overlap:
            confidence += 0.05 * (
                len(keyword_overlap) / max(1, len(query_terms))
            )
        confidence = min(confidence, 1.0)

        ranked.append((
            exact_anchor_match,
            confidence,
            coverage,
            len(anchor_overlap),
            len(keyword_overlap),
            item
        ))

    if not ranked:
        return [], 0.0

    ranked.sort(
        key=lambda row: (row[0], row[1], row[2], row[3], row[4]),
        reverse=True
    )

    min_coverage = float(os.getenv("MENTOR_MIN_QUERY_COVERAGE", "0.50"))
    min_confidence = float(os.getenv("MENTOR_RETRIEVAL_THRESHOLD", "0.58"))

    if (
        ranked[0][2] < min_coverage
        or ranked[0][1] < min_confidence
    ):
        return [], ranked[0][1]

    limit = max(1, int(limit))
    qualified = [
        row[5] for row in ranked
        if row[2] >= min_coverage and row[1] >= min_confidence
    ]
    return qualified[:limit], ranked[0][1]


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




def _profile_guidance(item, context):
    """Create concise guidance grounded in the student's saved profile."""
    career = context.get("career_interest") or context.get("roadmap_career")
    if career in (None, "", "Not saved"):
        career = None

    topic_phrases = [
        str(item.get("title") or ""),
        str(item.get("topic") or ""),
        str(item.get("question") or ""),
        str(item.get("category") or ""),
    ]
    topic_phrases += _as_list(item.get("keywords", []))
    topic_phrases += _as_list(item.get("related_topics", []))
    topic_terms = _tokens(" ".join(topic_phrases))

    matching_skills = []
    for skill_item in context.get("current_skills", []) or []:
        if not isinstance(skill_item, dict):
            continue
        skill_name = str(skill_item.get("skill") or "").strip()
        if not skill_name:
            continue
        skill_terms = _tokens(skill_name)
        if skill_terms and (skill_terms <= topic_terms or len(skill_terms & topic_terms) >= 1):
            matching_skills.append((skill_name, skill_item.get("proficiency_level")))

    lines = []
    if matching_skills:
        skill_name, raw_level = matching_skills[0]
        try:
            level = max(1, min(5, int(raw_level)))
        except (TypeError, ValueError):
            level = None

        if level is not None:
            if level <= 2:
                advice = "Focus on the fundamentals first, then practise one small exercise."
            elif level <= 3:
                advice = "You have a starting foundation; reinforce it with a practical exercise."
            else:
                advice = "You have a good foundation; try a hands-on exercise and document what you learn."
            lines.append(
                f"**Based on your profile:** Your assessed {skill_name} level is "
                f"**{level}/5**. {advice}"
            )

    if career:
        category = str(item.get("category") or "").casefold()
        career_lower = str(career).casefold()
        career_connection = None

        if "cyber" in career_lower or "security" in career_lower:
            if "network" in category:
                career_connection = (
                    "For your cybersecurity goal, networking helps you understand "
                    "IP addresses, DNS and network traffic during security investigations."
                )
            elif "linux" in category:
                career_connection = (
                    "For your cybersecurity goal, Linux skills help you work with "
                    "permissions, system commands and security logs."
                )
            elif "python" in category:
                career_connection = (
                    "For your cybersecurity goal, Python can help automate repetitive "
                    "checks and analyse security data."
                )
            elif "cyber" in category or "security" in category:
                career_connection = (
                    "This topic supports your cybersecurity goal by strengthening "
                    "your understanding of security principles and defensive practices."
                )

        if career_connection:
            lines.append(f"**Career connection ({career}):** {career_connection}")

    return "\n\n".join(lines)

def _is_follow_up(message):
    """Detect short contextual questions, including common spelling mistakes."""
    text = re.sub(r"\s+", " ", str(message or "").casefold()).strip()
    if not text:
        return False

    patterns = (
        r"\bgive me an example\b",
        r"\bgive an example\b",
        r"\bshow me an example\b",
        r"\banother example\b",
        r"\bexplain\b.*\b(?:it|this|that|them)\b",
        r"\bexplain its\b",
        r"\bwhat are its\b",
        r"\bwhat is its\b",
        r"\bwhat about its\b",
        r"\bwhat are the advantages\b",
        r"\bwhat are the disadvantages\b",
        r"\bwhat about\b",
        r"\btell me more\b",
        r"\bcan you elaborate\b",
        r"\belaborate\b",
        r"\bexplain more\b",
        r"\bmore details\b",
        r"\bexplain in detail\b",
        r"\bexplain simply\b",
        r"\bin simple words\b",
        r"\bsimplify it\b",
        r"\bmake it simple\b",
        r"\b(?:and )?(?:its|their)\b",
    )

    if any(re.search(pattern, text) for pattern in patterns):
        return True

    # Very short detail-only prompts usually refer to the previous topic.
    detail = _follow_up_detail(text)
    words = text.strip(" ?.!").split()
    if detail and len(words) <= 4:
        return True

    return False


def _resolve_follow_up(message, context):
    """Resolve a follow-up to the latest non-follow-up user question."""
    history = context.get("conversation_history", [])

    if not isinstance(history, list) or not history or not _is_follow_up(message):
        return message, False

    for exchange in reversed(history):
        if isinstance(exchange, dict):
            previous_message = str(exchange.get("user_message", "")).strip()
        else:
            previous_message = str(exchange or "").strip()

        if not previous_message:
            continue

        if not _is_follow_up(previous_message):
            return previous_message, True

    return message, False


def _follow_up_detail(message):
    """Identify the detail requested, tolerating minor spelling mistakes."""
    question = str(message or "").casefold()
    words = re.findall(r"[a-z]+", question)

    detail_terms = {
        "examples": ("example", "examples"),
        "types": ("type", "types"),
        "advantages": ("advantage", "advantages"),
        "disadvantages": ("disadvantage", "disadvantages"),
        "uses": ("use", "uses"),
        "a simplified explanation": ("simple", "simply", "simplify"),
        "additional details": ("detail", "details", "more"),
    }

    for description, variants in detail_terms.items():
        if any(variant in words for variant in variants):
            return description

    # Catch misspellings such as "adavanatges" without treating unrelated
    # words as a request for advantages.
    for word in words:
        for canonical in ("advantage", "disadvantage", "example"):
            if len(word) >= 6 and difflib.SequenceMatcher(
                None, word, canonical
            ).ratio() >= 0.78:
                if canonical == "advantage":
                    return "advantages"
                if canonical == "disadvantage":
                    return "disadvantages"
                return "examples"

    return None




def _select_knowledge_section(item, message, is_follow_up):
    """
    Return only the requested part of a knowledge entry.
    A first broad question receives the short introduction; detail questions
    receive the matching section from the same local knowledge entry.
    """
    answer = str(item.get("answer", "")).strip()
    if not answer:
        return ""

    # Split the answer into its introduction and Markdown heading sections.
    heading_pattern = re.compile(r"(?m)^###\s+(.+?)\s*$")
    matches = list(heading_pattern.finditer(answer))

    intro = answer[:matches[0].start()].strip() if matches else answer
    sections = {}

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
        heading = match.group(1).strip().casefold()
        body = answer[start:end].strip()
        sections[heading] = f"### {match.group(1).strip()}\n\n{body}"

    detail = _follow_up_detail(message)
    if detail:
        heading_aliases = {
            "types": ("types of computer networks", "types of networks", "types"),
            "examples": ("real-world examples", "examples"),
            "advantages": ("advantages of computer networking", "advantages"),
            "disadvantages": ("disadvantages of computer networking", "disadvantages"),
            "uses": ("uses", "use cases"),
            "a simplified explanation": ("networking in simple words", "simple explanation"),
            "additional details": ("additional details",),
        }
        for heading in heading_aliases.get(detail, ()):
            if heading in sections:
                return sections[heading]

        # The requested section is not present; do not dump unrelated sections.
        return (
            f"I couldn't find a separate **{detail}** section for this topic "
            "in my current knowledge base."
        )

    # For a first broad question, show only the concise introductory answer.
    return intro

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



    question = message.casefold()
    pending = context.get("pending_tasks", [])
    intent = _detect_intent(message)

    if intent == "student_context":
        answer = _profile_summary(context)

        if pending and ("next" in question or "should i learn" in question):

            answer += (

                "\n\n**Recommended next step:** "

                + pending[0].get("task_title", "your next pending task")

                + ". Start with this task, then update your roadmap when finished."

            )

        mode, confidence = "student_context", 1.0



    elif intent == "learning_plan":

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
        # Resolve contextual follow-up questions before retrieval.
        resolved_message, is_follow_up = _resolve_follow_up(
            message, context
        )

        matches, confidence = _retrieve(resolved_message)

        if matches:
            item = matches[0]

            # Get a meaningful topic name from the knowledge entry.
            topic = (
                item.get("title")
                or item.get("topic")
                or item.get("question")
                or "CareerMate Mentor"
            )

            topic = str(topic).strip().rstrip("?.!")

            # Remove common question prefixes from the topic.
            for prefix in (
                "what is ",
                "what are ",
                "explain ",
                "introduction to ",
            ):
                if topic.casefold().startswith(prefix):
                    topic = topic[len(prefix):].strip()
                    break

            topic = topic[:1].upper() + topic[1:]

            selected_content = _select_knowledge_section(
                item, message, is_follow_up
            )

            answer = f"### {topic}\n\n{selected_content}"

            # Personalize only the initial answer using saved profile data.
            # Follow-up answers remain focused on the requested section.
            if not is_follow_up:
                guidance = _profile_guidance(item, context)
                if guidance:
                    answer += "\n\n" + guidance

                if pending:
                    next_task = pending[0].get("task_title", "")
                    if next_task:
                        answer += (
                            f"\n\n**Your roadmap next step:** {next_task}."
                        )

            mode = "knowledge_base"

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


