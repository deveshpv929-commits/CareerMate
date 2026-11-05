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

cursor = None

tables = [
    """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        password_hash VARCHAR(255) NULL,
        phone_number VARCHAR(15) NULL,
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
    CREATE TABLE IF NOT EXISTS assessment_attempts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        total_questions INT NOT NULL,
        correct_answers INT NOT NULL,
        overall_percentage DECIMAL(5,2) NOT NULL,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        CHECK (total_questions > 0),
        CHECK (correct_answers >= 0),
        CHECK (correct_answers <= total_questions),
        CHECK (overall_percentage BETWEEN 0 AND 100)
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
    CREATE TABLE IF NOT EXISTS mentor_conversations (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        title VARCHAR(120) NOT NULL DEFAULT 'New chat',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_mentor_conversations_student_updated (student_id, updated_at),
        CONSTRAINT fk_mentor_conversations_student
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        conversation_id BIGINT NULL,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_chat_history_conversation (conversation_id, created_at),
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (conversation_id) REFERENCES mentor_conversations(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mentor_learning_plans (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        prompt TEXT NOT NULL,
        plan_text LONGTEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_mentor_plans_student_created (student_id, created_at),
        CONSTRAINT fk_mentor_learning_plans_student
            FOREIGN KEY (student_id) REFERENCES students(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

try:
    cursor = connection.cursor(buffered=True)

    # Create missing tables without deleting existing data.
    for table_sql in tables:
        cursor.execute(table_sql)

    # Add new account fields safely to existing databases without deleting student data.
    cursor.execute("SHOW COLUMNS FROM students LIKE 'phone_number'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE students ADD COLUMN phone_number VARCHAR(15) NULL")
        print("Added phone_number column to students.")

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            token_hash CHAR(64) NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            used_at DATETIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_password_reset_student (student_id),
            CONSTRAINT fk_password_reset_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )"""
    )

    # Add password_hash to an existing students table if necessary.
    cursor.execute("SHOW COLUMNS FROM students LIKE 'password_hash'")

    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE students "
            "ADD COLUMN password_hash VARCHAR(255) NULL"
        )
        print("Added password_hash column to students.")

    # Safely upgrade existing chat_history tables without deleting chat records.
    # Use a buffered cursor so SHOW/COLUMNS/INDEX results are fully consumed.
    cursor = connection.cursor(buffered=True)

    cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'conversation_id'")
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE chat_history ADD COLUMN conversation_id BIGINT NULL"
        )
        print("Added conversation_id column to chat_history.")

    cursor.execute(
        "SHOW INDEX FROM chat_history "
        "WHERE Key_name = 'idx_chat_history_conversation'"
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "CREATE INDEX idx_chat_history_conversation "
            "ON chat_history (conversation_id, created_at)"
        )

    cursor.execute("SHOW CREATE TABLE chat_history")
    create_table_row = cursor.fetchone()
    create_table_sql = create_table_row[1] if create_table_row else ""

    # Add the foreign key only if it is not already present.
    if "FOREIGN KEY (`conversation_id`)" not in create_table_sql:
        try:
            cursor.execute(
                "ALTER TABLE chat_history "
                "ADD CONSTRAINT fk_chat_history_conversation "
                "FOREIGN KEY (conversation_id) "
                "REFERENCES mentor_conversations(id) ON DELETE CASCADE"
            )
        except mysql.connector.Error as exc:
            # Existing historical data may prevent adding this constraint.
            # Keep the data and continue with the safe migration below.
            print(f"Could not add chat-history foreign key: {exc}")
            connection.rollback()
            cursor = connection.cursor(buffered=True)

    # Preserve old chats by grouping unassigned records into one legacy
    # conversation per student. No chat-history rows are deleted.
    cursor.execute(
        "SELECT DISTINCT student_id FROM chat_history "
        "WHERE conversation_id IS NULL"
    )
    legacy_students = [row[0] for row in cursor.fetchall()]

    for legacy_student_id in legacy_students:
        cursor.execute(
            "SELECT id FROM mentor_conversations "
            "WHERE student_id = %s AND title = %s ORDER BY id LIMIT 1",
            (legacy_student_id, "Previous conversation"),
        )
        legacy_conversation = cursor.fetchone()

        if legacy_conversation:
            legacy_conversation_id = legacy_conversation[0]
        else:
            cursor.execute(
                "INSERT INTO mentor_conversations (student_id, title) "
                "VALUES (%s, %s)",
                (legacy_student_id, "Previous conversation"),
            )
            legacy_conversation_id = cursor.lastrowid

        cursor.execute(
            "UPDATE chat_history SET conversation_id = %s "
            "WHERE student_id = %s AND conversation_id IS NULL",
            (legacy_conversation_id, legacy_student_id),
        )

    connection.commit()

    print("Core database tables checked successfully.")

    cursor.execute("SHOW TABLES")
    for (table_name,) in cursor.fetchall():
        print(f"- {table_name}")

except mysql.connector.Error:
    connection.rollback()
    raise

finally:
    if cursor is not None:
        cursor.close()

    if connection.is_connected():
        connection.close()
