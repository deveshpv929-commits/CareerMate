
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_learning_mentor"),
)

tables = [
    """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        career_interest VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        category VARCHAR(100)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS careers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(150) NOT NULL UNIQUE,
        description TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS career_skills (
        career_id INT NOT NULL,
        skill_id INT NOT NULL,
        target_level TINYINT NOT NULL,
        weight DECIMAL(5,2) DEFAULT 1.00,
        PRIMARY KEY (career_id, skill_id),
        FOREIGN KEY (career_id) REFERENCES careers(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id),
        CHECK (target_level BETWEEN 1 AND 5)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS student_skills (
        student_id INT NOT NULL,
        skill_id INT NOT NULL,
        proficiency_level TINYINT NOT NULL DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, skill_id),
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id),
        CHECK (proficiency_level BETWEEN 1 AND 5)
    )
    """,

    
    """
    CREATE TABLE IF NOT EXISTS questions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        skill_id INT NOT NULL,
        question_text TEXT NOT NULL,
        options JSON NOT NULL,
        correct_answer VARCHAR(255) NOT NULL,
        difficulty ENUM('beginner', 'intermediate', 'advanced')
            DEFAULT 'beginner',
        explanation TEXT,
        FOREIGN KEY (skill_id) REFERENCES skills(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        skill_id INT NOT NULL,
        score DECIMAL(5,2) NOT NULL,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_resources (
        id INT AUTO_INCREMENT PRIMARY KEY,
        skill_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        url VARCHAR(1000) NOT NULL,
        level ENUM('beginner', 'intermediate', 'advanced')
            DEFAULT 'beginner',
        FOREIGN KEY (skill_id) REFERENCES skills(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS study_plans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        career_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (career_id) REFERENCES careers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS study_tasks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        plan_id INT NOT NULL,
        skill_id INT NOT NULL,
        resource_id INT,
        task_title VARCHAR(255) NOT NULL,
        estimated_minutes INT NOT NULL DEFAULT 30,
        completed BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (plan_id) REFERENCES study_plans(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id),
        FOREIGN KEY (resource_id) REFERENCES learning_resources(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )
    """,

]

try:
    cursor = connection.cursor()

    for table_sql in tables:
        cursor.execute(table_sql)

    connection.commit()
    print("Core database tables created successfully.")

    cursor.execute("SHOW TABLES")
    for (table_name,) in cursor.fetchall():
        print(f"- {table_name}")

except mysql.connector.Error:
    connection.rollback()
    raise

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
