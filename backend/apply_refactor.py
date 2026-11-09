"""
Replaces the old /api/mentor/chat endpoint in app.py with the contents of
mentor_chat_refactor.py. Everything else in app.py is left untouched.

Run from the backend folder:   python apply_refactor.py
A backup is saved first as app_before_mentor_refactor.py.
"""
import shutil
import sys
from pathlib import Path

APP = Path("app.py")
PATCH = Path("mentor_chat_refactor.py")
BACKUP = Path("app_before_mentor_refactor.py")

START = '@app.route("/api/mentor/chat", methods=["POST"])'
END = '@app.route("/api/mentor/plans/latest", methods=["GET"])'


def fail(message):
    print(f"STOPPED: {message}\napp.py was NOT changed.")
    sys.exit(1)


for path in (APP, PATCH):
    if not path.exists():
        fail(f"{path} not found. Run this from the backend folder.")

source = APP.read_text(encoding="utf-8")
patch = PATCH.read_text(encoding="utf-8")

if "def call_gemini" in source:
    print("The refactor is already applied to app.py. Nothing to do.")
    sys.exit(0)

if source.count(START) != 1:
    fail(f"expected exactly one line:\n  {START}\nbut found {source.count(START)}.")
if source.count(END) != 1:
    fail(f"expected exactly one line:\n  {END}\nbut found {source.count(END)}.")

start_index = source.index(START)
end_index = source.index(END)
if start_index > end_index:
    fail("the mentor chat endpoint appears after the plans/latest endpoint; "
         "please replace it manually.")

new_source = source[:start_index] + patch + "\n\n\n" + source[end_index:]

try:
    compile(new_source, "app.py", "exec")
except SyntaxError as error:
    fail(f"the combined file would have a syntax error: {error}")

shutil.copy(APP, BACKUP)
APP.write_text(new_source, encoding="utf-8")
print(f"Done. Old endpoint replaced ({end_index - start_index} characters).")
print(f"Backup saved as {BACKUP}.")
print("Next: restart Flask, then run  python -m pytest -v test_api_independence.py")