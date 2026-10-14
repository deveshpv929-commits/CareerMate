
import json
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

with open(PROJECT_ROOT / "data" / "careers.json", encoding="utf-8") as file:
    careers = json.load(file)

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_learning_mentor"),
)

try:
    cursor = connection.cursor()

    for career in careers:
        cursor.execute(
            """
            INSERT INTO careers (title, description)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE description = %s
            """,
            (career["title"], career["description"], career["description"]),
        )

        career_id = cursor.lastrowid

        if not career_id:
            cursor.execute(
                "SELECT id FROM careers WHERE title = %s",
                (career["title"],),
            )
            career_id = cursor.fetchone()[0]

        for skill_name, target_level in career["skills"].items():
            cursor.execute(
                """
                INSERT INTO skills (name, category)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
                """,
                (skill_name, "Technical"),
            )

            skill_id = cursor.lastrowid

            if not skill_id:
                cursor.execute(
                    "SELECT id FROM skills WHERE name = %s",
                    (skill_name,),
                )
                skill_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO career_skills
                    (career_id, skill_id, target_level, weight)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    target_level = VALUES(target_level),
                    weight = VALUES(weight)
                """,
                (career_id, skill_id, target_level, 1.0),
            )

    connection.commit()
    print(f"Successfully loaded {len(careers)} career profiles.")

    cursor.execute("SELECT title FROM careers ORDER BY title")
    for (title,) in cursor.fetchall():
        print(f"- {title}")

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()
