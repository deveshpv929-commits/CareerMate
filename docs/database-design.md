# Database Design — AI Learning and Career Mentor

## 1. Database Name
ai_learning_mentor

## 2. Tables

### students
Stores student profile information.
- id: Primary key
- name: Student name
- email: Unique email address
- career_interest: Preferred career
- created_at: Account creation timestamp

### skills
Stores the skills used by the system.
- id: Primary key
- name: Unique skill name
- category: Skill category

### careers
Stores career paths.
- id: Primary key
- title: Career title
- description: Career description

### career_skills
Maps careers to required skills.
- career_id: Foreign key to careers
- skill_id: Foreign key to skills
- target_level: Required proficiency from 1 to 5
- weight: Importance of the skill

### questions
Stores quiz questions.
- id: Primary key
- skill_id: Foreign key to skills
- question_text: Question content
- options: Answer options
- correct_answer: Correct option
- difficulty: Question difficulty
- explanation: Answer explanation

### quiz_results
Stores assessment attempts.
- id: Primary key
- student_id: Foreign key to students
- skill_id: Foreign key to skills
- score: Assessment score
- attempted_at: Attempt timestamp

### student_skills
Stores the latest estimated proficiency for each student skill.
- student_id: Foreign key to students
- skill_id: Foreign key to skills
- proficiency_level: Estimated level from 1 to 5
- updated_at: Last update timestamp

### learning_resources
Stores curated learning material.
- id: Primary key
- skill_id: Foreign key to skills
- title: Resource title
- url: Resource URL
- level: Recommended difficulty

### study_plans
Stores generated learning plans.
- id: Primary key
- student_id: Foreign key to students
- career_id: Foreign key to careers
- created_at: Plan creation timestamp

### study_tasks
Stores tasks belonging to a study plan.
- id: Primary key
- plan_id: Foreign key to study_plans
- skill_id: Foreign key to skills
- resource_id: Foreign key to learning_resources
- task_title: Task description
- estimated_minutes: Estimated time
- completed: Completion status

### chat_history
Stores optional AI mentor conversation history.
- id: Primary key
- student_id: Foreign key to students
- user_message: Student question
- assistant_message: Mentor response
- created_at: Message timestamp

## 3. Design Rules
- Use primary and foreign keys to maintain relationships.
- Use unique constraints for student email and skill names.
- Use a unique constraint on each student-skill pair.
- Use transactions when saving related assessment results.
- Store API keys in environment variables, never in database seed files or source code.
- Do not store passwords as plain text; use a secure password-hashing method if authentication is implemented.