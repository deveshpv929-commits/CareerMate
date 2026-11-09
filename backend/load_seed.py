"""Loads mentor_knowledge_base_seed.sql into the database from your .env settings."""
import os
from pathlib import Path

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
cursor = connection.cursor()

lines = Path("mentor_knowledge_base_seed.sql").read_text(encoding="utf-8").splitlines()
# Drop the SET NAMES line (the connector already uses utf8mb4) and the final semicolon,
# so the rest runs as one single INSERT statement.
sql = "\n".join(line for line in lines if not line.startswith("SET NAMES")).strip().rstrip(";")

cursor.execute(sql)
connection.commit()
cursor.execute("SELECT DATABASE(), COUNT(*) FROM mentor_knowledge_base")
database, total = cursor.fetchone()
print(f"Done. Database '{database}' now has {total} knowledge-base entries.")
cursor.close()
connection.close()