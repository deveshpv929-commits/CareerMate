

import { useEffect, useState } from 'react'

import ReactMarkdown from 'react-markdown';

import remarkGfm from 'remark-gfm';

import './App.css'

const API = 'http://localhost:5000/api'

function App() {

  // Authentication

  const [student, setStudent] = useState(null)

  const [authChecked, setAuthChecked] = useState(false)

  const [authMode, setAuthMode] = useState('login')

  const [authName, setAuthName] = useState('')

  const [authPhone, setAuthPhone] = useState('')

  const [authEmail, setAuthEmail] = useState('')

  const [resetToken, setResetToken] = useState(new URLSearchParams(window.location.search).get('token') || '')

  const [newPassword, setNewPassword] = useState('')

  const [confirmPassword, setConfirmPassword] = useState('')

  // Independent show/hide controls for each password field
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  useEffect(() => {
    const tokenFromUrl = new URLSearchParams(window.location.search).get('token')
    if (tokenFromUrl) { setResetToken(tokenFromUrl); setAuthMode('reset') }
  }, [])

  const [authPassword, setAuthPassword] = useState('')

  const [authLoading, setAuthLoading] = useState(false)

  const [authError, setAuthError] = useState('')

  const [authMessage, setAuthMessage] = useState('')

  // Dashboard and assessment

  const [activeTab, setActiveTab] = useState('Overview')

  const [started, setStarted] = useState(false)

  const [questions, setQuestions] = useState([])

  const [current, setCurrent] = useState(0)

  const [answers, setAnswers] = useState({})

  const [finished, setFinished] = useState(false)

  const [loading, setLoading] = useState(false)

  const [error, setError] = useState('')

  const [result, setResult] = useState(null)

  // Career recommendations

  const [careerRecommendations, setCareerRecommendations] = useState([])

  const [careerLoading, setCareerLoading] = useState(false)

  const [careerError, setCareerError] = useState('')

  const [careerLoaded, setCareerLoaded] = useState(false)

  // Career selected by the student for roadmap generation.
  const [selectedCareer, setSelectedCareer] = useState('')

  // Saved student progress

    // Learning roadmap

  const [learningPlan, setLearningPlan] = useState(null)

  const [roadmapTasks, setRoadmapTasks] = useState([])

  const [roadmapLoading, setRoadmapLoading] = useState(false)

  const [roadmapError, setRoadmapError] = useState('')

  const [savedProgress, setSavedProgress] = useState(null)

  const [progressLoading, setProgressLoading] = useState(false)

  const [progressError, setProgressError] = useState('')

  // AI Career Mentor chat

  const [mentorInput, setMentorInput] = useState('')

  const [mentorMessages, setMentorMessages] = useState([])

  const [mentorConversations, setMentorConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [conversationLoading, setConversationLoading] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState(null)

  const [mentorLoading, setMentorLoading] = useState(false)

  const [mentorError, setMentorError] = useState('')

// Day 7: Saved AI Mentor learning plans

const [savedMentorPlan, setSavedMentorPlan] = useState(null)

const [savedMentorPlanLoading, setSavedMentorPlanLoading] = useState(false)

const [savedMentorPlanError, setSavedMentorPlanError] = useState('')

  const score = result?.correct_answers ?? 0

  const totalQuestions = result?.total_questions ?? questions.length

  const overallPercentage = result?.overall_percentage ?? 0

  // Day 5: Roadmap progress analytics

const completedRoadmapTasks = roadmapTasks.filter(

  (task) => task.completed

).length

const totalRoadmapTasks = roadmapTasks.length

const pendingRoadmapTasks =

  totalRoadmapTasks - completedRoadmapTasks

const roadmapProgressPercentage = totalRoadmapTasks

  ? Math.round(

      (completedRoadmapTasks / totalRoadmapTasks) * 100

    )

  : 0

  const answeredCount = Object.keys(answers).length

  const currentQuestion = questions[current]

  // Verify the existing Flask session.

  async function checkSession() {

    console.log("checkSession started")

    try {

      const response = await fetch(`${API}/students/me`, {

        credentials: 'include',

      })

      if (!response.ok) {

        setStudent(null)

        return null

      }

      const data = await response.json()

      setStudent(data.student)

      return data.student

    } catch {

      setStudent(null)

      setAuthError(

        'Cannot connect to CareerMate. Check that Flask is running.'

      )

      return null

    } 

    finally {

  console.log("checkSession finished")

  console.log("Setting authChecked to true")  

  setAuthChecked(true)

}

  }

  useEffect(() => {

    checkSession()

  }, [])

  // Retrieve saved progress for the logged-in student.

  async function loadSavedProgress(studentToLoad = student) {

    if (!studentToLoad?.id) return null

    setProgressLoading(true)

    setProgressError('')

    try {

      const response = await fetch(

        `${API}/students/${studentToLoad.id}/progress`,

        {

          credentials: 'include',

        }

      )

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Unable to load saved progress.')

      }

      setSavedProgress(data)

      return data

    } catch (err) {

      setProgressError(

        err.message || 'Unable to load your saved progress.'

      )

      return null

    } finally {

      setProgressLoading(false)

    }

  }

  useEffect(() => {

    if (student?.id) {

      loadSavedProgress(student)

    }

  }, [student?.id])

  // Load roadmap data for dashboard analytics

useEffect(() => {

  if (!student?.id) return

  async function loadDashboardRoadmap() {

    try {

      const response = await fetch(`${API}/students/me/plan`, {

        credentials: 'include',

      })

      const data = await response.json()

      if (response.ok) {

        setLearningPlan(data.plan || null)

        setRoadmapTasks(data.tasks || [])

      }

    } catch (err) {

      console.error('Unable to load dashboard roadmap:', err)

    }

  }

  loadDashboardRoadmap()

}, [student?.id])

  // Register, log in, and validate account details.
  async function handleAuthentication(event) {
    event.preventDefault()
    setAuthLoading(true)
    setAuthError('')
    setAuthMessage('')

    const isRegister = authMode === 'register'
    const normalizedEmail = authEmail.trim().toLowerCase()
    if (isRegister) {
      if (!/^[^\s@]+@gmail\.com$/i.test(normalizedEmail)) {
        setAuthError('Please use a valid Gmail address ending exactly in @gmail.com.')
        setAuthLoading(false)
        return
      }
      if (!/^[6-9]\d{9}$/.test(authPhone.trim())) {
        setAuthError('Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.')
        setAuthLoading(false)
        return
      }
      if (authPassword.length < 8) {
        setAuthError('Password must contain at least 8 characters.')
        setAuthLoading(false)
        return
      }
    }

    const payload = {
      email: normalizedEmail,
      password: authPassword,
      ...(isRegister ? { name: authName.trim(), phone_number: authPhone.trim() } : {}),
    }

    try {
      const response = await fetch(`${API}/students/${isRegister ? 'register' : 'login'}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Authentication failed.')

      if (isRegister) {
        setAuthMode('login')
        setAuthPassword('')
        setAuthPhone('')
        setAuthMessage('Registration successful! Please log in.')
        return
      }
      if (!data.student) throw new Error('Login succeeded but student details are missing.')
      setStudent(data.student)
      setAuthPassword('')
      setAuthError('')
      setAuthMessage('')
      setActiveTab('Overview')
    } catch (err) {
      setAuthError(err.message || 'Unable to connect to CareerMate.')
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleForgotPassword(event) {
    event.preventDefault()
    setAuthLoading(true)
    setAuthError('')
    setAuthMessage('')
    const normalizedEmail = authEmail.trim().toLowerCase()
    if (!/^[^\s@]+@gmail\.com$/i.test(normalizedEmail)) {
      setAuthError('Enter the Gmail address associated with your CareerMate account.')
      setAuthLoading(false)
      return
    }
    try {
      const response = await fetch(`${API}/students/forgot-password`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: normalizedEmail }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Unable to request a password reset.')
      setAuthMessage(data.message || 'If the account exists, a password reset link has been sent.')
    } catch (err) {
      setAuthError(err.message || 'Unable to request a password reset.')
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault()
    setAuthLoading(true)
    setAuthError('')
    setAuthMessage('')
    if (!resetToken) {
      setAuthError('This reset link is missing its token. Request a new password reset link.')
      setAuthLoading(false)
      return
    }
    if (newPassword.length < 8) {
      setAuthError('Your new password must contain at least 8 characters.')
      setAuthLoading(false)
      return
    }
    if (newPassword !== confirmPassword) {
      setAuthError('The passwords do not match.')
      setAuthLoading(false)
      return
    }
    try {
      const response = await fetch(`${API}/students/reset-password`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resetToken, password: newPassword }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Unable to reset password.')
      setAuthMode('login')
      setAuthPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setResetToken('')
      window.history.replaceState({}, document.title, window.location.pathname)
      setAuthMessage('Password updated successfully. You can now log in with your new password.')
    } catch (err) {
      setAuthError(err.message || 'Unable to reset password.')
    } finally {
      setAuthLoading(false)
    }
  }

  // Log out and clear the local student state.
async function handleLogout() {
  try {
    const response = await fetch(`${API}/students/logout`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('The server could not end the session.');
    }

    // Clear authentication and student information
    setStudent(null);
    setSavedProgress(null);

    // Clear assessment data
    setResult(null);
    setQuestions([]);
    setAnswers({});
    setFinished(false);
    setStarted(false);

    // Clear career recommendations
    setCareerRecommendations([]);
    setCareerLoaded(false);
    setCareerError('');
    setSelectedCareer('');

    // Clear authentication form fields and messages
    setAuthMode('login');
    setAuthName('');
    setAuthEmail('');
    setAuthPassword('');
    setAuthError('');
    setAuthMessage('');

    // Return to the Overview tab
    setActiveTab('Overview');

    // Clear other student-specific data only if these states
    // exist in your App.jsx.
    if (typeof setMentorMessages === 'function') {
      setMentorMessages([]);
    setMentorConversations([]);
    setActiveConversationId(null);
    }

    if (typeof setSavedPlan === 'function') {
      setSavedPlan(null);
    }

  } catch (err) {
    setAuthError(err.message || 'Unable to log out.');
  }
}


  // Load assessment questions.
  async function openAssessment() {

    setActiveTab('Skill Assessment')

    setStarted(false)

    setFinished(false)

    setCurrent(0)

    setAnswers({})

    setResult(null)

    setError('')

    setLoading(true)

    try {

      const response = await fetch(`${API}/assessment/questions`, {

        credentials: 'include',

      })

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Unable to load questions.')

      }

      if (!Array.isArray(data.questions) || data.questions.length === 0) {
  throw new Error('No assessment questions are available.')
}

// Match the backend's question_text field to the frontend's question field.
const formattedQuestions = data.questions.map((item) => ({
  ...item,
  question: item.question ?? item.question_text ?? '',
  options: Array.isArray(item.options) ? item.options : [],
}))

setQuestions(formattedQuestions)
setStarted(true)

    } catch (err) {

      setError(err.message || 'Unable to load assessment questions.')

    } finally {

      setLoading(false)

    }

  }

  // Submit answers for the currently logged-in student.

  async function finishAssessment() {

    if (answeredCount !== questions.length) {

      setError('Please answer every question before submitting.')

      return

    }

    if (!student?.id) {

      setError('Please log in before submitting your assessment.')

      return

    }

    setLoading(true)

    setError('')

    try {

      const response = await fetch(`${API}/assessment/submit`, {

        method: 'POST',

        credentials: 'include',

        headers: {

          'Content-Type': 'application/json',

        },

        body: JSON.stringify({

          student_id: student.id,

          answers: questions.map((question, index) => ({

            question_id: question.id,

            answer: answers[index],

          })),

        }),

      })

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Assessment submission failed.')

      }

      setResult(data)

      setFinished(true)

      setCareerRecommendations([])

      setCareerLoaded(false)

      setCareerError('')

      await loadSavedProgress(student)

    } catch (err) {

      setError(err.message || 'Unable to submit assessment.')

    } finally {

      setLoading(false)

    }

  }

  function resetAssessment() {

    setAnswers({})

    setCurrent(0)

    setFinished(false)

    setResult(null)

    setError('')

    setStarted(true)

    setCareerRecommendations([])

    setCareerLoaded(false)

    setCareerError('')

  }

  // Calculate personalized career recommendations.

  async function loadCareerRecommendations() {

  setActiveTab('Career Recommendations')

  setCareerError('')

  setCareerLoading(true)

  try {

    // Prefer results from the current assessment.

    let skillResults = result?.skill_results || []

    // Otherwise, use saved skills from MySQL.

    if (!skillResults.length) {

      let progress = savedProgress

      if (!progress && student?.id) {

        const response = await fetch(

          `${API}/students/${student.id}/progress`,

          { credentials: 'include' }

        )

        const data = await response.json()

        if (!response.ok) {

          throw new Error(

            data.message || 'Unable to load saved skills.'

          )

        }

        progress = data

        setSavedProgress(data)

      }

      skillResults = progress?.current_skills || []

    }

    if (!skillResults.length) {

      throw new Error(

        'No saved skills found. Please complete the skill assessment first.'

      )

    }

    // Convert the saved skills into the API's expected format.

    const skills = {}

    skillResults.forEach((item) => {

      if (item.skill) {

        skills[item.skill] =

          Number(item.proficiency_level) || 0

      }

    })

    if (!Object.keys(skills).length) {

      throw new Error('No usable skill data was found.')

    }

    const response = await fetch(`${API}/careers/match`, {

      method: 'POST',

      credentials: 'include',

      headers: {

        'Content-Type': 'application/json',

      },

      body: JSON.stringify({ skills }),

    })

    const data = await response.json()

    if (!response.ok) {

      throw new Error(

        data.message || 'Unable to load career recommendations.'

      )

    }

    if (!Array.isArray(data.recommendations)) {

      throw new Error(

        'The career API returned an invalid response.'

      )

    }

    setCareerRecommendations(data.recommendations)

    setCareerLoaded(true)

  } catch (err) {

    setCareerRecommendations([])

    setCareerLoaded(false)

    setCareerError(

      err.message || 'Unable to load career recommendations.'

    )

  } finally {

    setCareerLoading(false)

  }

}

  // Load the logged-in student's saved learning roadmap.

  async function loadLearningPlan() {

    setActiveTab('Learning Roadmap')

    setRoadmapLoading(true)

    setRoadmapError('')

    try {

      const response = await fetch(`${API}/students/me/plan`, {

        credentials: 'include',

      })

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Unable to load roadmap.')

      }

      setLearningPlan(data.plan || null)

      setRoadmapTasks(data.tasks || [])

      if (data.plan?.career) {
        setSelectedCareer(data.plan.career)
      }

    } catch (err) {

      setRoadmapError(err.message || 'Unable to load roadmap.')

    } finally {

      setRoadmapLoading(false)

    }

  }

  // Select a recommended career and open the roadmap section.
  function chooseCareerForRoadmap(career) {
    const careerName = career.career || career.title
    if (!careerName) return

    setSelectedCareer(careerName)
    setLearningPlan(null)
    setRoadmapTasks([])
    setRoadmapError('')
    setActiveTab('Learning Roadmap')
  }

  // Generate or synchronize the roadmap, then load its saved tasks.

  async function generateLearningPlan() {

    setRoadmapLoading(true)

    setRoadmapError('')

    try {

      const response = await fetch(`${API}/plan/generate`, {

        method: 'POST',

        credentials: 'include',

        headers: {

          'Content-Type': 'application/json',

        },

        body: JSON.stringify({
          career: selectedCareer || learningPlan?.career || '',
        }),

      })

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Unable to generate roadmap.')

      }

      const planResponse = await fetch(`${API}/students/me/plan`, {

        credentials: 'include',

      })

      const planData = await planResponse.json()

      if (!planResponse.ok) {

        throw new Error(planData.message || 'Unable to load roadmap tasks.')

      }

      setLearningPlan(planData.plan || null)

      setRoadmapTasks(planData.tasks || [])

    } catch (err) {

      setRoadmapError(err.message || 'Unable to generate roadmap.')

    } finally {

      setRoadmapLoading(false)

    }

  }

  // Save a task's completion status in MySQL.

  async function toggleRoadmapTask(task) {

    const newCompleted = !task.completed

    setRoadmapError('')

    // Update the screen immediately.

    setRoadmapTasks((previous) =>

      previous.map((item) =>

        item.task_id === task.task_id

          ? { ...item, completed: newCompleted }

          : item

      )

    )

    try {

      const response = await fetch(

        `${API}/plan/tasks/${task.task_id}`,

        {

          method: 'PATCH',

          credentials: 'include',

          headers: {

            'Content-Type': 'application/json',

          },

          body: JSON.stringify({ completed: newCompleted }),

        }

      )

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.message || 'Unable to save task progress.')

      }

    } catch (err) {

      // Restore the previous status if saving fails.

      setRoadmapTasks((previous) =>

        previous.map((item) =>

          item.task_id === task.task_id

            ? { ...item, completed: task.completed }

            : item

        )

      )

      setRoadmapError(err.message || 'Unable to save task progress.')

    }

  }

  // Load the signed-in student's conversation list. The backend scopes every query by session student_id.
  async function loadMentorConversations(preferredId = null) {
    setConversationLoading(true)
    try {
      const response = await fetch(`${API}/mentor/conversations`, { credentials: 'include' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Unable to load chat history.')
      const items = data.conversations || []
      setMentorConversations(items)
      const targetId = preferredId || activeConversationId || items[0]?.id || null
      if (targetId) await openMentorConversation(targetId, false)
      else { setActiveConversationId(null); setMentorMessages([]) }
    } catch (err) {
      setMentorError(err.message || 'Unable to load chat history.')
    } finally {
      setConversationLoading(false)
    }
  }

  async function createMentorConversation() {
    setMentorError('')
    try {
      const response = await fetch(`${API}/mentor/conversations`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New chat' }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Unable to start a new chat.')
      const conversation = data.conversation
      setActiveConversationId(conversation.id)
      setMentorMessages([])
      setMentorInput('')
      setMentorConversations(previous => [
        conversation, ...previous.filter(item => item.id !== conversation.id),
      ])
    } catch (err) {
      setMentorError(err.message || 'Unable to start a new chat.')
    }
  }

  async function openMentorConversation(conversationId, showError = true) {
    try {
      const response = await fetch(`${API}/mentor/conversations/${conversationId}`, {
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Unable to open this conversation.')
      setActiveConversationId(data.conversation.id)
      setMentorMessages(data.messages || [])
      setMentorInput('')
      if (showError) setMentorError('')
    } catch (err) {
      if (showError) setMentorError(err.message || 'Unable to open this conversation.')
    }
  }


  async function deleteMentorConversation(conversation) {
    const confirmed = window.confirm(
      `Delete "${conversation.title}"? This will permanently remove this conversation and its messages.`
    )
    if (!confirmed || deletingConversationId !== null) return

    setMentorError('')
    setDeletingConversationId(conversation.id)
    try {
      const response = await fetch(
        `${API}/mentor/conversations/${conversation.id}`,
        { method: 'DELETE', credentials: 'include' }
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Unable to delete this conversation.')

      const remaining = mentorConversations.filter(item => item.id !== conversation.id)
      setMentorConversations(remaining)

      if (activeConversationId === conversation.id) {
        const nextConversation = remaining[0]
        if (nextConversation) {
          await openMentorConversation(nextConversation.id)
        } else {
          setActiveConversationId(null)
          setMentorMessages([])
          setMentorInput('')
        }
      }
    } catch (err) {
      setMentorError(err.message || 'Unable to delete this conversation.')
    } finally {
      setDeletingConversationId(null)
    }
  }

  // Load conversation history when the AI Mentor tab is opened.
  useEffect(() => {
    if (student?.id && activeTab === 'AI Mentor') loadMentorConversations()
    // Deliberately respond to tab/student changes only; selection is handled by click handlers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [student?.id, activeTab])

  // Send a question to the authenticated Flask retrieval-first AI Mentor endpoint.

  async function sendMentorMessage(event) {

    event.preventDefault()

    const message = mentorInput.trim()

    if (!message || mentorLoading) return

    setMentorMessages((previous) => [...previous, { role: 'user', text: message }])

    setMentorInput('')

    setMentorError('')

    setMentorLoading(true)

    try {
      let conversationId = activeConversationId
      if (!conversationId) {
        const createResponse = await fetch(`${API}/mentor/conversations`, {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: message.slice(0, 70) || 'New chat' }),
        })
        const createData = await createResponse.json()
        if (!createResponse.ok) throw new Error(createData.error || 'Unable to start a new chat.')
        conversationId = createData.conversation.id
        setActiveConversationId(conversationId)
        setMentorConversations(previous => [createData.conversation, ...previous])
      }

      const response = await fetch(`${API}/mentor/chat`, {

        method: 'POST',

        credentials: 'include',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ message, conversation_id: conversationId }),

      })

      const data = await response.json()

      if (!response.ok) {

        throw new Error(data.error || data.message || 'The AI Mentor could not respond.')

      }

      if (!data.reply) {

        throw new Error('The AI Mentor returned an empty response. Please try again.')

      }

      setMentorMessages((previous) => [...previous, { role: 'assistant', text: data.reply }])
      loadMentorConversations(conversationId)

    } catch (err) {

      setMentorError(err.message || 'Unable to connect to the AI Mentor. Please try again.')

    } finally {

      setMentorLoading(false)

    }

  }

// Day 7: Retrieve the latest saved AI Mentor plan from MySQL.

async function loadSavedMentorPlan() {

  setActiveTab('Saved Learning Plans')

  setSavedMentorPlanLoading(true)

  setSavedMentorPlanError('')

  try {

    const response = await fetch(

      `${API}/mentor/plans/latest`,

      {

        credentials: 'include',

      }

    )

    const data = await response.json()

    if (!response.ok) {

      throw new Error(

        data.message ||

        data.error ||

        'Unable to load your saved learning plan.'

      )

    }

    setSavedMentorPlan(data.plan || null)

    if (!data.plan) {

      setSavedMentorPlanError(

        'You have no saved AI Mentor plans yet. Ask the AI Mentor to create a learning plan first.'

      )

    }

  } catch (err) {

    setSavedMentorPlan(null)

    setSavedMentorPlanError(

      err.message || 'Unable to load your saved learning plan.'

    )

  } finally {

    setSavedMentorPlanLoading(false)

  }

}

  function chooseAnswer(option) {

    setAnswers((previous) => ({

      ...previous,

      [current]: option,

    }))

    setError('')

  }

  const menuItems = [

    { name: 'Overview', icon: '▦' },

    { name: 'Skill Assessment', icon: '✓' },

    { name: 'Career Recommendations', icon: '◎' },

    { name: 'Learning Roadmap', icon: '↗' },

    { name: 'AI Mentor', icon: '✦' },

     { name: 'Saved Learning Plans', icon: '▤' },

  ]

  // Wait for Flask to check the session.

  if (!authChecked) {

    return (

      <div className="app auth-screen">

        <section className="assessment-panel auth-card">

          <div className="assessment-intro">

            <div className="assessment-symbol">✦</div>

            <h1>CareerMate</h1>

            <p>Checking your account...</p>

          </div>

        </section>

      </div>

    )

  }

  // Show login, registration, or password-recovery screens when logged out.
  if (!student) {
    const isReset = authMode === 'reset' || Boolean(resetToken)
    const isLogin = authMode === 'login' && !isReset
    const isRegister = authMode === 'register' && !isReset
    const isForgot = authMode === 'forgot' && !isReset

    return (
      <div className="app auth-screen">
        <section className="assessment-panel auth-card">
          <div className="assessment-intro">
            <div className="assessment-symbol">✦</div>
            <p className="eyebrow">YOUR PERSONAL CAREER COMPANION</p>
            <h1>{isRegister ? 'Create your account' : isForgot ? 'Forgot password?' : isReset ? 'Create a new password' : 'Welcome back!'}</h1>
            <p>{isRegister ? 'Join CareerMate and start building your future.' : isForgot ? 'We will email a secure reset link if your account exists.' : isReset ? 'Choose a new password for your CareerMate account.' : 'Log in to continue your learning journey.'}</p>
          </div>

          {authError && <p className="assessment-error" role="alert">{authError}</p>}
          {authMessage && <p className="assessment-status" role="status">{authMessage}</p>}

          {isLogin && (
            <form className="auth-form" onSubmit={handleAuthentication}>
              <label className="auth-field">Gmail address
                <input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@gmail.com" autoComplete="email" required />
              </label>
              <label className="auth-field">Password
                <span className="password-input-wrap">
                  <input type={showLoginPassword ? 'text' : 'password'} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} placeholder="Enter your password" autoComplete="current-password" required />
                  <button className="password-toggle" type="button" onClick={() => setShowLoginPassword((visible) => !visible)} aria-label={showLoginPassword ? 'Hide password' : 'Show password'} aria-pressed={showLoginPassword} title={showLoginPassword ? 'Hide password' : 'Show password'}>{showLoginPassword ? '🙈' : '👁️'}</button>
                </span>
              </label>
              <div className="auth-inline-link"><button type="button" className="text-button" onClick={() => { setAuthMode('forgot'); setAuthError(''); setAuthMessage('') }}>Forgot password?</button></div>
              <button className="primary-button auth-submit" type="submit" disabled={authLoading}>{authLoading ? 'Please wait...' : 'Log In →'}</button>
            </form>
          )}

          {isRegister && (
            <form className="auth-form" onSubmit={handleAuthentication}>
              <label className="auth-field">Full name
                <input type="text" value={authName} onChange={(event) => setAuthName(event.target.value)} placeholder="Enter your name" autoComplete="name" maxLength={100} required />
              </label>
              <label className="auth-field">Gmail address
                <input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@gmail.com" autoComplete="email" pattern="[^\s@]+@gmail\.com" title="Use an email ending exactly in @gmail.com" required />
                <small className="auth-help">Only addresses ending exactly in @gmail.com are accepted.</small>
              </label>
              <label className="auth-field">Phone number
                <input type="tel" value={authPhone} onChange={(event) => setAuthPhone(event.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="10-digit mobile number" autoComplete="tel" inputMode="numeric" pattern="[6-9][0-9]{9}" title="Enter a 10-digit Indian mobile number starting with 6, 7, 8, or 9" maxLength={10} required />
              </label>
              <label className="auth-field">Password
                <span className="password-input-wrap">
                  <input type={showRegisterPassword ? 'text' : 'password'} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} required />
                  <button className="password-toggle" type="button" onClick={() => setShowRegisterPassword((visible) => !visible)} aria-label={showRegisterPassword ? 'Hide password' : 'Show password'} aria-pressed={showRegisterPassword} title={showRegisterPassword ? 'Hide password' : 'Show password'}>{showRegisterPassword ? '🙈' : '👁️'}</button>
                </span>
              </label>
              <button className="primary-button auth-submit" type="submit" disabled={authLoading}>{authLoading ? 'Please wait...' : 'Create Account →'}</button>
            </form>
          )}

          {isForgot && (
            <form className="auth-form" onSubmit={handleForgotPassword}>
              <label className="auth-field">Registered Gmail address
                <input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@gmail.com" autoComplete="email" required />
              </label>
              <button className="primary-button auth-submit" type="submit" disabled={authLoading}>{authLoading ? 'Sending...' : 'Send Reset Link →'}</button>
            </form>
          )}

          {isReset && (
            <form className="auth-form" onSubmit={handleResetPassword}>
              <label className="auth-field">New password
                <span className="password-input-wrap">
                  <input type={showNewPassword ? 'text' : 'password'} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} required />
                  <button className="password-toggle" type="button" onClick={() => setShowNewPassword((visible) => !visible)} aria-label={showNewPassword ? 'Hide new password' : 'Show new password'} aria-pressed={showNewPassword} title={showNewPassword ? 'Hide password' : 'Show password'}>{showNewPassword ? '🙈' : '👁️'}</button>
                </span>
              </label>
              <label className="auth-field">Confirm new password
                <span className="password-input-wrap">
                  <input type={showConfirmPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter password again" autoComplete="new-password" minLength={8} required />
                  <button className="password-toggle" type="button" onClick={() => setShowConfirmPassword((visible) => !visible)} aria-label={showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'} aria-pressed={showConfirmPassword} title={showConfirmPassword ? 'Hide password' : 'Show password'}>{showConfirmPassword ? '🙈' : '👁️'}</button>
                </span>
              </label>
              <button className="primary-button auth-submit" type="submit" disabled={authLoading}>{authLoading ? 'Updating...' : 'Reset Password →'}</button>
            </form>
          )}

          <p className="auth-switch">
            {isLogin ? "Don't have an account?" : isRegister ? 'Already have an account?' : 'Remembered your password?'}{' '}
            <button type="button" className="text-button" onClick={() => {
              const nextMode = isLogin ? 'register' : 'login'
              setAuthMode(nextMode); setAuthError(''); setAuthMessage('')
              if (isReset) { setResetToken(''); setNewPassword(''); setConfirmPassword(''); window.history.replaceState({}, document.title, window.location.pathname) }
            }}>{isLogin ? 'Register' : 'Log in'}</button>
          </p>
          {isForgot && <p className="auth-switch"><button type="button" className="text-button" onClick={() => { setAuthMode('login'); setAuthError(''); setAuthMessage('') }}>← Back to login</button></p>}
        </section>
      </div>
    )
  }

  // The authenticated dashboard continues in Part 3.

  // Authenticated CareerMate dashboard.

  return (

    <div className="app">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-logo">C</div>

          <div>

            <h1>CareerMate</h1>

            <p>LEARN. GROW. SUCCEED.</p>

          </div>

        </div>

        <p className="menu-label">WORKSPACE</p>

        <nav>

          {menuItems.map((item) => (

            <button

              key={item.name}

              className={`nav-item ${

                activeTab === item.name ? 'active' : ''

              }`}

              onClick={() => {

                if (item.name === 'Career Recommendations') {

  loadCareerRecommendations()

  return

}

if (item.name === 'Learning Roadmap') {

  loadLearningPlan()

  return

}

if (item.name === 'AI Mentor') {

  setActiveTab('AI Mentor')

  setError('')

  return

}

if (item.name === 'Saved Learning Plans') {

  loadSavedMentorPlan()

  return

}

                setActiveTab(item.name)

                setError('')

                if (item.name === 'Skill Assessment') {

                  setStarted(false)

                  setFinished(false)

                }

              }}

            >

              <span>{item.icon}</span>

              {item.name}

            </button>

          ))}

        </nav>

        <div className="sidebar-bottom">

          <div className="help-icon">?</div>

          <div>

            <strong>Need some help?</strong>

            <p>Keep learning, keep growing.</p>

          </div>

        </div>

      </aside>

      <main className="main-content">

        <header className="topbar">

          <div>

            <p className="breadcrumb">Workspace / {activeTab}</p>

            <h2>{activeTab}</h2>

          </div>

          <div className="profile">

            <div className="avatar">

              {(student.name || 'S').charAt(0).toUpperCase()}

            </div>

            <div>

              <strong>{student.name}</strong>

              <p>{student.email}</p>

            </div>

            <button

              className="secondary-button"

              onClick={handleLogout}

            >

              Log out

            </button>

          </div>

        </header>

        {/* SKILL ASSESSMENT */}

        {activeTab === 'Skill Assessment' ? (

          <section className="assessment-panel">

            {loading && (

              <p className="assessment-status">

                Loading questions or submitting your results...

              </p>

            )}

            {error && (

              <p className="assessment-error">{error}</p>

            )}

            {!started ? (

              <div className="assessment-intro">

                <div className="intro-icon">✓</div>

                <p className="section-eyebrow">DISCOVER YOUR STRENGTHS</p>

                <h2>Skill Assessment</h2>

                <p>

                  Answer questions to evaluate your current skills and

                  discover career paths that match your strengths.

                </p>

                <button

                  className="primary-button"

                  onClick={openAssessment}

                  disabled={loading}

                >

                  Start Assessment

                </button>

              </div>

            ) : finished ? (

              <div className="assessment-results">

                <div className="success-icon">✓</div>

                <p className="section-eyebrow">ASSESSMENT COMPLETED</p>

                <h2>Your Results</h2>

                <div className="score-circle">
  <strong>
    {Number(result?.overall_percentage ?? 0).toFixed(1)}%
  </strong>

  <span>Overall Score</span>

</div>
                <p>

                  Great job completing your assessment! Your results

                  help CareerMate understand your current skill level.

                </p>

                {result?.skill_results?.length > 0 && (
  <div className="skill-results">
    <h3>Your Skill Levels</h3>
    <p className="skill-results-description">
      Your performance for each skill is shown below.
    </p>

    <div className="skill-results-grid">
      {result.skill_results.map((item, index) => {
        const skillScore = Math.min(
          100,
          Math.max(0, Number(item.score_percentage) || 0)
        );

        const proficiency = Math.min(
          5,
          Math.max(1, Number(item.proficiency_level) || 1)
        );

        return (
          <div
            className="skill-result-item"
            key={`${item.skill}-${index}`}
          >
            <div className="skill-result-heading">
              <strong>{item.skill}</strong>
              <span>{skillScore.toFixed(1)}%</span>
            </div>

            <div
              className="progress-track"
              role="progressbar"
              aria-label={`${item.skill} assessment score`}
              aria-valuenow={skillScore}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="progress-fill"
                style={{ width: `${skillScore}%` }}
              />
            </div>

            <p className="skill-proficiency">
              Proficiency level: {proficiency} / 5
            </p>
          </div>
        );
      })}
    </div>
  </div>
)}

                <div className="result-actions">

                  <button

                    className="secondary-button"

                    onClick={resetAssessment}

                  >

                    Try Again

                  </button>

                  <button

                    className="primary-button"

                    onClick={() => setActiveTab('Overview')}

                  >

                    Return to Overview

                  </button>

                  <button

                    className="primary-button"

                    onClick={loadCareerRecommendations}

                  >

                    Explore Career Matches

                  </button>

                </div>

              </div>

            ) : currentQuestion ? (

              <div className="question-container">

                <p className="section-eyebrow">

                  SKILL ASSESSMENT

                </p>

                <div className="question-progress-heading">

                  <span>

                    Question {current + 1} of {questions.length}

                  </span>

                  <span>

                    {Math.round(

                      ((current + 1) / questions.length) * 100

                    )}

                    %

                  </span>

                </div>

                <div className="progress-track question-progress">

                  <div

                    className="progress-fill"

                    style={{

                      width: `${

                        ((current + 1) / questions.length) * 100

                      }%`,

                    }}

                  />

                </div>

                <h2 className="question-title">

                  {currentQuestion.question}

                </h2>

                <div className="options-list">

                  {(currentQuestion.options || []).map(

                    (option, index) => (

                      <button

                        key={index}

                        className={`option-button ${

                          answers[current] === option

                            ? 'selected'

                            : ''

                        }`}

                        onClick={() => chooseAnswer(option)}

                        disabled={loading}

                      >

                        <span className="option-letter">

                          {String.fromCharCode(65 + index)}

                        </span>

                        <span>{option}</span>

                      </button>

                    )

                  )}

                </div>

                {error && (

                  <p className="assessment-error">{error}</p>

                )}

                <div className="question-navigation">

                  <button

                    className="secondary-button"

                    onClick={() =>

                      setCurrent((previous) =>

                        Math.max(0, previous - 1)

                      )

                    }

                    disabled={current === 0 || loading}

                  >

                    Previous

                  </button>

                  {current < questions.length - 1 ? (

                    <button

                      className="primary-button"

                      onClick={() => {

                        if (answers[current] === undefined) {

                          setError('Please select an answer first.')

                          return

                        }

                        setCurrent((previous) => previous + 1)

                        setError('')

                      }}

                      disabled={loading}

                    >

                      Next Question

                    </button>

                  ) : (

                    <button

                      className="primary-button"

                      onClick={finishAssessment}

                      disabled={loading}

                    >

                      Submit Assessment

                    </button>

                  )}

                </div>

              </div>

            ) : (

              <div className="assessment-intro">

                <h2>No question selected</h2>

                <button

                  className="primary-button"

                  onClick={openAssessment}

                >

                  Load Assessment

                </button>

              </div>

            )}

          </section>

        ) : /* CAREER RECOMMENDATIONS */

        activeTab === 'Career Recommendations' ? (

          <section className="assessment-panel">

            <div className="assessment-intro">

              <div className="intro-icon">◎</div>

              <p className="section-eyebrow">

                YOUR CAREER JOURNEY

              </p>

              <h2>Career Recommendations</h2>

              <p>

                Discover career options based on your skills and

                assessment results.

              </p>

              {careerLoading && (

                <p className="assessment-status">

                  Finding your best career matches...

                </p>

              )}

              {careerError && (

                <p className="assessment-error">

                  {careerError}

                </p>

              )}

              {!result?.skill_results?.length &&

                !savedProgress?.current_skills?.length && (

                  <button

                    className="primary-button"

                    onClick={() => {

                      setActiveTab('Skill Assessment')

                      setStarted(false)

                      setFinished(false)

                    }}

                  >

                    Start Skill Assessment

                  </button>

                )}

              {careerLoaded && careerRecommendations.length === 0 && (

                <p>

                  No career recommendations are available yet.

                  Try updating your assessment.

                </p>

              )}

              <button

                className="secondary-button"

                onClick={loadCareerRecommendations}

                disabled={careerLoading}

              >

                Refresh Recommendations

              </button>

            </div>

            {careerLoaded && careerRecommendations.length > 0 && (

              <div className="career-grid">

                {careerRecommendations.map((career, index) => (

                  <article

                    className="career-card"

                    key={`${career.career || career.title}-${index}`}

                  >

                    <div className="career-card-top">

                      <div className="career-icon">✦</div>

                      <span className="match-badge">

                        {career.match_percentage ??

                          career.match_percent ??

                          0}

                        % Match

                      </span>

                    </div>

                    <h3>

                      {career.career || career.title}

                    </h3>

                    <p>

                      {career.description ||

                        'A career path that may match your skills.'}

                    </p>

                    {career.matched_skills?.length > 0 && (

                      <div className="career-skill-section">

                        <strong>Matched Skills</strong>

                        <div className="skill-tags">

                          {career.matched_skills.map((skill) => (

                            <span key={skill}>{skill}</span>

                          ))}

                        </div>

                      </div>

                    )}

                    {career.skill_gaps?.length > 0 && (

                      <div className="career-skill-section">

                        <strong>Skills to Improve</strong>

                        <div className="skill-tags skill-gap-tags">

{career.skill_gaps.map((skill, index) => (

  <span key={index}>

    {typeof skill === 'string' ? skill : skill.skill}

  </span>

))}

                        </div>

                      </div>

                    )}

                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => chooseCareerForRoadmap(career)}
                    >
                      Pursue This Career
                    </button>

                  </article>

                ))}

              </div>

            )}

          </section>

        ) : /* OVERVIEW */

        activeTab === 'Overview' ? (

          <div className="dashboard-content">

            <section className="welcome-banner">

              <div>

                <p className="section-eyebrow">

                  YOUR PERSONAL LEARNING COMPANION

                </p>

                <h1>

                  Welcome back, {student.name || 'Student'}!

                </h1>

                <p>

                  Keep building your skills and moving closer to

                  your dream career.

                </p>

                <button

                  className="primary-button"

                  onClick={() => {

                    setActiveTab('Skill Assessment')

                    setStarted(false)

                    setFinished(false)

                    setError('')

                  }}

                >

                  Continue Learning

                </button>

              </div>

              <div className="welcome-decoration">✦</div>

            </section>

            {progressLoading && (

              <p className="assessment-status">

                Loading your saved progress...

              </p>

            )}

            {progressError && (

              <p className="assessment-error">{progressError}</p>

            )}

            <div className="stats-grid">

              <div className="stat-card">

                <div className="stat-icon">✓</div>

                <p>Assessments Completed</p>

                <h2>

                  {savedProgress?.assessment_attempts?.length ?? 0}

                </h2>

                <span>Your saved attempts</span>

              </div>

              <div className="stat-card">

                <div className="stat-icon">✦</div>

                <p>Skills Tracked</p>

                <h2>

                  {savedProgress?.current_skills?.length ?? 0}

                </h2>

                <span>Skills in your profile</span>

              </div>

              <div className="stat-card">

                <div className="stat-icon">◎</div>

                <p>Career Matches</p>

                <h2>{careerRecommendations.length}</h2>

                <span>Recommended career paths</span>

              </div>

                       </div>

            {/* DAY 5: LEARNING ROADMAP ANALYTICS */}

            <section className="dashboard-card roadmap-analytics">

              <div className="card-heading">

                <div>

                  <p className="section-eyebrow">DAY 5 · YOUR LEARNING</p>

                  <h2>Roadmap Progress</h2>

                </div>

                <span className="card-heading-icon">↗</span>

              </div>

              {!learningPlan ? (

                <div className="empty-state">

                  <p>

                    Generate your learning roadmap to track your progress here.

                  </p>

                  <button

                    className="primary-button"

                    onClick={loadLearningPlan}

                  >

                    Open Learning Roadmap

                  </button>

                </div>

              ) : (

                <>

                  <div className="stats-grid roadmap-stats">

                    <div className="stat-card">

                      <div className="stat-icon">✓</div>

                      <p>Tasks Completed</p>

                      <h2>{completedRoadmapTasks}</h2>

                    </div>

                    <div className="stat-card">

                      <div className="stat-icon">◷</div>

                      <p>Tasks Pending</p>

                      <h2>{pendingRoadmapTasks}</h2>

                    </div>

                    <div className="stat-card">

                      <div className="stat-icon">◎</div>

                      <p>Overall Progress</p>

                      <h2>{roadmapProgressPercentage}%</h2>

                    </div>

                  </div>

                  <div className="progress-track roadmap-overall-progress">

                    <div

                      className="progress-fill"

                      style={{

                        width: `${roadmapProgressPercentage}%`,

                      }}

                    />

                  </div>

                  <p className="roadmap-progress-caption">

                    {completedRoadmapTasks} of {totalRoadmapTasks} learning

                    tasks completed

                  </p>

                  <button

                    className="secondary-button"

                    onClick={() => loadLearningPlan()}

                  >

                    View Learning Roadmap

                  </button>

                </>

              )}

            </section>

            <div className="dashboard-grid">

              <section className="dashboard-card">

                <div className="card-heading">

                  <div>

                    <p className="section-eyebrow">YOUR PROGRESS</p>

                    <h2>Current Skills</h2>

                  </div>

                  <span className="card-heading-icon">↗</span>

                </div>

                {(savedProgress?.current_skills?.length ?? 0) > 0 ? (

                  <div className="saved-skills-list">

                    {savedProgress.current_skills.map(

                      (skill, index) => (

                        <div

                          className="skill-result-item"

                          key={`${skill.skill}-${index}`}

                        >

                          <div className="skill-result-heading">

                            <strong>{skill.skill}</strong>

                            <span>

                              {Number(skill.proficiency_level) * 20}%

                            </span>

                          </div>

                          <div className="progress-track">
                            <div
                              className="progress-fill"
                              style={{
                                width: `${Math.min(
  100,
  Math.max(
    0,
    (Number(skill.proficiency_level) || 0) * 20
  )
)}%`,
                              }}
                            />
                          </div>
                        </div>
                      )

                    )}

                  </div>

                ) : (

                  <div className="empty-state">

                    <p>

                      Your saved skills will appear here after you

                      complete an assessment.

                    </p>

                    <button

                      className="primary-button"

                      onClick={() => {

                        setActiveTab('Skill Assessment')

                        setStarted(false)

                        setFinished(false)

                      }}

                    >

                      Take Assessment

                    </button>

                  </div>

                )}

              </section>

              <section className="dashboard-card">

                <div className="card-heading">

                  <div>

                    <p className="section-eyebrow">RECENT ACTIVITY</p>

                    <h2>Assessment History</h2>

                  </div>

                  <span className="card-heading-icon">◷</span>

                </div>

                {(savedProgress?.assessment_attempts?.length ?? 0) > 0 ? (

                  <div className="history-list">

                    {savedProgress.assessment_attempts.map(

                      (attempt, index) => (

                        <div

                          className="history-item"

                          key={attempt.id ?? index}

                        >

                          <div className="history-icon">✓</div>

                          <div className="history-details">

                            <strong>Skill Assessment</strong>

                            <p>

                              {attempt.completed_at

                                ? new Date(

                                    attempt.completed_at

                                  ).toLocaleDateString()

                                : 'Completed assessment'}

                            </p>

                          </div>

                          <span className="history-score">

                            {attempt.score_percentage ??

                              attempt.percentage ??

                              0}

                            %

                          </span>

                        </div>

                      )

                    )}

                  </div>

                ) : (

                  <div className="empty-state">

                    <p>

                      You have not completed an assessment yet.

                    </p>

                  </div>

                )}

              </section>

            </div>

            <section className="next-steps-card">

              <div>

                <p className="section-eyebrow">YOUR NEXT STEP</p>

                <h2>Turn your skills into a career plan</h2>

                <p>

                  Explore personalized career matches and identify

                  the skills you can develop next.

                </p>

              </div>

              <button

                className="primary-button"

                onClick={loadCareerRecommendations}

              >

                Explore Career Matches

              </button>

            </section>

          </div>

) : activeTab === 'Learning Roadmap' ? (

  /* LEARNING ROADMAP */

  <section className="assessment-panel">

  <div className="assessment-intro">

    <div className="intro-icon">↗</div>

    <p className="section-eyebrow">PLAN YOUR GROWTH</p>

    <h2>Learning Roadmap</h2>

    <p>

      {learningPlan

        ? `Your personalized learning plan for ${learningPlan.career}.`

        : selectedCareer
          ? `Selected career: ${selectedCareer}. Generate your personalized learning plan.`
          : 'Build a personalized learning plan for your chosen career.'}

    </p>
    {roadmapLoading && (
      <p className="assessment-status">
        Loading your learning roadmap...
      </p>
    )}
    {roadmapError && (
      <p className="assessment-error">{roadmapError}</p>
    )}
    {!learningPlan && !roadmapLoading && (
      <button
        className="primary-button"
        onClick={generateLearningPlan}
        disabled={!selectedCareer}
      >
        Generate Learning Roadmap
      </button>
    )}
    {learningPlan && (
      <button
        className="primary-button"
        onClick={generateLearningPlan}
        disabled={roadmapLoading}
      >
        {roadmapLoading ? 'Refreshing...' : 'Refresh Roadmap'}
      </button>
    )}
  </div>
  {learningPlan && !roadmapLoading && (
    <div className="roadmap-content">
      <div className="dashboard-card">
        <p className="section-eyebrow">YOUR PROGRESS</p>
        <h3>
          {roadmapTasks.filter((task) => task.completed).length}
          {' of '}
          {roadmapTasks.length} tasks completed
        </h3>
        <div className="progress-track">
          <div
            className="progress-fill"
            style={{
              width: `${
                roadmapTasks.length
                  ? (roadmapTasks.filter(
                      (task) => task.completed
                    ).length / roadmapTasks.length) * 100
                  : 0
              }%`,
            }}
          />
        </div>
      </div>
      {roadmapTasks.length === 0 ? (
        <p>No learning tasks found. Check your career skill mappings.</p>
      ) : (
        <div className="roadmap-task-list">
          {roadmapTasks.map((task) => (
            <article
              className="dashboard-card roadmap-task"
              key={task.task_id}
            >
              <label className="roadmap-task-check">
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => toggleRoadmapTask(task)}
                />
                <strong>{task.task_title}</strong>
              </label>
              <p>Skill: {task.skill}</p>
              <p>Estimated time: {task.estimated_minutes} minutes</p>
              {task.resource_url ? (
                <p>
                  Resource:{' '}
                  <a
                    href={task.resource_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {task.resource_title || 'Open learning resource'}
                  </a>
                </p>
              ) : (
                <p>No learning resource available yet.</p>
              )}
              <span>
                {task.completed ? 'Completed ✓' : 'Not completed'}
              </span>
            </article>
          ))}
        </div>
      )}
    </div>
  )}
</section>
 ) : activeTab === 'Saved Learning Plans' ? (
  /* DAY 7: SAVED AI MENTOR LEARNING PLANS */
  <section className="assessment-panel">
    <div className="assessment-intro">
      <div className="intro-icon">▤</div>
      <p className="section-eyebrow">
        YOUR PERSONALIZED STUDY PLAN
      </p>
      <h2>Saved Learning Plans</h2>
      <p>
        Access your AI-generated learning plan saved in CareerMate.
        Your plan remains available after refreshing the page.
      </p>
      <button
        className="primary-button"
        type="button"
        onClick={loadSavedMentorPlan}
        disabled={savedMentorPlanLoading}
      >
        {savedMentorPlanLoading
          ? 'Loading plan...'
          : 'Refresh Saved Plan'}
      </button>
    </div>
    {savedMentorPlanLoading && (
      <p className="assessment-status">
        Loading your saved learning plan...
      </p>
    )}
    {savedMentorPlanError && (
      <p className="assessment-error">
        {savedMentorPlanError}
      </p>
    )}
    {savedMentorPlan && !savedMentorPlanLoading && (
      <div className="dashboard-card">
        <div className="card-heading">
          <div>
            <p className="section-eyebrow">
              AI MENTOR · SAVED PLAN
            </p>
            <h2>Your Learning Plan</h2>
          </div>
          <span className="card-heading-icon">✦</span>
        </div>
        {savedMentorPlan.created_at && (
          <p>
            <strong>Created:</strong>{' '}
            {new Date(
              savedMentorPlan.created_at
            ).toLocaleString()}
          </p>
        )}
        {savedMentorPlan.prompt && (
          <p>
            <strong>Your request:</strong>{' '}
            {savedMentorPlan.prompt}
          </p>
        )}
        <div className="mentor-markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {savedMentorPlan.plan_text || 'No plan content was found.'}
          </ReactMarkdown>
        </div>
      </div>
    )}
  </section>
  ) : activeTab === 'AI Mentor' ? (
  <section className="assessment-panel mentor-panel mentor-workspace">
    <aside className="mentor-history-sidebar" aria-label="Chat history">
      <div className="mentor-history-header">
        <h3>Chat history</h3>
        <button type="button" className="mentor-new-chat-button" onClick={createMentorConversation}>+ New Chat</button>
      </div>
      {conversationLoading && <p className="mentor-history-status">Loading chats...</p>}
      {!conversationLoading && mentorConversations.length === 0 && (
        <p className="mentor-history-status">Your previous chats will appear here.</p>
      )}
      <div className="mentor-history-list">
        {mentorConversations.map((conversation) => (
          <div
            className="mentor-history-row"
            key={conversation.id}
            style={{ display: 'flex', alignItems: 'stretch', gap: '6px', marginBottom: '6px' }}
          >
            <button
              type="button"
              className={`mentor-history-item ${activeConversationId === conversation.id ? 'active' : ''}`}
              onClick={() => openMentorConversation(conversation.id)}
              title={conversation.title}
              style={{ flex: 1, minWidth: 0, textAlign: 'left' }}
            >
              <span className="mentor-history-title">{conversation.title}</span>
              <small>{conversation.message_count ? `${conversation.message_count} message${conversation.message_count === 1 ? '' : 's'}` : 'No messages yet'}</small>
            </button>
            <button
              type="button"
              onClick={() => deleteMentorConversation(conversation)}
              disabled={deletingConversationId !== null || mentorLoading}
              aria-label={`Delete chat: ${conversation.title}`}
              title="Delete chat"
              style={{
                flex: '0 0 38px',
                alignSelf: 'stretch',
                border: '1px solid #e5b8b8',
                borderRadius: '8px',
                background: '#fff7f7',
                color: '#b42318',
                cursor: deletingConversationId !== null || mentorLoading ? 'not-allowed' : 'pointer',
                opacity: deletingConversationId !== null || mentorLoading ? 0.55 : 1,
                fontSize: '16px',
              }}
            >
              {deletingConversationId === conversation.id ? '…' : '🗑'}
            </button>
          </div>
        ))}
      </div>
    </aside>
    <div className="mentor-main-column">
    <div className="assessment-intro">
      <div className="intro-icon">✦</div>
      <p className="section-eyebrow">YOUR PERSONAL AI GUIDE</p>
      <h2>AI Career Mentor</h2>
      <p>Ask about career choices, skills to learn, interview preparation, or your learning roadmap.</p>
    </div>
    <div className="mentor-chat" aria-live="polite">
      {mentorMessages.length === 0 ? (
        <div className="empty-state mentor-welcome">
          <p><strong>What would you like help with?</strong></p>
          <p>Try asking: “What skills should I learn to become a cybersecurity analyst?”</p>
        </div>
      ) : (
        <div className="mentor-message-list">
          {mentorMessages.map((message, index) => (
            <article
              className={`mentor-message ${message.role === 'user' ? 'mentor-user-message' : 'mentor-ai-message'}`}
              key={`${message.role}-${index}`}
            >
              <strong>{message.role === 'user' ? 'You' : 'CareerMate Mentor'}</strong>
              {message.role === 'user' ? (
                <p>{message.text}</p>
              ) : (
                <div className="mentor-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.text}
                  </ReactMarkdown>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      {mentorLoading && <p className="assessment-status">CareerMate Mentor is thinking...</p>}
      {mentorError && <p className="assessment-error">{mentorError}</p>}
    </div>
    <form className="mentor-chat-form" onSubmit={sendMentorMessage}>
      <label className="auth-field mentor-input-label">
        Your question
        <textarea
          value={mentorInput}
          onChange={(event) => setMentorInput(event.target.value)}
          placeholder="Ask a career or learning question..."
          rows={3}
          maxLength={4000}
          disabled={mentorLoading}
          required
        />
      </label>
      <button className="primary-button" type="submit" disabled={mentorLoading || !mentorInput.trim()}>
        {mentorLoading ? 'Getting advice...' : 'Send message →'}
      </button>
    </form>
    </div>
  </section>
) : null}
        <footer className="app-footer">
          <span>CareerMate · AI-Powered Personalized Learning</span>
          <span>Learn today. Lead tomorrow.</span>
        </footer>
      </main>
    </div>
  )
}
export default App