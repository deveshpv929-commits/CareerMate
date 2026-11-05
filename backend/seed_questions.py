
import json
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

QUESTIONS = [
    {
        "skill": "Python",
        "question": "Which keyword defines a function in Python?",
        "options": ["func", "def", "function", "define"],
        "answer": "def",
        "difficulty": "beginner",
        "explanation": "Python uses the def keyword to define functions.",
    },
    {
        "skill": "Python",
        "question": "What is the output of print(2 ** 3)?",
        "options": ["6", "8", "9", "5"],
        "answer": "8",
        "difficulty": "beginner",
        "explanation": "The ** operator performs exponentiation: 2 raised to 3 is 8.",
    },
    {
        "skill": "Python",
        "question": "Which data type stores unique values?",
        "options": ["List", "Tuple", "Set", "String"],
        "answer": "Set",
        "difficulty": "beginner",
        "explanation": "A Python set stores unique elements.",
    },
    {
        "skill": "SQL",
        "question": "Which SQL command retrieves data from a table?",
        "options": ["GET", "OPEN", "SELECT", "FETCH ALL"],
        "answer": "SELECT",
        "difficulty": "beginner",
        "explanation": "SELECT retrieves rows and columns from database tables.",
    },
    {
        "skill": "SQL",
        "question": "Which clause filters rows based on a condition?",
        "options": ["ORDER BY", "WHERE", "GROUP BY", "SELECT"],
        "answer": "WHERE",
        "difficulty": "beginner",
        "explanation": "WHERE filters rows according to a specified condition.",
    },
    {
        "skill": "SQL",
        "question": "Which function counts rows in a query result?",
        "options": ["SUM()", "TOTAL()", "COUNT()", "NUMBER()"],
        "answer": "COUNT()",
        "difficulty": "beginner",
        "explanation": "COUNT() returns the number of rows or non-NULL values, depending on its argument.",
    },
    {
        "skill": "HTML",
        "question": "Which HTML element creates a hyperlink?",
        "options": ["<link>", "<a>", "<href>", "<url>"],
        "answer": "<a>",
        "difficulty": "beginner",
        "explanation": "The anchor element, <a>, creates hyperlinks.",
    },
    {
        "skill": "CSS",
        "question": "Which CSS property changes text colour?",
        "options": ["font-color", "text-style", "color", "background"],
        "answer": "color",
        "difficulty": "beginner",
        "explanation": "The color property sets an element's text colour.",
    },
    {
        "skill": "JavaScript",
        "question": "Which keyword declares a block-scoped variable that can be reassigned?",
        "options": ["const", "let", "static", "define"],
        "answer": "let",
        "difficulty": "beginner",
        "explanation": "let declares a block-scoped variable that can be reassigned.",
    },
    {
        "skill": "React",
        "question": "Which React hook manages local component state?",
        "options": ["useRoute", "useState", "useStyle", "useFetch"],
        "answer": "useState",
        "difficulty": "beginner",
        "explanation": "useState adds state to a React function component.",
    },
    {
        "skill": "Git",
        "question": "Which command creates a local Git repository?",
        "options": ["git start", "git create", "git init", "git new"],
        "answer": "git init",
        "difficulty": "beginner",
        "explanation": "git init initializes a new Git repository.",
    },
    {
        "skill": "REST APIs",
        "question": "Which HTTP method is commonly used to retrieve a resource?",
        "options": ["POST", "GET", "PATCH", "DELETE"],
        "answer": "GET",
        "difficulty": "beginner",
        "explanation": "GET requests representation of a resource.",
    },
    {
        "skill": "Statistics",
        "question": "What is the arithmetic mean of 2, 4, and 6?",
        "options": ["3", "4", "5", "6"],
        "answer": "4",
        "difficulty": "beginner",
        "explanation": "The mean is (2 + 4 + 6) / 3 = 4.",
    },
    {
        "skill": "Machine Learning",
        "question": "Which type of learning uses labelled training examples?",
        "options": [
            "Unsupervised learning",
            "Supervised learning",
            "Reinforcement learning only",
            "Random search",
        ],
        "answer": "Supervised learning",
        "difficulty": "beginner",
        "explanation": "Supervised learning trains models using labelled examples.",
    },
    {
        "skill": "Networking",
        "question": "Which protocol translates domain names into IP addresses?",
        "options": ["HTTP", "FTP", "DNS", "SMTP"],
        "answer": "DNS",
        "difficulty": "beginner",
        "explanation": "DNS resolves domain names to IP addresses.",
    },
    {
        "skill": "Linux",
        "question": "Which command displays the current working directory?",
        "options": ["ls", "pwd", "cd", "mkdir"],
        "answer": "pwd",
        "difficulty": "beginner",
        "explanation": "pwd prints the current working directory.",
    },
    {
        "skill": "Security Fundamentals",
        "question": "What is the main purpose of multi-factor authentication?",
        "options": [
            "Speed up downloads",
            "Add another layer of identity verification",
            "Compress files",
            "Remove all passwords",
        ],
        "answer": "Add another layer of identity verification",
        "difficulty": "beginner",
        "explanation": "MFA requires multiple forms of verification to strengthen account security.",
    },
    {
        "skill": "Problem Solving",
        "question": "What should you generally do first when solving a programming problem?",
        "options": [
            "Write random code",
            "Understand the requirements",
            "Delete existing files",
            "Choose a framework immediately",
        ],
        "answer": "Understand the requirements",
        "difficulty": "beginner",
        "explanation": "Understanding the problem helps identify requirements and suitable solutions.",
    },
    {
        "skill": "Testing Fundamentals",
        "question": "What is the primary purpose of software testing?",
        "options": [
            "Guarantee zero bugs forever",
            "Find defects and check expected behaviour",
            "Replace requirements",
            "Increase code duplication",
        ],
        "answer": "Find defects and check expected behaviour",
        "difficulty": "beginner",
        "explanation": "Testing checks software behaviour and helps identify defects.",
    },
    {
        "skill": "API Testing",
        "question": "What should you usually verify when testing a successful API request?",
        "options": [
            "Only the button colour",
            "Status code and response content",
            "Only the file name",
            "The keyboard layout",
        ],
        "answer": "Status code and response content",
        "difficulty": "beginner",
        "explanation": "API tests commonly validate status codes, response structure, and expected data.",
    },
    {
        "skill": "Log Analysis",
        "question": "Which information is especially useful when investigating an application error?",
        "options": [
            "Timestamp and error details",
            "Desktop wallpaper",
            "Monitor size",
            "Keyboard brand",
        ],
        "answer": "Timestamp and error details",
        "difficulty": "beginner",
        "explanation": "Timestamps and error details help correlate events and diagnose failures.",
    },
    {
        "skill": "Data Visualization",
        "question": "Which chart is commonly used to compare values across categories?",
        "options": ["Bar chart", "Password field", "Source code file", "Network socket"],
        "answer": "Bar chart",
        "difficulty": "beginner",
        "explanation": "Bar charts make comparisons between categories easy to see.",
    },
    {
        "skill": "Excel",
        "question": "Which Excel function calculates the arithmetic mean?",
        "options": ["COUNT", "AVERAGE", "MAX", "IF"],
        "answer": "AVERAGE",
        "difficulty": "beginner",
        "explanation": "AVERAGE calculates the arithmetic mean of supplied numeric values.",
    },
]

def main():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_learning_mentor"),
    )

    cursor = None

    try:
        cursor = connection.cursor()

        for question in QUESTIONS:
            cursor.execute(
                """
                INSERT INTO skills (name, category)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
                """,
                (question["skill"], "Technical"),
            )

            cursor.execute(
                "SELECT id FROM skills WHERE name = %s",
                (question["skill"],),
            )
            skill_id = cursor.fetchone()[0]

            # Avoid duplicating an identical question if this script is rerun.
            cursor.execute(
                """
                SELECT id FROM questions
                WHERE skill_id = %s AND question_text = %s
                """,
                (skill_id, question["question"]),
            )

            if cursor.fetchone():
                continue

            cursor.execute(
                """
                INSERT INTO questions
                    (skill_id, question_text, options, correct_answer,
                     difficulty, explanation)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    skill_id,
                    question["question"],
                    json.dumps(question["options"]),
                    question["answer"],
                    question["difficulty"],
                    question["explanation"],
                ),
            )

        connection.commit()
        cursor.execute("SELECT COUNT(*) FROM questions")
        total = cursor.fetchone()[0]
        print(f"Assessment questions available in database: {total}")

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
