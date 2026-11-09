"""
Adds the tables needed by the hybrid AI Mentor (cache -> knowledge base -> Gemini).
Safe to run repeatedly: uses CREATE TABLE IF NOT EXISTS and touches no existing data.
Run once:  python mentor_tables_migration.py
"""
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
    # Curated, human-reviewed answers. `keywords` is a comma-separated list
    # that drives retrieval (see find_kb_match in the endpoint code).
    """
    CREATE TABLE IF NOT EXISTS mentor_knowledge_base (
        id INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(100) NOT NULL,
        title VARCHAR(255) NOT NULL,
        keywords TEXT NOT NULL,
        answer_text LONGTEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_mentor_kb_active_category (is_active, category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # Shared (non-personalised) answers only. Never store per-student answers here.
    """
    CREATE TABLE IF NOT EXISTS mentor_response_cache (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        question_hash CHAR(64) NOT NULL UNIQUE,
        normalized_question VARCHAR(500) NOT NULL,
        answer_text LONGTEXT NOT NULL,
        source ENUM('gemini', 'knowledge_base') NOT NULL DEFAULT 'gemini',
        hit_count INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_hit_at DATETIME NULL,
        expires_at DATETIME NULL,
        INDEX idx_mentor_cache_expires (expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

# Example seed row so retrieval can be tested immediately. Add many more.
seed_sql = """
    INSERT INTO mentor_knowledge_base (category, title, keywords, answer_text)
    SELECT %s, %s, %s, %s
    WHERE NOT EXISTS (SELECT 1 FROM mentor_knowledge_base WHERE title = %s)
"""
seed_rows = [
    (
        "Security Fundamentals",
        "What is a firewall",
        "firewall, network firewall, packet filtering, iptables, ufw, block traffic",
        "A firewall is a security control that allows or blocks network traffic "
        "based on rules (IP address, port, protocol). Start with host firewalls "
        "like ufw/iptables on Linux, then learn network firewalls and zones.",
    ),
]

cursor = None
try:
    cursor = connection.cursor(buffered=True)
    for table_sql in tables:
        cursor.execute(table_sql)
    for category, title, keywords, answer in seed_rows:
        cursor.execute(seed_sql, (category, title, keywords, answer, title))
    connection.commit()
    print("Mentor knowledge-base and cache tables are ready.")
except mysql.connector.Error:
    connection.rollback()
    raise
finally:
    if cursor is not None:
        cursor.close()
    if connection.is_connected():
        connection.close()
