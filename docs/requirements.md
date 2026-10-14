# AI-Powered Personalized Learning and Career Mentor

## 1. Problem Statement

Students often struggle to identify their skill gaps, choose suitable career paths, and determine what they should learn next. Existing learning platforms frequently provide generic learning paths without sufficiently considering individual skill levels, career goals, and assessment performance.

This project aims to develop an AI-powered personalized learning and career mentoring system that assesses student skills, recommends suitable career paths, identifies skill gaps, and generates adaptive learning plans using machine learning, natural language processing, and large language models.

## 2. Project Objectives

1. Assess student proficiency through topic-based quizzes.
2. Identify strengths, weaknesses, and skill gaps.
3. Recommend career paths based on student skills and career requirements.
4. Generate personalized learning plans with relevant resources.
5. Provide an AI mentor for learning assistance and explanations.
6. Track progress and adapt recommendations based on assessment results.
7. Evaluate recommendation quality and system performance.

## 3. Core Modules

### Module 1: Student Profile and Skill Assessment
Collect student interests and career preferences. Conduct quizzes and calculate topic-wise proficiency scores.

### Module 2: Skill-Gap Analysis
Compare demonstrated student proficiency against the target skills required for selected careers.

### Module 3: Career Recommendation Engine
Rank suitable career paths using weighted skill matching and semantic similarity.

### Module 4: Personalized Learning Planner
Prioritize weak skills, respect topic prerequisites, and generate realistic weekly learning plans.

### Module 5: AI Learning Mentor
Answer learning questions, explain concepts, and recommend relevant learning resources using an LLM API and curated material.

### Module 6: Progress Tracking and Evaluation
Track quiz results and completed learning tasks, update skill estimates, and evaluate recommendation quality.

## 4. Initial Career Paths

1. Python Developer
2. Frontend Developer
3. Data Analyst
4. Machine Learning Engineer
5. Cybersecurity Analyst
6. QA Engineer

Each career will have a defined set of required skills and target proficiency levels.

## 5. Functional Requirements

- The system shall allow students to create and update their profiles.
- The system shall provide topic-based assessments.
- The system shall calculate skill proficiency scores.
- The system shall identify missing or underdeveloped skills.
- The system shall recommend and rank career paths.
- The system shall explain the reasons behind career recommendations.
- The system shall generate personalized learning plans.
- The system shall provide AI-assisted learning support.
- The system shall store quiz results and learning progress.
- The system shall update recommendations after new assessment results.

## 6. Non-Functional Requirements

- Usability: The interface shall be clear and responsive.
- Performance: Recommendations should return within a reasonable response time.
- Security: API keys and credentials shall be stored in environment variables.
- Reliability: Core assessment and recommendation features shall work even if the LLM service is unavailable.
- Maintainability: Frontend, backend, database, and ML components shall be organized separately.
- Evaluation: Model performance and recommendation quality shall be measured using documented test data.

## 7. Technology Stack

- Frontend: React and Vite
- Backend: Python and Flask
- Database: MySQL
- Machine Learning: scikit-learn, Pandas, NumPy
- NLP: Sentence Transformers
- AI Mentor: LLM API
- Visualization: Chart.js or Recharts
- Version Control: Git and GitHub

## 8. Project Scope

The initial version will support six career paths, topic-based assessments, skill-gap analysis, career recommendations, adaptive learning plans, an AI mentor, and progress tracking.

The project will use curated career data and learning resources. Its recommendations will be decision-support suggestions rather than guarantees of career success.

## 9. Expected Outcome

A working web application that combines machine learning, semantic matching, personalized learning logic, and AI-assisted mentoring to help students understand their skill gaps and plan their learning toward suitable career paths.