
import requests

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

email = input("Enter your registered email: ")
password = input("Enter your password: ")

# Log in and preserve the session cookie
login_response = session.post(
    f"{BASE_URL}/api/students/login",
    json={"email": email, "password": password}
)

print("\nLogin status:", login_response.status_code)

if login_response.status_code != 200:
    print("Login failed:", login_response.text)
    raise SystemExit

student = login_response.json()["student"]
student_id = student["id"]

print("Logged in as student ID:", student_id)

# Test access to another student's progress
other_student_id = 2 if student_id != 2 else 4

response = session.get(
    f"{BASE_URL}/api/students/{other_student_id}/progress"
)

print("\nOther student's progress test")
print("HTTP status:", response.status_code)
print("Response:", response.text)

session.post(f"{BASE_URL}/api/students/logout")
