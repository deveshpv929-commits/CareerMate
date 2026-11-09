# =====================================================================
# CareerMate AI Mentor Chat  (hybrid: cache -> knowledge base -> Gemini)
#
# HOW TO APPLY
#   Replace ONLY the old `mentor_chat()` function (and the genai imports just
#   above the mentor section) with everything in this file.
#   Leave these untouched: list/create/get conversation routes,
#   /api/mentor/plans/latest, login/register/session code.
# =====================================================================
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# google-api-core is NOT a dependency of the `google-genai` SDK, so import it
# defensively. If it is installed (e.g. via the older google-generativeai SDK)
# its DeadlineExceeded is caught too; otherwise this placeholder is inert.
try:
    from google.api_core.exceptions import DeadlineExceeded as ApiCoreDeadlineExceeded
except ImportError:
    class ApiCoreDeadlineExceeded(Exception):
        """Placeholder used when google-api-core is not installed."""


# --- BEGIN PURE MATCHING (no Flask / DB dependencies) -----------------
import os
import re

KB_MATCH_THRESHOLD = float(os.getenv("MENTOR_KB_THRESHOLD", "0.60"))   # answer directly
KB_SOFT_THRESHOLD = float(os.getenv("MENTOR_KB_SOFT_THRESHOLD", "0.35"))  # used only if Gemini fails
KB_MAX_QUERY_TOKENS = 12     # longer questions are usually multi-part -> let Gemini handle them
KB_REFRESH_SECONDS = 60      # how long the in-process KB copy is reused
CACHE_TTL_DAYS = int(os.getenv("MENTOR_CACHE_TTL_DAYS", "7"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "45000"))

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "do", "does",
    "did", "can", "could", "should", "would", "will", "shall", "may", "might",
    "what", "whats", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "i", "me", "you", "your", "we", "us", "it", "its", "this", "that", "these",
    "those", "to", "of", "in", "on", "at", "for", "with", "about", "as", "by",
    "from", "and", "or", "but", "if", "so", "than", "then", "please", "tell",
    "explain", "give", "need", "want", "know", "get", "some", "any", "there",
    "have", "has", "had", "just", "really", "also", "very", "much", "many",
    "use", "using", "used", "mean", "means", "meaning",
    "difference", "differences", "between", "vs", "versus",
}


def _stem(token):
    """Very light suffix stripping, applied identically to questions and KB text."""
    if "." in token or "+" in token or "#" in token:
        return token  # c++, c#, node.js stay as typed
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_question(text):
    """Lower-case, tokenise, drop stop-words, stem. Keeps c++, c#, node.js intact."""
    if not isinstance(text, str):
        return []
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9+#.]*", text.casefold())
    tokens = []
    for token in raw_tokens:
        token = token.rstrip(".")
        if not token or token in _STOPWORDS:
            continue
        if len(token) == 1 and token not in {"c", "r"}:
            continue
        tokens.append(_stem(token))
    return tokens


def question_fingerprint(tokens):
    """Order-insensitive canonical form + SHA-256 used as the cache key."""
    canonical = " ".join(sorted(set(tokens)))
    return canonical[:500], hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_PERSONAL_RE = re.compile(
    r"\b(my|mine|myself)\b|\b(next|pending|completed|current)\s+(task|tasks|step)\b",
    re.IGNORECASE,
)


def is_personalized_question(message):
    """Questions about *this* student need saved context, so they bypass shared stores."""
    return bool(_PERSONAL_RE.search(message))


def is_seven_day_plan_request(message):
    normalized = message.casefold()
    return (
        ("7-day" in normalized or "7 day" in normalized
         or "seven-day" in normalized or "seven day" in normalized)
        and "plan" in normalized
    )


def score_entry(query_tokens, entry):
    """
    Relevance in [0, 1] between a question and one knowledge-base entry.

        coverage    = |Q ∩ K| / |Q|            how much of the question the entry explains
        title_bonus = |Q ∩ T| / |T|            how much of the entry's title the question names
        score       = 0.8 * coverage + 0.2 * title_bonus

    where Q = question tokens, K = entry keywords ∪ title tokens, T = title tokens.
    Two guards stop vague questions from being answered by accident:
      * at least min(2, |Q|) tokens must match, and
      * a one-word question must hit an explicit keyword, not just the title.
    """
    matched = query_tokens & entry["keyword_tokens"]
    if len(matched) < min(2, len(query_tokens)):
        return 0.0
    if len(query_tokens) == 1 and not (query_tokens & entry["explicit_tokens"]):
        return 0.0
    coverage = len(matched) / len(query_tokens)
    title_tokens = entry["title_tokens"]
    title_bonus = (
        len(query_tokens & title_tokens) / len(title_tokens) if title_tokens else 0.0
    )
    return round(0.8 * coverage + 0.2 * title_bonus, 4)


def find_kb_match(tokens, entries):
    """Return (best_entry, best_score). best_entry is None when nothing matches."""
    query_tokens = set(tokens)
    best_entry, best_score = None, 0.0
    if not query_tokens:
        return None, 0.0
    for entry in entries:
        score = score_entry(query_tokens, entry)
        if score > best_score:
            best_entry, best_score = entry, score
    return best_entry, best_score
# --- END PURE MATCHING ------------------------------------------------


# ---------------------------------------------------------------------
# Knowledge-base loading (small in-process copy, refreshed every minute)
# ---------------------------------------------------------------------
_kb_cache = {"loaded_at": 0.0, "entries": []}


def load_knowledge_base():
    now = time.monotonic()
    if _kb_cache["loaded_at"] and now - _kb_cache["loaded_at"] < KB_REFRESH_SECONDS:
        return _kb_cache["entries"]

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, category, title, keywords, answer_text
            FROM mentor_knowledge_base
            WHERE is_active = TRUE
            """
        )
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            title_tokens = set(normalize_question(row["title"]))
            keyword_tokens = set()
            for part in re.split(r"[,;\n]", row["keywords"] or ""):
                keyword_tokens.update(normalize_question(part))
            entries.append({
                "id": row["id"],
                "category": row["category"],
                "title": row["title"],
                "answer_text": row["answer_text"],
                "title_tokens": title_tokens,
                "explicit_tokens": keyword_tokens,
                "keyword_tokens": keyword_tokens | title_tokens,
            })

        _kb_cache["entries"] = entries
        _kb_cache["loaded_at"] = now
        return entries
    except mysql.connector.Error:
        app.logger.exception("Unable to load mentor knowledge base")
        return _kb_cache["entries"]  # stale copy is better than none
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------------------
# Response cache (shared, non-personalised answers only)
# ---------------------------------------------------------------------
def get_cached_answer(question_hash):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, answer_text
            FROM mentor_response_cache
            WHERE question_hash = %s
              AND (expires_at IS NULL OR expires_at > UTC_TIMESTAMP())
            LIMIT 1
            """,
            (question_hash,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cursor.execute(
            """
            UPDATE mentor_response_cache
            SET hit_count = hit_count + 1, last_hit_at = UTC_TIMESTAMP()
            WHERE id = %s
            """,
            (row["id"],),
        )
        connection.commit()
        return row["answer_text"]
    except mysql.connector.Error:
        app.logger.exception("Mentor cache lookup failed")
        return None  # a broken cache must never break the chat
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def store_cached_answer(question_hash, normalized_question, answer, source="gemini"):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO mentor_response_cache
                (question_hash, normalized_question, answer_text, source, expires_at)
            VALUES (%s, %s, %s, %s, DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s DAY))
            ON DUPLICATE KEY UPDATE
                answer_text = VALUES(answer_text),
                source = VALUES(source),
                expires_at = VALUES(expires_at)
            """,
            (question_hash, normalized_question, answer, source, CACHE_TTL_DAYS),
        )
        connection.commit()
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to store mentor cache entry")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------------------
# Student context (same data and limits as the original endpoint)
# ---------------------------------------------------------------------
def load_student_context_for_prompt(student_id):
    student_context = {
        "student_name": None,
        "career_interest": None,
        "skills": [],
        "plan": None,
        "tasks": [],
    }
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT name, career_interest FROM students WHERE id = %s",
            (student_id,),
        )
        student = cursor.fetchone()
        if student:
            student_context["student_name"] = student.get("name")
            student_context["career_interest"] = student.get("career_interest")

        cursor.execute(
            """
            SELECT s.name AS skill, ss.proficiency_level
            FROM student_skills ss
            JOIN skills s ON s.id = ss.skill_id
            WHERE ss.student_id = %s
            ORDER BY s.name
            """,
            (student_id,),
        )
        student_context["skills"] = cursor.fetchall()

        cursor.execute(
            """
            SELECT sp.id AS plan_id, c.title AS career, c.description
            FROM study_plans sp
            JOIN careers c ON c.id = sp.career_id
            WHERE sp.student_id = %s
            ORDER BY sp.created_at DESC, sp.id DESC
            LIMIT 1
            """,
            (student_id,),
        )
        plan = cursor.fetchone()
        student_context["plan"] = plan

        if plan:
            cursor.execute(
                """
                SELECT st.task_title, st.completed, st.estimated_minutes, s.name AS skill
                FROM study_tasks st
                JOIN skills s ON s.id = st.skill_id
                WHERE st.plan_id = %s
                ORDER BY st.id
                """,
                (plan["plan_id"],),
            )
            student_context["tasks"] = [
                {
                    "task_title": task["task_title"],
                    "skill": task["skill"],
                    "completed": bool(task["completed"]),
                    "estimated_minutes": task["estimated_minutes"],
                }
                for task in cursor.fetchall()
            ]
    except mysql.connector.Error:
        app.logger.exception(
            "Unable to load saved student context for AI Mentor (student_id=%s).",
            student_id,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    tasks = student_context["tasks"]
    completed_tasks = [t for t in tasks if t["completed"]]
    pending_tasks = [t for t in tasks if not t["completed"]]
    return {
        "student_name": student_context["student_name"] or "Not saved",
        "career_interest": student_context["career_interest"] or "Not saved",
        "current_skills": student_context["skills"][:20],
        "roadmap_career": (
            student_context["plan"]["career"] if student_context["plan"] else None
        ),
        "roadmap_exists": bool(student_context["plan"]),
        "total_roadmap_tasks": len(tasks),
        "completed_task_count": len(completed_tasks),
        "pending_task_count": len(pending_tasks),
        "completed_tasks": completed_tasks[:15],
        "pending_tasks": pending_tasks[:15],
    }


def build_gemini_prompt(message, context_for_prompt=None):
    """
    With context  -> personalised prompt (identical rules to the original).
    Without       -> generic prompt, so the answer is safe to share via the cache.
    """
    prompt = (
        "You are CareerMate, a friendly AI learning and career mentor "
        "for college students. Give practical, beginner-friendly advice "
        "about careers, technical skills, projects, internships, and interviews.\n\n"
    )
    if context_for_prompt is not None:
        prompt += (
            "Use the student's SAVED CareerMate context below when relevant. "
            "Do not invent skills, completed tasks, career interests, or progress. "
            "If a field says Not saved, or no roadmap exists, be honest about that "
            "and ask only for the missing information that is genuinely needed. "
            "When roadmap tasks are available, clearly distinguish completed tasks "
            "from pending tasks and recommend a sensible next pending task. "
            "Use the saved proficiency levels as the student's current skill data. "
            "Do not claim to guarantee jobs or placements.\n\n"
        )
    else:
        prompt += "Do not claim to guarantee jobs or placements.\n\n"

    prompt += (
        "For comparisons or tables, return a valid GitHub-Flavored Markdown "
        "table with each row on a separate line and a header separator row.\n\n"
    )
    if context_for_prompt is not None:
        prompt += (
            "SAVED STUDENT CONTEXT (JSON):\n"
            + json.dumps(context_for_prompt, ensure_ascii=False, default=str)
            + "\n\n"
        )
    return prompt + "Student's question:\n" + message


def call_gemini(prompt):
    """One request, no retries, bounded by GEMINI_TIMEOUT_MS. Raises on failure."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from the backend environment.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=GEMINI_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=1024),
    )
    return response.text if response else None


# ---------------------------------------------------------------------
# Conversation / history persistence (same SQL and ownership checks as before)
# ---------------------------------------------------------------------
def student_owns_conversation(student_id, conversation_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM mentor_conversations WHERE id = %s AND student_id = %s",
            (conversation_id, student_id),
        )
        return cursor.fetchone() is not None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def save_chat_exchange(student_id, conversation_id, message, answer):
    """Save the Q/A pair. Returns the conversation id (new one if none was given)."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if conversation_id is None:
            # Compatibility fallback for older frontend clients.
            title = message[:70].strip() or "New chat"
            cursor.execute(
                "INSERT INTO mentor_conversations (student_id, title) VALUES (%s, %s)",
                (student_id, title),
            )
            conversation_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO chat_history
               (student_id, conversation_id, user_message, assistant_message)
               VALUES (%s, %s, %s, %s)""",
            (student_id, conversation_id, message, answer.strip()),
        )
        cursor.execute(
            """UPDATE mentor_conversations
               SET title = CASE WHEN title = 'New chat' THEN %s ELSE title END,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND student_id = %s""",
            (message[:70].strip() or "New chat", conversation_id, student_id),
        )
        connection.commit()
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception(
            "Unable to save AI Mentor chat history (student_id=%s).", student_id
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
    return conversation_id


def save_seven_day_plan(student_id, message, answer):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO mentor_learning_plans (student_id, prompt, plan_text)
            VALUES (%s, %s, %s)
            """,
            (student_id, message, answer),
        )
        plan_id = cursor.lastrowid
        connection.commit()
        return plan_id
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception(
            "Unable to save generated mentor plan (student_id=%s).", student_id
        )
        return None  # keep the generated answer available even if persistence fails
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------
@app.route("/api/mentor/chat", methods=["POST"])
def mentor_chat():
    """
    Answer the authenticated student's question.

    Order of resolution:
      1. mentor_response_cache   (exact, normalised-question hit)
      2. mentor_knowledge_base   (keyword relevance >= KB_MATCH_THRESHOLD)
      3. Gemini                  (fallback; generic answers are cached)
    Personal questions ("my progress...") and 7-day plan requests skip 1-2.
    """
    # ---- Authentication & validation: unchanged behaviour ----
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({"error": "Please log in to use the AI Mentor."}), 401

    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    if not isinstance(message, str):
        return jsonify({"error": "Please enter a valid text message."}), 400

    message = message.strip()

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    if len(message) > 4000:
        return jsonify({
            "error": "Message is too long. Please keep it under 4000 characters."
        }), 400

    # Validate conversation ownership BEFORE spending any Gemini call.
    conversation_id = data.get("conversation_id")
    if conversation_id is not None:
        try:
            conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid conversation."}), 400
        try:
            if not student_owns_conversation(student_id, conversation_id):
                return jsonify({"error": "Conversation not found."}), 404
        except mysql.connector.Error:
            app.logger.exception(
                "Unable to verify conversation ownership (student_id=%s).", student_id
            )
            return jsonify({"error": "Unable to load this conversation."}), 500

    # ---- 1. Parse and normalise ----
    tokens = normalize_question(message)
    normalized_question, question_hash = question_fingerprint(tokens)
    plan_request = is_seven_day_plan_request(message)
    personalized = is_personalized_question(message)
    # Only generic questions may use (or populate) the shared cache / KB.
    use_shared = bool(tokens) and not (plan_request or personalized)

    answer = None
    source = None
    best_entry, best_score = None, 0.0

    if use_shared:
        # ---- 2a. Cache ----
        answer = get_cached_answer(question_hash)
        if answer:
            source = "cache"

        # ---- 2b. Knowledge base with relevance threshold ----
        if not answer and len(tokens) <= KB_MAX_QUERY_TOKENS:
            best_entry, best_score = find_kb_match(tokens, load_knowledge_base())
            if best_entry is not None and best_score >= KB_MATCH_THRESHOLD:
                answer = best_entry["answer_text"]
                source = "knowledge_base"
                app.logger.info(
                    "Mentor KB hit id=%s score=%.2f (student_id=%s).",
                    best_entry["id"], best_score, student_id,
                )

    # ---- 3. Gemini fallback ----
    if not answer:
        failure = None  # (reason, http_status, student-facing message)
        try:
            context = (
                None if use_shared else load_student_context_for_prompt(student_id)
            )
            prompt = build_gemini_prompt(message, context)
            started_at = time.monotonic()
            answer = call_gemini(prompt)
            app.logger.info(
                "Gemini generation completed in %.2f seconds (student_id=%s).",
                time.monotonic() - started_at,
                student_id,
            )

            if not answer or not answer.strip():
                app.logger.warning("Gemini returned an empty response.")
                answer = None
                failure = (
                    "empty_response", 502,
                    "The AI Mentor could not generate a response. Please try again.",
                )
            else:
                source = "gemini"

        except (ApiCoreDeadlineExceeded, httpx.TimeoutException, TimeoutError):
            # Gemini 504 DEADLINE_EXCEEDED (old SDK / transport-level timeout).
            app.logger.warning(
                "Gemini deadline exceeded after %s ms (student_id=%s).",
                GEMINI_TIMEOUT_MS, student_id,
            )
            failure = (
                "ai_timeout", 504,
                "The AI Mentor is taking too long to respond right now. "
                "Please try again in a moment.",
            )

        except genai_errors.APIError as error:
            # google-genai raises APIError subclasses; a server-side 504 arrives
            # here with code=504 / status='DEADLINE_EXCEEDED'.
            code = getattr(error, "code", None)
            status = str(getattr(error, "status", "") or "").upper()
            if code == 504 or "DEADLINE_EXCEEDED" in status:
                app.logger.warning(
                    "Gemini returned 504 DEADLINE_EXCEEDED (student_id=%s).", student_id
                )
                failure = (
                    "ai_timeout", 504,
                    "The AI Mentor is taking too long to respond right now. "
                    "Please try again in a moment.",
                )
            elif code == 429:
                app.logger.warning("Gemini rate limit reached (student_id=%s).", student_id)
                failure = (
                    "ai_rate_limited", 429,
                    "The AI Mentor is busy right now. Please try again shortly.",
                )
            else:
                app.logger.exception("Gemini API error (code=%s).", code)
                failure = (
                    "ai_unavailable", 502,
                    "The AI Mentor is temporarily unavailable. Please try again.",
                )

        except RuntimeError:
            app.logger.error("GEMINI_API_KEY is missing from the backend environment.")
            failure = ("ai_not_configured", 500, "The AI Mentor is not configured yet.")

        except Exception as error:
            app.logger.exception(
                "CareerMate AI Mentor request failed (%s).", type(error).__name__
            )
            failure = (
                "ai_unavailable", 502,
                "The AI Mentor is temporarily unavailable. Please try again.",
            )

        if failure is not None:
            reason, http_status, public_message = failure

            # Graceful degradation: offer the closest curated answer, if any.
            if (
                use_shared
                and best_entry is not None
                and best_score >= KB_SOFT_THRESHOLD
            ):
                notice = (
                    "The live AI service is slow right now, so here is the closest "
                    "information from CareerMate's library:\n\n"
                )
                degraded_reply = notice + best_entry["answer_text"]
                conversation_id = save_chat_exchange(
                    student_id, conversation_id, message, degraded_reply
                )
                return jsonify({
                    "reply": degraded_reply,
                    "source": "knowledge_base_fallback",
                    "student_id": student_id,
                    "conversation_id": conversation_id,
                    "saved_plan_id": None,
                    "plan_saved": False,
                }), 200

            return jsonify({"error": public_message, "reason": reason}), http_status

        # Cache only generic Gemini answers (never personalised ones).
        if use_shared:
            store_cached_answer(question_hash, normalized_question, answer.strip())

    # ---- Persist chat + optional 7-day plan, then respond ----
    conversation_id = save_chat_exchange(student_id, conversation_id, message, answer)

    saved_plan_id = None
    if plan_request and source == "gemini":
        saved_plan_id = save_seven_day_plan(student_id, message, answer)

    return jsonify({
        "reply": answer,
        "source": source,
        "student_id": student_id,
        "conversation_id": conversation_id,
        "saved_plan_id": saved_plan_id,
        "plan_saved": saved_plan_id is not None,
    }), 200
