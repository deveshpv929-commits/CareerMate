
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = "http://127.0.0.1:5000/api/careers/match"

payload = {
    "skills": {
        "Python": 4,
        "SQL": 3,
        "Machine Learning": 3,
        "HTML": 4,
        "CSS": 3,
        "JavaScript": 3
    }
}

request = Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
        print(json.dumps(result, indent=2))
except HTTPError as error:
    print("HTTP error:", error.code)
    print(error.read().decode("utf-8"))
except URLError as error:
    print("Connection error:", error.reason)
