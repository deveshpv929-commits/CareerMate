from flask import Flask, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
import json
import os
import re
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from urllib.parse import quote
from mentor_engine import generate_hybrid_answer

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

CORS(
    app,
    origins=["http://localhost:5173"],
    supports_credentials=True
)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_learning_mentor"),
    )


def is_valid_gmail(email):
    """Accept a non-empty local part and the exact gmail.com domain only."""
    if not isinstance(email, str):
        return False
    email = email.strip()
    if email.count("@") != 1:
        return False
    local_part, domain = email.rsplit("@", 1)
    return bool(local_part and not any(ch.isspace() for ch in local_part) and domain.lower() == "gmail.com" and len(email) <= 254)


def send_password_reset_email(recipient, reset_url):
    """Send a reset link using SMTP settings supplied through environment variables."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    sender = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not all([host, sender, smtp_password]):
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST, SMTP_EMAIL, and SMTP_PASSWORD in backend/.env.")

    message = EmailMessage()
    message["Subject"] = "Reset your CareerMate password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your CareerMate password.\n\n"
        f"Open this link within 20 minutes to choose a new password:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        server.login(sender, smtp_password)
        server.send_message(message)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "message": "AI Learning and Career Mentor API is running",
    }), 200


@app.route("/api/db-health", methods=["GET"])
def database_health():
    connection = None
    try:
        connection = get_db_connection()
        return jsonify({
            "status": "success",
            "message": "MySQL connection successful",
        }), 200
    except mysql.connector.Error:
        app.logger.exception("Database connection failed")
        return jsonify({
            "status": "error",
            "message": "Database connection failed. Check configuration.",
        }), 500
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/careers/match", methods=["POST"])
def match_careers():
    """
    Rank careers by comparing current student skill levels
    with each career's required skill levels.

    Expected JSON:
    {
        "skills": {
            "Python": 4,
            "SQL": 2,
            "Machine Learning": 3
        }
    }
    """
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "status": "error",
            "message": "Send a valid JSON object.",
        }), 400

    student_skills = payload.get("skills")

    if not isinstance(student_skills, dict) or not student_skills:
        return jsonify({
            "status": "error",
            "message": "Provide a non-empty skills object.",
        }), 400

    normalized_skills = {}

    for name, level in student_skills.items():
        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Skill names must be non-empty strings.",
            }), 400

        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            return jsonify({
                "status": "error",
                "message": f"Level for '{name}' must be a number from 1 to 5.",
            }), 400

        if not 1 <= level <= 5:
            return jsonify({
                "status": "error",
                "message": f"Level for '{name}' must be from 1 to 5.",
            }), 400

        normalized_skills[name.strip().casefold()] = float(level)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                c.id AS career_id,
                c.title,
                c.description,
                s.name AS skill_name,
                cs.target_level,
                cs.weight
            FROM careers c
            JOIN career_skills cs ON cs.career_id = c.id
            JOIN skills s ON s.id = cs.skill_id
            ORDER BY c.title, s.name
        """)

        rows = cursor.fetchall()

        if not rows:
            return jsonify({
                "status": "error",
                "message": "No career-skill mappings found. Seed the database first.",
            }), 500

        careers = {}

        for row in rows:
            career_id = row["career_id"]

            if career_id not in careers:
                careers[career_id] = {
                    "title": row["title"],
                    "description": row["description"],
                    "requirements": [],
                }

            careers[career_id]["requirements"].append({
                "name": row["skill_name"],
                "target": float(row["target_level"]),
                "weight": float(row["weight"] or 1),
            })

        results = []

        for career in careers.values():
            total_weight = sum(
                requirement["weight"]
                for requirement in career["requirements"]
            )

            weighted_score = 0.0
            skill_gaps = []
            matched_skills = []

            for requirement in career["requirements"]:
                name = requirement["name"]
                target = requirement["target"]
                weight = requirement["weight"]
                current = normalized_skills.get(name.casefold(), 0.0)

                # Cap proficiency at the required level for matching.
                skill_score = min(current / target, 1.0) if target else 1.0
                weighted_score += skill_score * weight

                if current >= target:
                    matched_skills.append(name)
                else:
                    skill_gaps.append({
                        "skill": name,
                        "current_level": current,
                        "target_level": target,
                        "gap": round(target - current, 2),
                    })

            match_percentage = (
                weighted_score / total_weight * 100
                if total_weight else 0.0
            )

            skill_gaps.sort(key=lambda item: item["gap"], reverse=True)

            results.append({
                "career": career["title"],
                "description": career["description"],
                "match_percentage": round(match_percentage, 2),
                "matched_skills": matched_skills,
                "skill_gaps": skill_gaps,
                "recommendation": (
                    "Strong match" if match_percentage >= 75
                    else "Promising match" if match_percentage >= 50
                    else "Development recommended"
                ),
            })

        results.sort(
            key=lambda item: item["match_percentage"],
            reverse=True,
        )

        return jsonify({
            "status": "success",
            "results_count": len(results),
            "recommendations": results,
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Career matching database query failed")
        return jsonify({
            "status": "error",
            "message": "Unable to calculate career matches.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/assessment/questions", methods=["GET"])
def get_assessment_questions():
    """Return assessment questions without exposing their answers."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                q.id,
                q.question_text,
                q.options,
                q.difficulty,
                s.name AS skill
            FROM questions q
            JOIN skills s ON s.id = q.skill_id
            ORDER BY q.id
        """)

        questions = cursor.fetchall()

        for question in questions:
            if isinstance(question["options"], str):
                question["options"] = json.loads(question["options"])

        return jsonify({
            "status": "success",
            "total": len(questions),
            "questions": questions,
        }), 200

    except (mysql.connector.Error, ValueError, TypeError):
        app.logger.exception("Unable to retrieve assessment questions")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve assessment questions.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/assessment/submit", methods=["POST"])
def submit_assessment():
    """
    Grade submitted answers and save the complete assessment
    along with per-skill results.
    """
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "status": "error",
            "message": "Send a valid JSON object.",
        }), 400

    # Use the authenticated student's ID from the Flask session.
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in before submitting your assessment.",
        }), 401

    answers = payload.get("answers")

    if (
        isinstance(student_id, bool)
        or not isinstance(student_id, int)
        or student_id <= 0
    ):
        return jsonify({
            "status": "error",
            "message": "A valid student_id is required.",
        }), 400

    if not isinstance(answers, list) or not answers:
        return jsonify({
            "status": "error",
            "message": "Provide at least one answer.",
        }), 400

    submitted = {}

    for item in answers:
        if not isinstance(item, dict):
            return jsonify({
                "status": "error",
                "message": "Each answer must be an object.",
            }), 400

        question_id = item.get("question_id")
        answer = item.get("answer")

        if (
            isinstance(question_id, bool)
            or not isinstance(question_id, int)
            or question_id <= 0
        ):
            return jsonify({
                "status": "error",
                "message": "Each question_id must be a positive integer.",
            }), 400

        if not isinstance(answer, str):
            return jsonify({
                "status": "error",
                "message": "Each answer must be a string.",
            }), 400

        if question_id in submitted:
            return jsonify({
                "status": "error",
                "message": "Duplicate question IDs are not allowed.",
            }), 400

        submitted[question_id] = answer

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Verify that the student exists.
        cursor.execute(
            "SELECT id FROM students WHERE id = %s",
            (student_id,),
        )

        if cursor.fetchone() is None:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Student not found. Create a student record first.",
            }), 404

        # Retrieve correct answers and their associated skills.
        placeholders = ", ".join(["%s"] * len(submitted))

        cursor.execute(
            f"""
            SELECT
                q.id,
                q.correct_answer,
                s.id AS skill_id,
                s.name AS skill
            FROM questions q
            JOIN skills s ON s.id = q.skill_id
            WHERE q.id IN ({placeholders})
            """,
            tuple(submitted.keys()),
        )

        question_rows = cursor.fetchall()

        if len(question_rows) != len(submitted):
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": "One or more question IDs do not exist.",
            }), 400

        # Calculate results for each skill.
        skill_results = {}

        for question in question_rows:
            skill_id = question["skill_id"]
            skill_name = question["skill"]
            correct_answer = question["correct_answer"]
            user_answer = submitted[question["id"]]

            if skill_id not in skill_results:
                skill_results[skill_id] = {
                    "skill": skill_name,
                    "total": 0,
                    "correct": 0,
                }

            skill_results[skill_id]["total"] += 1

            if user_answer.strip() == correct_answer:
                skill_results[skill_id]["correct"] += 1

        total_correct = sum(
            result["correct"]
            for result in skill_results.values()
        )
        total_questions = len(question_rows)
        percentage = round(
            total_correct / total_questions * 100, 2
        )

        # NEW: Save the complete assessment attempt.
        cursor.execute(
            """
            INSERT INTO assessment_attempts (
                student_id,
                total_questions,
                correct_answers,
                overall_percentage
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                student_id,
                total_questions,
                total_correct,
                percentage,
            ),
        )

        assessment_attempt_id = cursor.lastrowid

        # Save one quiz result per assessed skill and update proficiency.
        for skill_id, result in skill_results.items():
            skill_percentage = (
                result["correct"] / result["total"] * 100
            )

            proficiency = max(
                1,
                min(5, 1 + int(skill_percentage // 25)),
            )

            cursor.execute(
                """
                INSERT INTO quiz_results (
                    student_id,
                    skill_id,
                    score
                )
                VALUES (%s, %s, %s)
                """,
                (
                    student_id,
                    skill_id,
                    round(skill_percentage, 2),
                ),
            )

            cursor.execute(
                """
                INSERT INTO student_skills (
                    student_id,
                    skill_id,
                    proficiency_level
                )
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    proficiency_level = VALUES(proficiency_level)
                """,
                (student_id, skill_id, proficiency),
            )

            result["score_percentage"] = round(
                skill_percentage, 2
            )
            result["proficiency_level"] = proficiency

        # Commit the attempt and all skill results together.
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Assessment submitted successfully.",
            "assessment_attempt_id": assessment_attempt_id,
            "total_questions": total_questions,
            "correct_answers": total_correct,
            "overall_percentage": percentage,
            "skill_results": list(skill_results.values()),
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        app.logger.exception("Assessment submission failed")

        return jsonify({
            "status": "error",
            "message": "Unable to save assessment results.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/register", methods=["POST"])
def register_student():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "status": "error",
            "message": "Send a valid JSON object.",
        }), 400

    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")
    phone_number = payload.get("phone_number")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Name is required.",
        }), 400

    if not is_valid_gmail(email):
        return jsonify({
            "status": "error",
            "message": "Use a valid Gmail address ending exactly in @gmail.com.",
        }), 400

    if not isinstance(phone_number, str) or not re.fullmatch(r"[6-9][0-9]{9}", phone_number.strip()):
        return jsonify({
            "status": "error",
            "message": "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.",
        }), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "Password must contain at least 8 characters.",
        }), 400

    email = email.strip().lower()
    password_hash = generate_password_hash(password)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO students (name, email, phone_number, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (name.strip(), email.strip().lower(), phone_number.strip(), password_hash),
        )

        student_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful.",
            "student": {
                "id": student_id,
                "name": name.strip(),
                "email": email.strip().lower(),
                "phone_number": phone_number.strip(),
            },
        }), 201

    except mysql.connector.IntegrityError:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "This email is already registered.",
        }), 409

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        app.logger.exception("Student registration failed")

        return jsonify({
            "status": "error",
            "message": "Unable to register student.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/forgot-password", methods=["POST"])
def forgot_password():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not is_valid_gmail(payload.get("email")):
        return jsonify({"status": "error", "message": "Enter a valid Gmail address ending in @gmail.com."}), 400

    email = payload["email"].strip().lower()
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, email FROM students WHERE email = %s", (email,))
        student = cursor.fetchone()
        # Return the same public response for unknown accounts to avoid account enumeration.
        if not student:
            return jsonify({"status": "success", "message": "If a CareerMate account exists for that Gmail address, a password reset link will be sent."}), 200

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        cursor.execute("UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE student_id = %s AND used_at IS NULL", (student["id"],))
        cursor.execute(
            "INSERT INTO password_reset_tokens (student_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (student["id"], token_hash, datetime.utcnow() + timedelta(minutes=20)),
        )
        connection.commit()
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        reset_url = f"{frontend_url}/?token={quote(raw_token)}"
        try:
            send_password_reset_email(student["email"], reset_url)
        except Exception:
            app.logger.exception("Password reset email could not be sent. Check SMTP configuration.")
            # Do not reveal whether the account exists. The server log contains the configuration error.
        return jsonify({"status": "success", "message": "If a CareerMate account exists for that Gmail address, a password reset link will be sent."}), 200
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Forgot password request failed")
        return jsonify({"status": "error", "message": "Unable to process the request right now. Please try again later."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/reset-password", methods=["POST"])
def reset_password():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "Send a valid JSON object."}), 400
    token = payload.get("token")
    password = payload.get("password")
    if not isinstance(token, str) or not token or not isinstance(password, str) or len(password) < 8:
        return jsonify({"status": "error", "message": "A valid reset token and a password of at least 8 characters are required."}), 400

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, student_id FROM password_reset_tokens
               WHERE token_hash = %s AND used_at IS NULL AND expires_at > UTC_TIMESTAMP()
               LIMIT 1""",
            (token_hash,),
        )
        reset_record = cursor.fetchone()
        if not reset_record:
            return jsonify({"status": "error", "message": "This reset link is invalid or has expired. Please request a new one."}), 400

        cursor.execute("UPDATE students SET password_hash = %s WHERE id = %s", (generate_password_hash(password), reset_record["student_id"]))
        cursor.execute("UPDATE password_reset_tokens SET used_at = UTC_TIMESTAMP() WHERE student_id = %s AND used_at IS NULL", (reset_record["student_id"],))
        connection.commit()
        return jsonify({"status": "success", "message": "Password reset successful. You can now log in."}), 200
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Password reset failed")
        return jsonify({"status": "error", "message": "Unable to reset password right now. Please try again later."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/login", methods=["POST"])
def login_student():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "status": "error",
            "message": "Send a valid JSON object.",
        }), 400

    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not email.strip():
        return jsonify({
            "status": "error",
            "message": "Email is required.",
        }), 400

    if not isinstance(password, str) or not password:
        return jsonify({
            "status": "error",
            "message": "Password is required.",
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password_hash
            FROM students
            WHERE email = %s
            """,
            (email.strip().lower(),),
        )

        student = cursor.fetchone()

        if (
            student is None
            or not student["password_hash"]
            or not check_password_hash(
                student["password_hash"], password
            )
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid email or password.",
            }), 401

        # Start a fresh session for the authenticated student.
        session.clear()
        session["student_id"] = student["id"]

        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "student": {
                "id": student["id"],
                "name": student["name"],
                "email": student["email"],
            },
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Student login failed")

        return jsonify({
            "status": "error",
            "message": "Unable to log in. Please try again.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/me", methods=["GET"])
def current_student():
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in first.",
        }), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, career_interest
            FROM students
            WHERE id = %s
            """,
            (student_id,),
        )

        student = cursor.fetchone()

        if student is None:
            session.clear()
            return jsonify({
                "status": "error",
                "message": "Student account not found.",
            }), 404

        return jsonify({
            "status": "success",
            "student": student,
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Unable to retrieve current student")

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve student account.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/students/logout", methods=["POST"])
def logout_student():
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully.",
    }), 200

@app.route("/api/students/<int:student_id>/progress", methods=["GET"])
def get_student_progress(student_id):
    """Retrieve a student's assessment history and current skill levels."""

    authenticated_student_id = session.get("student_id")

    if not authenticated_student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in to view your progress."
        }), 401

    if student_id != authenticated_student_id:
        return jsonify({
            "status": "error",
            "message": "You cannot access another student's progress."
        }), 403

    connection = None
    cursor = None
  

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that the student exists.
        cursor.execute(
            "SELECT id, name, email FROM students WHERE id = %s",
            (student_id,),
        )
        student = cursor.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student not found.",
            }), 404

        # Retrieve all saved assessment attempts.
        cursor.execute(
            """
            SELECT
                id,
                total_questions,
                correct_answers,
                overall_percentage,
                attempted_at
            FROM assessment_attempts
            WHERE student_id = %s
            ORDER BY attempted_at DESC, id DESC
            """,
            (student_id,),
        )
        attempts = cursor.fetchall()

        # Retrieve the student's current proficiency levels.
        cursor.execute(
            """
            SELECT
                s.name AS skill,
                ss.proficiency_level,
                ss.updated_at
            FROM student_skills ss
            JOIN skills s ON s.id = ss.skill_id
            WHERE ss.student_id = %s
            ORDER BY s.name
            """,
            (student_id,),
        )
        skills = cursor.fetchall()

        # Convert database timestamps into JSON-friendly strings.
        for attempt in attempts:
            if attempt["attempted_at"]:
                attempt["attempted_at"] = (
                    attempt["attempted_at"].isoformat()
                )

        for skill in skills:
            if skill["updated_at"]:
                skill["updated_at"] = skill["updated_at"].isoformat()

        return jsonify({
            "status": "success",
            "student": student,
            "assessment_attempts": attempts,
            "current_skills": skills,
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Unable to retrieve student progress")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve student progress.",
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()



# ==============================
# DAY 4: PERSONALIZED LEARNING ROADMAP
# ==============================

@app.route("/api/plan/generate", methods=["POST"])

def generate_learning_plan():
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in first."
        }), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # 1. Get the student's selected career.
        cursor.execute(
            """
            SELECT career_interest
            FROM students
            WHERE id = %s
            """,
            (student_id,)
        )
        student = cursor.fetchone()

        if not student:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Student account not found."
            }), 404

        career_title = student.get("career_interest")

        # Allow a career to be selected in the request.
        payload = request.get_json(silent=True) or {}
        requested_career = payload.get("career")

        if requested_career is not None:
            if (
                not isinstance(requested_career, str)
                or not requested_career.strip()
            ):
                connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Enter a valid career name."
                }), 400

            career_title = requested_career.strip()

        if not career_title:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": (
                    "Select a career before generating a roadmap."
                )
            }), 400

        # 2. Find the selected career.
        cursor.execute(
            """
            SELECT id, title, description
            FROM careers
            WHERE LOWER(title) = LOWER(%s)
            """,
            (career_title,)
        )
        career = cursor.fetchone()

        if not career:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Career not found in the database."
            }), 404

        # 3. Find required skills and current proficiency levels.
        cursor.execute(
            """
            SELECT
                s.id AS skill_id,
                s.name AS skill_name,
                cs.target_level,
                COALESCE(ss.proficiency_level, 0) AS current_level,
                cs.weight
            FROM career_skills cs
            JOIN skills s ON s.id = cs.skill_id
            LEFT JOIN student_skills ss
                ON ss.skill_id = s.id
                AND ss.student_id = %s
            WHERE cs.career_id = %s
            ORDER BY
                (
                    cs.target_level -
                    COALESCE(ss.proficiency_level, 0)
                ) DESC,
                s.name
            """,
            (student_id, career["id"])
        )
        skill_gaps = cursor.fetchall()

        if not skill_gaps:
            connection.rollback()
            return jsonify({
                "status": "error",
                "message": (
                    "No required skills are mapped to this career yet."
                )
            }), 400

        # 4. Reuse the existing plan for this student and career.
        cursor.execute(
            """
            SELECT id
            FROM study_plans
            WHERE student_id = %s AND career_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (student_id, career["id"])
        )
        plan = cursor.fetchone()

        if plan:
            plan_id = plan["id"]
        else:
            cursor.execute(
                """
                INSERT INTO study_plans (student_id, career_id)
                VALUES (%s, %s)
                """,
                (student_id, career["id"])
            )
            plan_id = cursor.lastrowid

        # Track changes made during this generation request.
        created_count = 0
        updated_count = 0
        preserved_completed_count = 0

        # 5. Synchronize tasks with the latest skill gaps.
        for index, skill in enumerate(skill_gaps, start=1):
            skill_id = skill["skill_id"]
            current_level = int(skill["current_level"])
            target_level = int(skill["target_level"])

            if current_level >= target_level:
                task_description = (
                    f"Review and practise {skill['skill_name']}"
                )
            else:
                task_description = (
                    f"Learn {skill['skill_name']} "
                    f"(Level {max(1, current_level)} to {target_level})"
                )

            task_title = f"Step {index}: {task_description}"

            # Choose the best available learning resource.
            cursor.execute(
                """
                SELECT id
                FROM learning_resources
                WHERE skill_id = %s
                ORDER BY
                    CASE LOWER(level)
                        WHEN 'beginner' THEN 1
                        WHEN 'intermediate' THEN 2
                        WHEN 'advanced' THEN 3
                        ELSE 4
                    END,
                    id
                LIMIT 1
                """,
                (skill_id,)
            )
            resource = cursor.fetchone()

            # Find the existing task for this skill in this plan.
            cursor.execute(
                """
                SELECT id, resource_id, completed, task_title
                FROM study_tasks
                WHERE plan_id = %s AND skill_id = %s
                ORDER BY id
                LIMIT 1
                """,
                (plan_id, skill_id)
            )
            existing_task = cursor.fetchone()

            if existing_task:
                # Never overwrite a completed task.
                if existing_task["completed"]:
                    preserved_completed_count += 1
                    continue

                # Update incomplete tasks when skill levels or
                # available learning resources change.
                new_resource_id = (
                    resource["id"]
                    if resource
                    else existing_task["resource_id"]
                )

                if (
                    existing_task["task_title"] != task_title
                    or existing_task["resource_id"] != new_resource_id
                ):
                    cursor.execute(
                        """
                        UPDATE study_tasks
                        SET task_title = %s,
                            resource_id = %s
                        WHERE id = %s AND plan_id = %s
                        """,
                        (
                            task_title,
                            new_resource_id,
                            existing_task["id"],
                            plan_id
                        )
                    )
                    updated_count += 1

            else:
                # Add a task for a newly mapped skill.
                cursor.execute(
                    """
                    INSERT INTO study_tasks (
                        plan_id,
                        skill_id,
                        resource_id,
                        task_title,
                        estimated_minutes,
                        completed
                    )
                    VALUES (%s, %s, %s, %s, %s, FALSE)
                    """,
                    (
                        plan_id,
                        skill_id,
                        resource["id"] if resource else None,
                        task_title,
                        60
                    )
                )
                created_count += 1

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Learning roadmap is ready and synchronized.",
            "plan_id": plan_id,
            "career": career["title"],
            "tasks_created": created_count > 0,
            "new_tasks_count": created_count,
            "updated_tasks_count": updated_count,
            "completed_tasks_preserved": preserved_completed_count
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        app.logger.exception(
            "Unable to generate learning roadmap"
        )
        return jsonify({
            "status": "error",
            "message": "Unable to generate the learning roadmap."
        }), 500

    except Exception:
        if connection is not None:
            connection.rollback()

        app.logger.exception(
            "Unexpected error while generating learning roadmap"
        )
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.route("/api/students/me/plan", methods=["GET"])
def get_learning_plan():
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in first."
        }), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                sp.id AS plan_id,
                c.title AS career,
                c.description,
                sp.created_at
            FROM study_plans sp
            JOIN careers c ON c.id = sp.career_id
            WHERE sp.student_id = %s
            ORDER BY sp.created_at DESC, sp.id DESC
            LIMIT 1
            """,
            (student_id,)
        )
        plan = cursor.fetchone()

        if not plan:
            return jsonify({
                "status": "success",
                "plan": None,
                "tasks": []
            }), 200

        cursor.execute(
            """
            SELECT
                st.id AS task_id,
                st.task_title,
                st.estimated_minutes,
                st.completed,
                s.name AS skill,
                lr.title AS resource_title,
                lr.url AS resource_url
            FROM study_tasks st
            JOIN skills s ON s.id = st.skill_id
            LEFT JOIN learning_resources lr
                ON lr.id = st.resource_id
            WHERE st.plan_id = %s
            ORDER BY st.id
            """,
            (plan["plan_id"],)
        )
        tasks = cursor.fetchall()

        for task in tasks:
            task["completed"] = bool(task["completed"])

        if plan["created_at"]:
            plan["created_at"] = plan["created_at"].isoformat()

        completed_count = sum(
            1 for task in tasks if task["completed"]
        )

        return jsonify({
            "status": "success",
            "plan": plan,
            "tasks": tasks,
            "total_tasks": len(tasks),
            "completed_tasks": completed_count,
            "progress_percentage": round(
                completed_count / len(tasks) * 100, 2
            ) if tasks else 0
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Unable to retrieve learning roadmap")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve the learning roadmap."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/plan/tasks/<int:task_id>", methods=["PATCH"])
def update_learning_task(task_id):
    student_id = session.get("student_id")

    if not student_id:
        return jsonify({
            "status": "error",
            "message": "Please log in first."
        }), 401

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict) or not isinstance(
        payload.get("completed"), bool
    ):
        return jsonify({
            "status": "error",
            "message": "Provide completed as true or false."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update only tasks belonging to the authenticated student.
        cursor.execute(
            """
            UPDATE study_tasks st
            JOIN study_plans sp ON sp.id = st.plan_id
            SET st.completed = %s
            WHERE st.id = %s AND sp.student_id = %s
            """,
            (payload["completed"], task_id, student_id)
        )

        if cursor.rowcount == 0:
            # Check existence without exposing another student's data.
            cursor.execute(
                """
                SELECT st.id
                FROM study_tasks st
                JOIN study_plans sp ON sp.id = st.plan_id
                WHERE st.id = %s AND sp.student_id = %s
                """,
                (task_id, student_id)
            )

            if cursor.fetchone() is None:
                connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Task not found."
                }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Task progress saved.",
            "task_id": task_id,
            "completed": payload["completed"]
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        app.logger.exception("Unable to update learning task")
        return jsonify({
            "status": "error",
            "message": "Unable to update task progress."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# =========================
# CareerMate AI Mentor Chat
# =========================

import time


@app.route("/api/mentor/conversations", methods=["GET"])
def list_mentor_conversations():
    """List only the authenticated student's AI Mentor conversations."""
    student_id = session.get("student_id")
    if not student_id:
        return jsonify({"error": "Please log in to view chat history."}), 401

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(h.id) AS message_count
            FROM mentor_conversations c
            LEFT JOIN chat_history h ON h.conversation_id = c.id
            WHERE c.student_id = %s
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC, c.id DESC
            """,
            (student_id,),
        )
        conversations = cursor.fetchall()
        for item in conversations:
            for field in ("created_at", "updated_at"):
                if item.get(field):
                    item[field] = item[field].isoformat()
        return jsonify({"conversations": conversations}), 200
    except mysql.connector.Error:
        app.logger.exception("Unable to list mentor conversations for student_id=%s", student_id)
        return jsonify({"error": "Unable to load chat history."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/mentor/conversations", methods=["POST"])
def create_mentor_conversation():
    """Create a new conversation owned by the authenticated student."""
    student_id = session.get("student_id")
    if not student_id:
        return jsonify({"error": "Please log in to start a chat."}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title", "New chat")
    if not isinstance(title, str):
        title = "New chat"
    title = title.strip()[:120] or "New chat"

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO mentor_conversations (student_id, title) VALUES (%s, %s)",
            (student_id, title),
        )
        connection.commit()
        conversation_id = cursor.lastrowid
        return jsonify({"conversation": {"id": conversation_id, "title": title}}), 201
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Unable to create mentor conversation for student_id=%s", student_id)
        return jsonify({"error": "Unable to start a new chat."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/mentor/conversations/<int:conversation_id>", methods=["GET"])
def get_mentor_conversation(conversation_id):
    """Return messages only when the conversation belongs to the current student."""
    student_id = session.get("student_id")
    if not student_id:
        return jsonify({"error": "Please log in to view this conversation."}), 401

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, title FROM mentor_conversations WHERE id = %s AND student_id = %s",
            (conversation_id, student_id),
        )
        conversation = cursor.fetchone()
        if not conversation:
            return jsonify({"error": "Conversation not found."}), 404

        cursor.execute(
            """SELECT id, user_message, assistant_message, created_at
               FROM chat_history
               WHERE conversation_id = %s AND student_id = %s
               ORDER BY created_at ASC, id ASC""",
            (conversation_id, student_id),
        )
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({"role": "user", "text": row["user_message"]})
            messages.append({"role": "assistant", "text": row["assistant_message"]})
        return jsonify({"conversation": conversation, "messages": messages}), 200
    except mysql.connector.Error:
        app.logger.exception("Unable to load mentor conversation %s", conversation_id)
        return jsonify({"error": "Unable to load this conversation."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()




@app.route("/api/mentor/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_mentor_conversation(conversation_id):
    """Delete one conversation and its messages, only for its owning student."""
    student_id = session.get("student_id")
    if not student_id:
        return jsonify({"error": "Please log in to delete chat history."}), 401

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Confirm ownership before deleting anything.
        cursor.execute(
            "SELECT id FROM mentor_conversations WHERE id = %s AND student_id = %s",
            (conversation_id, student_id),
        )
        if not cursor.fetchone():
            return jsonify({"error": "Conversation not found."}), 404

        # Delete only this student's messages for this conversation.
        cursor.execute(
            "DELETE FROM chat_history WHERE conversation_id = %s AND student_id = %s",
            (conversation_id, student_id),
        )
        cursor.execute(
            "DELETE FROM mentor_conversations WHERE id = %s AND student_id = %s",
            (conversation_id, student_id),
        )
        connection.commit()
        return jsonify({
            "message": "Conversation deleted successfully.",
            "conversation_id": conversation_id,
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        app.logger.exception(
            "Unable to delete mentor conversation %s for student_id=%s",
            conversation_id,
            student_id,
        )
        return jsonify({"error": "Unable to delete this conversation."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/mentor/chat", methods=["POST"])
def mentor_chat():
    """Answer the authenticated student's question using saved CareerMate data."""
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

    # Load only this authenticated student's saved profile and roadmap.
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
            """SELECT s.name AS skill, ss.proficiency_level
               FROM student_skills ss
               JOIN skills s ON s.id = ss.skill_id
               WHERE ss.student_id = %s ORDER BY s.name""",
            (student_id,),
        )
        student_context["skills"] = cursor.fetchall()

        cursor.execute(
            """SELECT sp.id AS plan_id, c.title AS career, c.description
               FROM study_plans sp
               JOIN careers c ON c.id = sp.career_id
               WHERE sp.student_id = %s
               ORDER BY sp.created_at DESC, sp.id DESC LIMIT 1""",
            (student_id,),
        )
        student_context["plan"] = cursor.fetchone()
        if student_context["plan"]:
            cursor.execute(
                """SELECT st.task_title, st.completed, st.estimated_minutes,
                          s.name AS skill
                   FROM study_tasks st
                   JOIN skills s ON s.id = st.skill_id
                   WHERE st.plan_id = %s ORDER BY st.id""",
                (student_context["plan"]["plan_id"],),
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
        # Retrieval still works if the profile query fails; log the database issue.
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
    completed_tasks = [task for task in tasks if task["completed"]]
    pending_tasks = [task for task in tasks if not task["completed"]]
    context_for_prompt = {
        "student_id": student_id,
        "student_name": student_context["student_name"] or "Not saved",
        "career_interest": student_context["career_interest"] or "Not saved",
        "current_skills": student_context["skills"][:20],
        "roadmap_career": student_context["plan"]["career"] if student_context["plan"] else None,
        "roadmap_exists": bool(student_context["plan"]),
        "total_roadmap_tasks": len(tasks),
        "completed_task_count": len(completed_tasks),
        "pending_task_count": len(pending_tasks),
        "completed_tasks": completed_tasks[:15],
        "pending_tasks": pending_tasks[:15],
    }

    # Retrieval-first hybrid answer. Gemini is no longer required.
    
    # Retrieve recent conversation history for contextual follow-up questions.
    conversation_history = []
    conversation_id = data.get("conversation_id")

    if conversation_id is not None:
        try:
            conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid conversation."}), 400

        history_connection = None
        history_cursor = None

        try:
            history_connection = get_db_connection()
            history_cursor = history_connection.cursor(dictionary=True)

            # Verify that this conversation belongs to the logged-in student.
            history_cursor.execute(
                """
                SELECT id
                FROM mentor_conversations
                WHERE id = %s AND student_id = %s
                """,
                (conversation_id, student_id),
            )

            if not history_cursor.fetchone():
                return jsonify({"error": "Conversation not found."}), 404

            # Retrieve the six most recent exchanges.
            history_cursor.execute(
                """
                SELECT user_message, assistant_message
                FROM chat_history
                WHERE student_id = %s AND conversation_id = %s
                ORDER BY id DESC
                LIMIT 6
                """,
                (student_id, conversation_id),
            )

            conversation_history = list(reversed(history_cursor.fetchall()))

        except mysql.connector.Error:
            app.logger.exception(
                "Unable to retrieve mentor conversation history."
            )

        finally:
            if history_cursor is not None:
                history_cursor.close()

            if history_connection is not None and history_connection.is_connected():
                history_connection.close()

    context_for_prompt["conversation_history"] = conversation_history
    try:
        context_for_prompt["student_id"] = student_id
        answer, mentor_mode, retrieval_confidence, cache_hit = generate_hybrid_answer(
            message, context_for_prompt
        )

        # Save this question/answer pair to the authenticated student's conversation.
        chat_connection = None
        chat_cursor = None
        conversation_id = data.get("conversation_id")

        try:
            chat_connection = get_db_connection()
            chat_cursor = chat_connection.cursor(dictionary=True)

            if conversation_id is not None:
                try:
                    conversation_id = int(conversation_id)
                except (TypeError, ValueError):
                    return jsonify({"error": "Invalid conversation."}), 400
                chat_cursor.execute(
                    "SELECT id, title FROM mentor_conversations WHERE id = %s AND student_id = %s",
                    (conversation_id, student_id),
                )
                conversation = chat_cursor.fetchone()
                if not conversation:
                    return jsonify({"error": "Conversation not found."}), 404
            else:
                # Compatibility fallback for older frontend clients.
                title = message[:70].strip() or "New chat"
                chat_cursor.execute(
                    "INSERT INTO mentor_conversations (student_id, title) VALUES (%s, %s)",
                    (student_id, title),
                )
                conversation_id = chat_cursor.lastrowid

            chat_cursor.execute(
                """INSERT INTO chat_history
                   (student_id, conversation_id, user_message, assistant_message)
                   VALUES (%s, %s, %s, %s)""",
                (student_id, conversation_id, message, answer.strip()),
            )

            # Replace the placeholder title on the first message, and keep activity current.
            chat_cursor.execute(
                """UPDATE mentor_conversations
                   SET title = CASE WHEN title = 'New chat' THEN %s ELSE title END,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s AND student_id = %s""",
                (message[:70].strip() or "New chat", conversation_id, student_id),
            )
            chat_connection.commit()

        except mysql.connector.Error:
            if chat_connection is not None:
                chat_connection.rollback()
            app.logger.exception(
                "Unable to save AI Mentor chat history (student_id=%s).", student_id
            )
        finally:
            if chat_cursor is not None:
                chat_cursor.close()
            if chat_connection is not None and chat_connection.is_connected():
                chat_connection.close()

        # Persist generated 7-day learning plans so the student can revisit them.
        # Store only plans explicitly requested by the authenticated student.
        normalized_message = message.casefold()
        is_seven_day_plan_request = (
            ("7-day" in normalized_message or "7 day" in normalized_message
             or "seven-day" in normalized_message or "seven day" in normalized_message)
            and "plan" in normalized_message
        )
        saved_plan_id = None

        if is_seven_day_plan_request:
            save_connection = None
            save_cursor = None
            try:
                save_connection = get_db_connection()
                save_cursor = save_connection.cursor()
                save_cursor.execute("""
                    INSERT INTO mentor_learning_plans (student_id, prompt, plan_text)
                    VALUES (%s, %s, %s)
                """, (student_id, message, answer))
                saved_plan_id = save_cursor.lastrowid
                save_connection.commit()
            except mysql.connector.Error:
                if save_connection is not None:
                    save_connection.rollback()
                app.logger.exception(
                    "Unable to save generated mentor plan (student_id=%s).", student_id
                )
                # Keep the generated answer available even if persistence fails.
            finally:
                if save_cursor is not None:
                    save_cursor.close()
                if save_connection is not None and save_connection.is_connected():
                    save_connection.close()

        return jsonify({
            "reply": answer,
            "student_id": student_id,
            "conversation_id": conversation_id,
            "saved_plan_id": saved_plan_id,
            "plan_saved": saved_plan_id is not None,
            "mentor_mode": mentor_mode,
            "retrieval_confidence": round(float(retrieval_confidence), 3),
            "cache_hit": cache_hit,
        }), 200

    except Exception as error:
        app.logger.exception(
            "CareerMate AI Mentor request failed (%s).",
            type(error).__name__,
        )
        return jsonify({
            "error": "The AI Mentor is temporarily unavailable. Please try again."
        }), 502


@app.route("/api/mentor/plans/latest", methods=["GET"])
def get_latest_mentor_plan():
    """Return the authenticated student's most recently saved 7-day plan."""
    student_id = session.get("student_id")
    if not student_id:
        return jsonify({"error": "Please log in to view saved learning plans."}), 401

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, prompt, plan_text, created_at
            FROM mentor_learning_plans
            WHERE student_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        """, (student_id,))
        plan = cursor.fetchone()
        if plan and plan.get("created_at"):
            plan["created_at"] = plan["created_at"].isoformat()
        return jsonify({"status": "success", "plan": plan}), 200
    except mysql.connector.Error:
        app.logger.exception("Unable to retrieve saved mentor plan (student_id=%s).", student_id)
        return jsonify({"error": "Unable to retrieve your saved learning plan."}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, port=5000)





