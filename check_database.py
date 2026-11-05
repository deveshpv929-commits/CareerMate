
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Locate the project root and load its .env file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

connection = None
cursor = None

try:
    # Use the same database settings as backend/app.py
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "Deveshpv@26"),
        database=os.getenv("DB_NAME", "ai_learning_mentor")
    )

    print("Connected to CareerMate database!")

    cursor = connection.cursor()

    # Display database tables
    cursor.execute("SHOW TABLES")
    print("\n--- Database tables ---")
    for table in cursor.fetchall():
        print(table[0])

    # Display students table structure
    cursor.execute("DESCRIBE students")
    print("\n--- Students table columns ---")
    for column in cursor.fetchall():
        print(column[0], "-", column[1])

    # Display registered students
    cursor.execute(
        "SELECT id, email, created_at FROM students"
    )
    print("\n--- Registered students ---")
    for student in cursor.fetchall():
        print(student)

    # Verify assessment and skill records for student ID 4
    student_id = 4

    for table in [
        "assessment_attempts",
        "quiz_results",
        "student_skills"
    ]:
        print(f"\n--- {table} ---")

        cursor.execute(f"DESCRIBE `{table}`")
        columns = [row[0] for row in cursor.fetchall()]
        print("Columns:", columns)

        if "student_id" in columns:
            cursor.execute(
                f"SELECT * FROM `{table}` "
                "WHERE student_id = %s LIMIT 10",
                (student_id,)
            )

            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    print(row)
            else:
                print(
                    f"No records found for student ID {student_id}"
                )
        else:
            print("No student_id column in this table.")

except (Error, ValueError) as error:
    print("Database verification failed:", error)

finally:
    if cursor is not None:
        cursor.close()

    if connection is not None and connection.is_connected():
        connection.close()
        print("\nDatabase connection closed.")
