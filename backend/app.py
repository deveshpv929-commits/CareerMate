
import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_learning_mentor"),
    )


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
