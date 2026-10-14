# API Design — AI Learning and Career Mentor

All endpoints use the prefix `/api`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Verify backend status |
| GET | /careers | Retrieve available career paths |
| GET | /skills | Retrieve available skills |
| GET | /questions | Retrieve assessment questions |
| POST | /assessment/submit | Submit quiz answers |
| GET | /students/{id}/skills | Retrieve a student's skill profile |
| POST | /careers/match | Rank career paths |
| POST | /plan/generate | Generate a personalized learning plan |
| GET | /students/{id}/plan | Retrieve the current study plan |
| POST | /progress/update | Update learning progress |
| POST | /mentor/chat | Ask the AI learning mentor a question |

## API conventions
- Use JSON for request and response bodies.
- Validate incoming data before processing.
- Return suitable HTTP status codes.
- Never expose API keys or sensitive server details.
- Use consistent error responses.
- Protect student-specific endpoints with authentication before public deployment.