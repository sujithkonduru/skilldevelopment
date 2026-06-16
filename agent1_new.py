import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from dotenv import load_dotenv
import json
import re
import tempfile
import os
import time
import random
import base64
from datetime import datetime
import hashlib
import sqlite3
from io import BytesIO
from typing import List, Dict, Any

load_dotenv()

# Optional imports
try:
    import PyPDF2
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False

try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_OK = True
except ImportError:
    MIC_RECORDER_OK = False

# Page config
st.set_page_config(
    page_title="AI Technical Interview Assistant | Skill Development Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Modern Color Variables */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --primary-light: #818cf8;
        --secondary: #10b981;
        --accent: #f59e0b;
        --dark: #1e293b;
        --gray: #64748b;
        --light: #f8fafc;
        --white: #ffffff;
        --gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    }
    
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 0;
        border-radius: 0 0 30px 30px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
    }
    
    /* Card styling */
    .modern-card {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }
    
    /* Stats card */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 1.5rem;
        color: white;
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    /* Feature grid */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .feature-card {
        text-align: center;
        padding: 2rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    /* Skill tags */
    .skill-tag {
        display: inline-block;
        background: linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%);
        color: #4f46e5;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-size: 0.85rem;
        margin: 0.25rem;
        font-weight: 500;
    }
    
    /* Progress container */
    .progress-container {
        background: #e2e8f0;
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
    }
    
    .progress-fill {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    /* Footer */
    .footer {
        background: #1e293b;
        color: white;
        padding: 3rem 0;
        margin-top: 3rem;
        border-radius: 30px 30px 0 0;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.8rem;
        }
        .feature-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
""", unsafe_allow_html=True)

# Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Database setup
DB_PATH = "interview_assistant.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            current_role TEXT,
            experience_years INTEGER,
            education_level TEXT,
            preferred_language TEXT,
            career_goal TEXT,
            target_role TEXT,
            interests TEXT,
            learning_goals TEXT,
            short_term_goal TEXT,
            long_term_goal TEXT,
            why_tech TEXT,
            registration_date TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT UNIQUE,
            resume_data TEXT,
            resume_skills TEXT,
            questions TEXT,
            answers TEXT,
            evaluations TEXT,
            final_report TEXT,
            overall_score REAL,
            recommended INTEGER,
            interview_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_database()

# Password utilities
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# User database functions
def register_user(email: str, password: str, user_data: Dict) -> tuple:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return False, "User already exists"
        cursor.execute('''
            INSERT INTO users (
                email, password_hash, full_name, phone, current_role,
                experience_years, education_level, preferred_language,
                career_goal, target_role, interests, learning_goals,
                short_term_goal, long_term_goal, why_tech, registration_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email, hash_password(password),
            user_data.get('full_name', ''),
            user_data.get('phone', ''),
            user_data.get('current_role', ''),
            user_data.get('experience_years', 0),
            user_data.get('education_level', ''),
            user_data.get('preferred_language', 'English'),
            user_data.get('career_goal', ''),
            user_data.get('target_role', ''),
            json.dumps(user_data.get('interests', [])),
            user_data.get('learning_goals', ''),
            user_data.get('short_term_goal', ''),
            user_data.get('long_term_goal', ''),
            user_data.get('why_tech', ''),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, user_id
    except Exception as e:
        conn.close()
        return False, str(e)

def login_user(email: str, password: str) -> tuple:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, full_name, email FROM users WHERE email = ? AND is_active = 1", (email,))
    user = cursor.fetchone()
    if user and verify_password(password, user[1]):
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user[0]))
        conn.commit()
        user_data = {'user_id': user[0], 'full_name': user[2], 'email': user[3]}
        conn.close()
        return True, user_data
    conn.close()
    return False, None

def get_user_profile(user_id: int) -> Dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT full_name, email, phone, current_role, experience_years,
               education_level, preferred_language, career_goal, target_role,
               interests, learning_goals, short_term_goal, long_term_goal,
               why_tech, registration_date, last_login
        FROM users WHERE id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {
            'full_name': user[0], 'email': user[1], 'phone': user[2] or '',
            'current_role': user[3] or '', 'experience_years': user[4] or 0,
            'education_level': user[5] or '', 'preferred_language': user[6] or 'English',
            'career_goal': user[7] or '', 'target_role': user[8] or '',
            'interests': json.loads(user[9]) if user[9] else [],
            'learning_goals': user[10] or '', 'short_term_goal': user[11] or '',
            'long_term_goal': user[12] or '', 'why_tech': user[13] or '',
            'registration_date': user[14], 'last_login': user[15] or 'Never'
        }
    return {}

def save_interview_session(user_id: int, session_id: str, resume_data: Dict, resume_skills: List[str],
                           questions: List[Dict], answers: List[Dict], evaluations: List[Dict],
                           final_report: Dict, overall_score: float, recommended: bool):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_sessions (
            user_id, session_id, resume_data, resume_skills, questions,
            answers, evaluations, final_report, overall_score, recommended, interview_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, session_id, json.dumps(resume_data), json.dumps(resume_skills),
        json.dumps(questions), json.dumps(answers), json.dumps(evaluations),
        json.dumps(final_report), overall_score, 1 if recommended else 0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# Constants
CAREER_GOALS = [
    "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "DevOps Engineer", "Data Scientist", "Machine Learning Engineer",
    "Cloud Architect", "Mobile Developer", "Security Engineer",
    "Technical Lead", "Product Manager", "Software Architect", "Other"
]

INTERESTS_OPTIONS = [
    "Web Development", "Mobile Development", "Cloud Computing",
    "Artificial Intelligence", "Machine Learning", "Data Science",
    "Cybersecurity", "DevOps", "Blockchain", "IoT", "Game Development",
    "Open Source", "System Design", "Database Management", "UI/UX Design"
]

GRADE_MAP = [
    (90, "A+", "🏆 Outstanding"), (80, "A", "🎉 Excellent"),
    (70, "B", "👍 Good"), (60, "C", "📚 Average"),
    (50, "D", "⚠️ Below Average"), (0, "F", "❌ Needs Improvement"),
]

BEHAVIORAL_POOL = [
    {"topic": "Challenging Project", "question": "Tell me about a challenging project you worked on. What was your role and how did you overcome obstacles?"},
    {"topic": "Team Conflict", "question": "Describe a situation where you had to resolve a team conflict. What was the outcome?"},
    {"topic": "Missed Deadline", "question": "Explain a time when you missed a deadline and how you handled it."},
    {"topic": "Technical Problem Solving", "question": "Describe a difficult technical problem you faced and how you solved it."},
    {"topic": "Learning from Failure", "question": "Describe a project that didn't go as planned. What did you learn from it?"},
]

FRESHER_BEHAVIORAL_POOL = [
    {"topic": "Academic Projects", "question": "Tell me about a challenging academic project you worked on. What was your role and what did you learn?"},
    {"topic": "Learning New Technology", "question": "Describe a time when you had to learn a new technology quickly. How did you approach it?"},
    {"topic": "Team Collaboration", "question": "Tell me about your experience working in a team environment. How did you contribute?"},
    {"topic": "Problem Solving", "question": "Describe a difficult technical problem you solved during your studies or personal projects."},
    {"topic": "Motivation", "question": "Why did you choose to pursue a career in technology? What excites you about this field?"},
]

# Helper functions
def clean_json(text: str) -> str:
    text = re.sub(r"#{@.*?#{@}", "", text, flags=re.DOTALL)
    return text.replace("```json", "").replace("```", "").strip()

def groq_chat(prompt: str, max_tokens: int = 800, system: str = "") -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=msgs, temperature=0.3, max_tokens=max_tokens,
    )
    return r.choices[0].message.content

def safe_parse(text: str, fallback):
    try:
        return json.loads(clean_json(text))
    except Exception:
        return fallback

def speak(text: str, key: str) -> None:
    if GTTS_OK:
        try:
            buf = BytesIO()
            gTTS(text=text, lang="en", slow=False).write_to_fp(buf)
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode()
            components.html(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', height=0)
            return
        except Exception:
            pass
    safe = text.replace("\\","\\\\").replace("`","\\`").replace("$","\\$").replace('"','\\"')
    components.html(f"""<script>
(function(){{
  window.speechSynthesis.cancel();
  var u=new SpeechSynthesisUtterance(`{safe}`);
  u.rate=0.9;u.lang='en-US';
  function go(){{
    var v=window.speechSynthesis.getVoices();
    var sel=v.find(x=>x.name.includes('Google US English'))||v.find(x=>x.lang==='en-US')||v[0];
    if(sel)u.voice=sel;
    window.speechSynthesis.speak(u);
  }}
  if(window.speechSynthesis.getVoices().length>0)go();
  else window.speechSynthesis.onvoiceschanged=go;
}})();
</script>""", height=0)

def transcribe_audio(audio_bytes):
    if not audio_bytes:
        return ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    file=(tmp_path, audio_file, "audio/wav"),
                    model="whisper-large-v3-turbo",
                )
            return transcript.text.strip()
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        st.warning(f"Transcription error: {str(e)}")
        return ""

# Email extraction functions
def extract_email_from_resume(resume_text: str) -> str:
    """Extract email address from resume text"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, resume_text)
    if emails:
        return emails[0].lower().strip()
    return ""

def validate_resume_owner_by_email(resume_data: Dict, user_email: str) -> tuple:
    """Check if the resume belongs to the logged-in user using email"""
    resume_email = resume_data.get("candidate_email", "").lower().strip()
    user_email_lower = user_email.lower().strip()
    
    if not resume_email:
        return False, "No email address found in resume. Please ensure your resume contains your email address."
    
    if resume_email == user_email_lower:
        return True, "Email verified successfully!"
    
    return False, f"Email mismatch: Resume shows '{resume_email}' but logged in as '{user_email}'"

# Resume analysis functions
def extract_text_from_pdf(pdf_file) -> str:
    if not PDF_OK:
        st.error("PyPDF2 is not installed. Please install it using: pip install PyPDF2")
        return ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def extract_name_from_resume(resume_text: str) -> str:
    prompt = f"""
    Extract the candidate's full name from this resume. 
    Return ONLY the name as a string. If no name found, return "Candidate".
    Resume text: {resume_text[:1000]}
    """
    response = groq_chat(prompt, max_tokens=50)
    name = response.strip()
    if not name or len(name) < 2 or "name" in name.lower():
        return "Candidate"
    name = re.sub(r'["\']', '', name)
    name = name.split('\n')[0].strip()
    return name if len(name) > 1 else "Candidate"

def parse_resume(resume_text: str) -> Dict[str, Any]:
    candidate_name = extract_name_from_resume(resume_text)
    candidate_email = extract_email_from_resume(resume_text)
    
    prompt = f"""
    Parse the following resume and extract structured information.
    Return ONLY valid JSON with this exact structure:
    {{
        "candidate_name": "{candidate_name}",
        "candidate_email": "{candidate_email}",
        "professional_summary": "",
        "qualifications": {{
            "highest_degree": "",
            "degree_field": "",
            "institution": "",
            "graduation_year": "",
            "certifications": []
        }},
        "experience_level": {{
            "years_of_experience": 0,
            "seniority_level": "",
            "previous_roles": [],
            "team_leadership": false,
            "mentorship_experience": false,
            "is_fresher": false
        }},
        "skills": {{"technical": [], "non_technical": []}},
        "projects": [],
        "work_experience": [],
        "education": [],
        "certifications": []
    }}
    Resume text: {resume_text[:4000]}
    """
    response = groq_chat(prompt, max_tokens=1000)
    result = safe_parse(response, {
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "professional_summary": "",
        "qualifications": {"highest_degree": "Not specified", "degree_field": "", "institution": "", "graduation_year": "", "certifications": []},
        "experience_level": {"years_of_experience": 0, "seniority_level": "fresher", "previous_roles": [], "team_leadership": False, "mentorship_experience": False, "is_fresher": True},
        "skills": {"technical": [], "non_technical": []},
        "projects": [], "work_experience": [], "education": [], "certifications": []
    })
    if not result.get("candidate_name") or result.get("candidate_name") == "Unknown":
        result["candidate_name"] = candidate_name
    if not result.get("candidate_email"):
        result["candidate_email"] = candidate_email
    return result

def extract_technical_terms_from_resume(resume_data: Dict) -> List[str]:
    return list(set(resume_data.get("skills", {}).get("technical", [])))

def calculate_experience_level(resume_data: Dict) -> Dict:
    work_exp = resume_data.get("work_experience", [])
    exp_from_parse = resume_data.get("experience_level", {})
    if exp_from_parse.get("years_of_experience", 0) > 0 or exp_from_parse.get("is_fresher"):
        return exp_from_parse
    total_years = 0
    roles = []
    has_leadership = False
    has_mentorship = False
    for exp in work_exp:
        if isinstance(exp, dict):
            duration = exp.get("duration", "")
            if "year" in duration.lower():
                years = re.findall(r'(\d+)\s*year', duration.lower())
                if years:
                    total_years += int(years[0])
            title = exp.get("title", "").lower()
            roles.append(exp.get("title", ""))
            leadership_keywords = ["lead", "senior", "principal", "architect", "manager", "director", "head"]
            if any(keyword in title for keyword in leadership_keywords):
                has_leadership = True
            desc = exp.get("description", "").lower()
            mentorship_keywords = ["mentor", "train", "guide", "coach", "lead"]
            if any(keyword in desc for keyword in mentorship_keywords):
                has_mentorship = True
    is_fresher = total_years < 1 and len(work_exp) == 0
    if is_fresher:
        seniority = "fresher"
    elif total_years >= 12:
        seniority = "principal"
    elif total_years >= 10 or has_leadership:
        seniority = "lead"
    elif total_years >= 6:
        seniority = "senior"
    elif total_years >= 3:
        seniority = "mid"
    elif total_years >= 1:
        seniority = "entry"
    else:
        seniority = "fresher"
    return {
        "years_of_experience": total_years,
        "seniority_level": seniority,
        "previous_roles": roles[:5],
        "team_leadership": has_leadership,
        "mentorship_experience": has_mentorship,
        "is_fresher": is_fresher
    }

def get_experience_display_name(exp_level: Dict) -> str:
    seniority = exp_level.get("seniority_level", "fresher")
    is_fresher = exp_level.get("is_fresher", False)
    if is_fresher or seniority == "fresher":
        return "Fresher"
    elif seniority == "entry":
        return "Entry Level"
    elif seniority == "mid":
        return "Mid Level"
    elif seniority == "senior":
        return "Senior"
    elif seniority == "lead":
        return "Lead"
    elif seniority == "principal":
        return "Principal"
    return "Fresher"

# Question generation functions
def generate_behavioral_questions(resume_data: Dict, user_registration: Dict, count: int = 5) -> List[Dict]:
    exp_level = calculate_experience_level(resume_data)
    career_goal = user_registration.get("career_goal", "") if user_registration else ""
    interests = user_registration.get("interests", []) if user_registration else []
    personalized_questions = []
    if career_goal and career_goal != "Other":
        personalized_questions.append({
            "topic": "Career Goals",
            "question": f"You mentioned your career goal is to become a {career_goal}. What steps are you taking to achieve this goal?"
        })
    if interests:
        interest_str = ", ".join(interests[:3])
        personalized_questions.append({
            "topic": "Technical Interests",
            "question": f"You're interested in {interest_str}. Can you tell me about a recent project in one of these areas?"
        })
    if exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher":
        pool = FRESHER_BEHAVIORAL_POOL
    else:
        pool = BEHAVIORAL_POOL
    remaining_count = count - len(personalized_questions)
    if remaining_count > 0:
        selected = random.sample(pool, min(remaining_count, len(pool)))
    else:
        selected = []
    return personalized_questions + selected

def determine_skill_level(skill: str, resume_data: Dict, exp_level: Dict = None) -> str:
    if exp_level is None:
        exp_level = calculate_experience_level(resume_data)
    if exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher":
        return "beginner"
    return "intermediate"

def generate_skill_question(skill: str, level: str, user_registration: Dict = None) -> Dict:
    prompt = f"""
    Generate exactly ONE interview question for the technical skill "{skill}".
    Difficulty level: {level.upper()}
    Return ONLY valid JSON: {{"topic": "{skill}", "question": "your question here"}}
    """
    response = groq_chat(prompt, max_tokens=200)
    result = safe_parse(response, {"topic": skill, "question": f"Explain {skill} and describe a scenario where you would use it."})
    return result

def generate_all_questions(resume_data: Dict, resume_skills: List[str], detected_skills: List[str], user_registration: Dict) -> List[Dict]:
    all_skills = list(dict.fromkeys(resume_skills + detected_skills))
    exp_level = calculate_experience_level(resume_data)
    is_fresher = exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher"
    max_skills = 5 if is_fresher else 8
    behavioral_count = 4 if is_fresher else 5
    selected_skills = all_skills[:max_skills]
    behavioral_questions = generate_behavioral_questions(resume_data, user_registration, count=behavioral_count)
    skill_questions = []
    for skill in selected_skills:
        level = determine_skill_level(skill, resume_data, exp_level)
        skill_q = generate_skill_question(skill, level, user_registration)
        skill_questions.append(skill_q)
    all_questions = behavioral_questions + skill_questions
    random.shuffle(all_questions)
    return all_questions

# Answer evaluation
def evaluate_answer(topic: str, question: str, answer: str, user_registration: Dict = None) -> Dict:
    if answer.strip() in ("", "[Skipped]"):
        return {
            "technical_accuracy": 0, "communication_skills": 0, "confidence": 0,
            "completeness": 0, "relevance": 0, "score": 0, 
            "feedback": "No answer provided for this question. Please provide an answer to get proper evaluation.",
            "strengths": [], 
            "improvements": ["Provide a complete answer", "Be more specific in your response", "Try to structure your answer clearly"]
        }
    
    prompt = f"""
    You are a Senior Technical Interviewer. Evaluate this candidate's answer in detail.
    
    Topic: {topic}
    Question: {question}
    Answer: {answer}
    
    Please provide:
    1. Technical accuracy (1-10): How technically correct is the answer?
    2. Communication skills (1-10): How clear and well-structured is the answer?
    3. Confidence (1-10): How confidently does the candidate present their answer?
    4. Completeness (1-10): Does the answer fully address the question?
    5. Relevance (1-10): Is the answer relevant to the question asked?
    
    Also provide:
    - A detailed feedback summary (2-3 sentences)
    - 2-3 specific strengths demonstrated
    - 2-3 specific areas for improvement
    
    Return ONLY valid JSON with this exact structure:
    {{
        "technical_accuracy": 8,
        "communication_skills": 7,
        "confidence": 7,
        "completeness": 8,
        "relevance": 9,
        "score": 8,
        "feedback": "Your answer demonstrates good understanding of the concept. You explained the key points clearly and provided relevant examples.",
        "strengths": ["Clear explanation of core concepts", "Good use of examples", "Structured approach"],
        "improvements": ["Could add more depth to technical details", "Mention specific frameworks/tools", "Provide code examples if relevant"]
    }}
    """
    
    response = groq_chat(prompt, max_tokens=800)
    result = safe_parse(response, {
        "technical_accuracy": 5, "communication_skills": 5, "confidence": 5,
        "completeness": 5, "relevance": 5, "score": 5, 
        "feedback": "Your answer has been evaluated. Consider adding more specific details and examples to improve.",
        "strengths": ["Good attempt at answering"], 
        "improvements": ["Add more technical depth", "Structure your answer better", "Provide concrete examples"]
    })
    
    avg_score = (result.get("technical_accuracy", 5) + result.get("communication_skills", 5) +
                 result.get("confidence", 5) + result.get("completeness", 5) + result.get("relevance", 5)) / 5
    result["score"] = round(avg_score, 1)
    
    return result

# Final report
def generate_final_report(candidate_name: str, resume_data: Dict, resume_skills: List[str],
                          detected_speech_skills: List[str], answers: List[Dict],
                          evaluations: List[Dict], user_registration: Dict) -> Dict:
    technical_scores = [e.get("technical_accuracy", 5) for e in evaluations if e.get("technical_accuracy", 0) > 0]
    communication_scores = [e.get("communication_skills", 5) for e in evaluations if e.get("communication_skills", 0) > 0]
    confidence_scores = [e.get("confidence", 5) for e in evaluations if e.get("confidence", 0) > 0]
    
    technical_score = sum(technical_scores) / len(technical_scores) if technical_scores else 0
    communication_score = sum(communication_scores) / len(communication_scores) if communication_scores else 0
    confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    overall_score = (technical_score + communication_score + confidence_score) / 3 if (technical_score + communication_score + confidence_score) > 0 else 0
    
    all_strengths = [s for e in evaluations for s in e.get("strengths", [])]
    all_improvements = [i for e in evaluations for i in e.get("improvements", [])]
    unique_strengths = list(dict.fromkeys(all_strengths))[:5]
    unique_improvements = list(dict.fromkeys(all_improvements))[:5]
    
    exp_level = calculate_experience_level(resume_data)
    is_fresher = exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher"
    exp_display = get_experience_display_name(exp_level)
    expected_score = 4.5 if is_fresher else 6.5
    recommended = overall_score >= expected_score
    percentile = min(100, (overall_score / 10) * 100) if overall_score > 0 else 0
    
    return {
        "candidate_name": candidate_name,
        "technical_score": round(technical_score, 1),
        "communication_score": round(communication_score, 1),
        "confidence_score": round(confidence_score, 1),
        "overall_score": round(overall_score, 1),
        "percentile_rank": round(percentile, 1),
        "strengths": unique_strengths,
        "improvement_areas": unique_improvements,
        "recommended_for_next_round": recommended,
        "experience_display": exp_display,
        "performance_vs_expectation": round(overall_score - expected_score, 1)
    }

def get_grade(pct: float):
    for threshold, grade, label in GRADE_MAP:
        if pct >= threshold:
            return grade, label
    return "F", "❌ Needs Improvement"

# Session state management
def reset_interview_state():
    st.session_state.resume_data = None
    st.session_state.resume_skills = []
    st.session_state.detected_speech_skills = []
    st.session_state.all_questions = []
    st.session_state.current_q = 0
    st.session_state.answers = []
    st.session_state.evaluations = []
    st.session_state.final_report = None
    st.session_state.greeted = False
    st.session_state.intro_recorded = False
    st.session_state.intro_text = ""
    st.session_state.resume_analyzed = False

DEFAULTS = {
    "logged_in": False, "user_id": None, "user_email": None, "user_name": None,
    "stage": "login", "user_registration": None, "resume_data": None,
    "resume_skills": [], "detected_speech_skills": [], "all_questions": [],
    "current_q": 0, "answers": [], "evaluations": [], "final_report": None,
    "greeted": False, "intro_recorded": False, "intro_text": "", "resume_analyzed": False
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# UI Components
def show_navbar():
    if st.session_state.logged_in:
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            st.markdown("### 🎯 SkillForge")
        with col2:
            if st.button("🏠 Home", key="nav_home", use_container_width=True):
                st.session_state.stage = "welcome"
                st.rerun()
        with col3:
            if st.button("👤 Profile", key="nav_profile", use_container_width=True):
                st.session_state.stage = "profile"
                st.rerun()
        with col4:
            if st.button("📊 Reports", key="nav_reports", use_container_width=True):
                st.session_state.stage = "welcome"
        with col5:
            if st.button("🚪 Logout", key="nav_logout", use_container_width=True):
                reset_interview_state()
                st.session_state.logged_in = False
                st.session_state.stage = "login"
                st.rerun()
        st.markdown("---")

def show_login():
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Welcome to SkillForge</h1>
        <p>AI-Powered Technical Interview Preparation Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        <div class="modern-card">
            <h2>✨ Why Choose SkillForge?</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon">🤖</div>
                    <h3>AI-Powered</h3>
                    <p>Smart question generation based on your resume</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🎤</div>
                    <h3>Voice-Based</h3>
                    <p>Real interview simulation with voice interaction</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <h3>Detailed Reports</h3>
                    <p>Comprehensive feedback and improvement areas</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🎯</div>
                    <h3>Personalized</h3>
                    <p>Tailored questions based on your career goals</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                if submitted:
                    if email and password:
                        success, user_data = login_user(email, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_data['user_id']
                            st.session_state.user_email = user_data['email']
                            st.session_state.user_name = user_data['full_name']
                            reset_interview_state()
                            st.session_state.stage = "welcome"
                            st.success(f"Welcome back, {user_data['full_name']}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
        
        with tab2:
            with st.form("register_form"):
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email Address *")
                phone = st.text_input("Phone Number")
                password = st.text_input("Password *", type="password")
                confirm_password = st.text_input("Confirm Password *", type="password")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    current_role = st.text_input("Current Role")
                    experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, value=0)
                with col_b:
                    education_level = st.selectbox("Education Level", ["High School", "Bachelor's Degree", "Master's Degree", "PhD", "Other"])
                    career_goal = st.selectbox("Career Goal", CAREER_GOALS)
                
                interests = st.multiselect("Technical Interests", INTERESTS_OPTIONS)
                learning_goals = st.text_area("What are you currently learning?", height=80)
                
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                if submitted:
                    if full_name and email and password:
                        if password == confirm_password:
                            user_data = {
                                'full_name': full_name, 'phone': phone, 'current_role': current_role,
                                'experience_years': experience_years, 'education_level': education_level,
                                'preferred_language': 'English', 'career_goal': career_goal,
                                'target_role': '', 'interests': interests, 'learning_goals': learning_goals,
                                'short_term_goal': '', 'long_term_goal': '', 'why_tech': ''
                            }
                            success, result = register_user(email, password, user_data)
                            if success:
                                st.success("Registration successful! Please login.")
                                st.balloons()
                            else:
                                st.error(f"Registration failed: {result}")
                        else:
                            st.error("Passwords do not match")
        st.markdown('</div>', unsafe_allow_html=True)

def show_welcome():
    show_navbar()
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">Welcome back, {st.session_state.user_name}! 👋</h1>
        <p style="color: rgba(255,255,255,0.9); font-size: 1.2rem;">Ready to ace your next technical interview?</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="modern-card">
            <h2>📋 Your Interview Journey</h2>
            <div style="margin: 1.5rem 0;">
                <div style="display: flex; align-items: center; margin: 1rem 0;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; margin-right: 1rem;">1</div>
                    <div><strong>Complete Your Profile</strong><br>Tell us about your career goals and interests</div>
                </div>
                <div style="display: flex; align-items: center; margin: 1rem 0;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; margin-right: 1rem;">2</div>
                    <div><strong>Upload Your Resume</strong><br>AI analyzes your skills and experience</div>
                </div>
                <div style="display: flex; align-items: center; margin: 1rem 0;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; margin-right: 1rem;">3</div>
                    <div><strong>Voice Introduction</strong><br>Record your self-introduction</div>
                </div>
                <div style="display: flex; align-items: center; margin: 1rem 0;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; margin-right: 1rem;">4</div>
                    <div><strong>Live Interview</strong><br>Answer personalized questions</div>
                </div>
                <div style="display: flex; align-items: center; margin: 1rem 0;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; margin-right: 1rem;">5</div>
                    <div><strong>Get Detailed Report</strong><br>Receive comprehensive feedback and scores</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="modern-card" style="text-align: center;">
            <h2>🚀 Quick Stats</h2>
            <div class="stat-card" style="margin: 1rem 0;">
                <div style="font-size: 2rem;">🎯</div>
                <div class="stat-number">500+</div>
                <div>Interview Questions</div>
            </div>
            <div class="stat-card" style="margin: 1rem 0; background: linear-gradient(135deg, #10b981, #059669);">
                <div style="font-size: 2rem;">👥</div>
                <div class="stat-number">1000+</div>
                <div>Students Trained</div>
            </div>
            <div class="stat-card" style="margin: 1rem 0; background: linear-gradient(135deg, #f59e0b, #d97706);">
                <div style="font-size: 2rem;">🏆</div>
                <div class="stat-number">85%</div>
                <div>Success Rate</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Your Interview Journey", use_container_width=True, type="primary"):
            user_profile = get_user_profile(st.session_state.user_id)
            if user_profile and user_profile.get('career_goal'):
                st.session_state.user_registration = user_profile
                st.session_state.stage = "intro"
            else:
                st.session_state.stage = "registration"
            st.rerun()

def show_registration_form():
    show_navbar()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">📝 Complete Your Profile</h1>
        <p style="color: rgba(255,255,255,0.9);">Tell us about yourself to personalize your interview experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_profile = get_user_profile(st.session_state.user_id) or {}
    
    st.info(f"**Current User:** {st.session_state.user_name} ({st.session_state.user_email})")
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("👤 Full Name", value=st.session_state.user_name)
            current_role = st.text_input("💼 Current Role", value=user_profile.get('current_role', ''))
            experience_years = st.number_input("📊 Years of Experience", min_value=0, max_value=50, value=user_profile.get('experience_years', 0), step=1)
            education_level = st.selectbox("🎓 Highest Education Level", 
                                          ["High School", "Bachelor's Degree", "Master's Degree", "PhD", "Other"],
                                          index=1 if user_profile.get('education_level') == "Bachelor's Degree" else 0)
        with col2:
            career_goal = st.selectbox("🎯 Career Goal", CAREER_GOALS, 
                                      index=0 if not user_profile.get('career_goal') else (CAREER_GOALS.index(user_profile['career_goal']) if user_profile['career_goal'] in CAREER_GOALS else 0))
            if career_goal == "Other":
                career_goal = st.text_input("Specify your career goal", value=user_profile.get('career_goal', '') if user_profile.get('career_goal') not in CAREER_GOALS else '')
            target_role = st.text_input("🏆 Target Role (next 1-2 years)", value=user_profile.get('target_role', ''))
            preferred_language = st.selectbox("🌐 Preferred Language", ["English", "Spanish", "French", "German"], index=0)
        
        interests = st.multiselect("💡 Technical Interests", INTERESTS_OPTIONS, default=user_profile.get('interests', []))
        learning_goals = st.text_area("📚 What technologies/skills are you currently learning?", value=user_profile.get('learning_goals', ''), height=80)
        
        col1, col2 = st.columns(2)
        with col1:
            short_term_goal = st.text_area("🎯 Short-term goal (next 6 months)", value=user_profile.get('short_term_goal', ''), height=80)
        with col2:
            long_term_goal = st.text_area("🌟 Long-term goal (next 3-5 years)", value=user_profile.get('long_term_goal', ''), height=80)
        
        why_tech = st.text_area("💭 Why did you choose a career in technology?", value=user_profile.get('why_tech', ''), height=80)
        
        submitted = st.form_submit_button("✅ Save Profile & Continue", type="primary", use_container_width=True)
        if submitted:
            if full_name != st.session_state.user_name:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, st.session_state.user_id))
                conn.commit()
                conn.close()
                st.session_state.user_name = full_name
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''UPDATE users SET current_role = ?, experience_years = ?, education_level = ?, preferred_language = ?, career_goal = ?, target_role = ?, interests = ?, learning_goals = ?, short_term_goal = ?, long_term_goal = ?, why_tech = ? WHERE id = ?''',
                           (current_role, experience_years, education_level, preferred_language, career_goal, target_role, json.dumps(interests), learning_goals, short_term_goal, long_term_goal, why_tech, st.session_state.user_id))
            conn.commit()
            conn.close()
            st.session_state.user_registration = {
                'full_name': st.session_state.user_name, 'email': st.session_state.user_email,
                'current_role': current_role, 'experience_years': experience_years,
                'education_level': education_level, 'preferred_language': preferred_language,
                'career_goal': career_goal, 'target_role': target_role, 'interests': interests,
                'learning_goals': learning_goals, 'short_term_goal': short_term_goal,
                'long_term_goal': long_term_goal, 'why_tech': why_tech
            }
            st.success("Profile saved successfully!")
            time.sleep(1)
            st.session_state.stage = "intro"
            st.rerun()

def show_resume_upload():
    show_navbar()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">📄 Upload Your Resume</h1>
        <p style="color: rgba(255,255,255,0.9);">Let our AI analyze your skills and experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background: #e0e7ff; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 4px solid #6366f1;">
        <strong>👤 Logged in as:</strong> {st.session_state.user_name}<br>
        <strong>📧 Email:</strong> {st.session_state.user_email}
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("ℹ️ About Email Validation"):
        st.markdown("""
        The system will validate your resume using the **email address** found in it.
        
        **Requirements:**
        - Your resume MUST contain your email address
        - The email in your resume must match the email you registered with
        - This ensures that you are uploading YOUR own resume
        
        **Tip:** Make sure your email is clearly visible in the resume header or contact section.
        """)
    
    if st.session_state.get('resume_analyzed', False) and st.session_state.resume_data:
        resume_email = st.session_state.resume_data.get("candidate_email", "Unknown")
        st.success(f"✅ Your resume (Email: {resume_email}) has been analyzed and verified!")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Continue with this Resume", type="primary", use_container_width=True):
                st.session_state.stage = "resume"
                st.rerun()
        with col2:
            if st.button("🔄 Upload Different Resume", use_container_width=True):
                st.session_state.resume_data = None
                st.session_state.resume_skills = []
                st.session_state.resume_analyzed = False
                st.rerun()
        return
    
    st.markdown("---")
    
    pdf = st.file_uploader(
        "Choose your resume file (PDF only)", 
        type=["pdf"], 
        key="resume_uploader_main",
        help="Upload YOUR resume in PDF format for AI analysis"
    )
    
    if pdf is not None:
        st.success(f"✅ File '{pdf.name}' uploaded successfully! Size: {pdf.size/1024:.1f} KB")
        
        if not st.session_state.get('resume_analyzed', False):
            if st.button("🚀 Analyze Resume", type="primary", use_container_width=True):
                with st.spinner("📖 Reading PDF file..."):
                    resume_text = extract_text_from_pdf(pdf)
                
                if not resume_text or not resume_text.strip():
                    st.error("❌ Could not read the PDF file. Please make sure it's a valid PDF document.")
                    st.stop()
                
                with st.spinner("🧠 AI is analyzing your resume..."):
                    progress_bar = st.progress(0)
                    progress_bar.progress(30)
                    
                    resume_data = parse_resume(resume_text)
                    progress_bar.progress(60)
                    
                    if not resume_data.get("candidate_email"):
                        resume_data["candidate_email"] = extract_email_from_resume(resume_text)
                    
                    resume_skills = extract_technical_terms_from_resume(resume_data)
                    progress_bar.progress(80)
                    
                    exp_level = calculate_experience_level(resume_data)
                    progress_bar.progress(100)
                
                resume_email = resume_data.get("candidate_email", "")
                is_valid, match_message = validate_resume_owner_by_email(resume_data, st.session_state.user_email)
                
                if not is_valid:
                    st.error(f"❌ {match_message}")
                    st.markdown("""
                    **Please upload a resume that belongs to you.**
                    
                    **Troubleshooting:**
                    1. Make sure your resume contains your email address in the header
                    2. The email in your resume must match your registered email
                    3. Check for typos in your resume email
                    4. Try re-uploading after adding your email
                    """)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Registered Email:** `{st.session_state.user_email}`")
                    with col2:
                        st.markdown(f"**Resume Email:** `{resume_email if resume_email else 'Not found'}`")
                    
                    if not resume_email:
                        st.warning("⚠️ No email address was found in your resume. Please add your email to your resume and try again.")
                    
                    return
                else:
                    st.success(f"✅ {match_message}")
                    st.info(f"Resume email '{resume_email}' matches your registered email '{st.session_state.user_email}'")
                
                st.session_state.resume_data = resume_data
                st.session_state.resume_skills = resume_skills
                st.session_state.resume_analyzed = True
                
                candidate_name = resume_data.get("candidate_name", "Candidate")
                candidate_email = resume_data.get("candidate_email", "Not found")
                is_fresher = exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher"
                exp_display = get_experience_display_name(exp_level)
                
                st.balloons()
                
                st.markdown("---")
                st.markdown("### 📊 Resume Analysis Results")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="modern-card">
                        <h4>👤 Candidate Information</h4>
                        <p><strong>Name on Resume:</strong> {candidate_name}</p>
                        <p><strong>Email on Resume:</strong> {candidate_email}</p>
                        <p><strong>Registered Email:</strong> {st.session_state.user_email}</p>
                        <p><strong>Verification Status:</strong> ✅ Email Verified</p>
                        <p><strong>Experience Level:</strong> {exp_display}</p>
                        <p><strong>Years of Experience:</strong> {exp_level.get('years_of_experience', 0)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    quals = resume_data.get("qualifications", {})
                    st.markdown(f"""
                    <div class="modern-card">
                        <h4>🎓 Qualifications</h4>
                        <p><strong>Highest Degree:</strong> {quals.get('highest_degree', 'Not specified')}</p>
                        <p><strong>Field:</strong> {quals.get('degree_field', 'Not specified')}</p>
                        <p><strong>Institution:</strong> {quals.get('institution', 'Not specified')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 💻 Technical Skills Detected")
                
                if resume_skills:
                    skill_html = ""
                    for skill in resume_skills[:20]:
                        skill_html += f'<span class="skill-tag">{skill}</span>'
                    st.markdown(f'<div style="margin: 1rem 0;">{skill_html}</div>', unsafe_allow_html=True)
                    
                    if len(resume_skills) > 20:
                        st.caption(f"... and {len(resume_skills) - 20} more skills detected")
                else:
                    st.warning("No technical skills detected in the resume.")
                
                st.markdown("---")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Confirm & Continue", type="primary", use_container_width=True):
                        st.session_state.stage = "resume"
                        st.rerun()
                with col2:
                    if st.button("🔄 Upload Different Resume", use_container_width=True):
                        st.session_state.resume_data = None
                        st.session_state.resume_skills = []
                        st.session_state.resume_analyzed = False
                        st.rerun()

def show_voice_introduction():
    show_navbar()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">🎤 Voice Introduction</h1>
        <p style="color: rgba(255,255,255,0.9);">Record a 30-60 second introduction about yourself</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.resume_data is None:
        st.error("No resume data found. Please go back and upload your resume first.")
        if st.button("← Back to Resume Upload"):
            st.session_state.stage = "intro"
            st.rerun()
        return
    
    exp_level = calculate_experience_level(st.session_state.resume_data)
    candidate_name = st.session_state.resume_data.get("candidate_name", "Candidate")
    is_fresher = exp_level.get("is_fresher") or exp_level.get("seniority_level") == "fresher"
    exp_display = get_experience_display_name(exp_level)
    
    st.info(f"""
    **Candidate Profile:**
    - 👤 **Name:** {candidate_name}
    - 📊 **Experience Level:** {exp_display}
    - 💻 **Key Skills:** {', '.join(st.session_state.resume_skills[:5]) if st.session_state.resume_skills else 'Detected from resume'}
    """)
    
    if not st.session_state.get("greeted", False):
        if is_fresher:
            speak("Please introduce yourself. Tell us about your educational background, any projects you've worked on, and the technologies you're familiar with.", key="intro_greet")
        else:
            speak("Please introduce yourself. Tell me about your background and the technologies you work with.", key="intro_greet")
        st.session_state.greeted = True
    
    st.markdown("---")
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("#### 🎙️ Recording Instructions")
    st.markdown("""
    1. Click **Start Recording** below
    2. Speak clearly for 30-60 seconds
    3. Click **Stop Recording** when done
    4. Review your transcription
    """)
    
    if not MIC_RECORDER_OK:
        st.error("❌ Voice recording feature not available. Please install streamlit-mic-recorder.")
        st.stop()
    
    audio_data = mic_recorder(
        start_prompt="🎙 Start Recording",
        stop_prompt="⏹ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
        key="intro_recorder",
    )
    
    if audio_data and not st.session_state.get('intro_recorded', False):
        st.success("✅ Recording captured successfully!")
        st.audio(audio_data["bytes"], format="audio/wav")
        with st.spinner("🔍 Transcribing your introduction..."):
            intro_text = transcribe_audio(audio_data["bytes"])
        if intro_text:
            st.session_state.intro_text = intro_text
            st.markdown(f"**📝 Your introduction:** {intro_text}")
            with st.spinner("📊 Analyzing introduction for additional skills..."):
                detect_prompt = f"Extract technical skills mentioned in this introduction: {intro_text}\nReturn as JSON list: {{\"skills\": [\"skill1\", \"skill2\"]}}"
                response = groq_chat(detect_prompt, max_tokens=200)
                detected = safe_parse(response, {"skills": []})
                new_skills = detected.get("skills", [])
                if new_skills:
                    existing_skills = set(st.session_state.detected_speech_skills)
                    for skill in new_skills:
                        if skill not in existing_skills:
                            st.session_state.detected_speech_skills.append(skill)
                    st.success(f"🎯 Detected additional skills: {', '.join(new_skills)}")
            st.session_state.intro_recorded = True
            st.rerun()
        else:
            st.warning("⚠️ Could not transcribe your introduction. Please try again.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get('intro_text', ''):
        st.markdown("---")
        st.markdown("### ✅ Your Introduction")
        st.markdown(f"**Recorded:** {st.session_state.intro_text}")
        if st.button("🔄 Re-record Introduction", use_container_width=True):
            st.session_state.intro_recorded = False
            st.session_state.intro_text = ""
            st.rerun()
    
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("▶ Generate Questions & Start Interview", type="primary", use_container_width=True, disabled=not st.session_state.get('intro_recorded', False)):
            with st.spinner("🔧 Generating personalized interview questions..."):
                all_questions = generate_all_questions(
                    st.session_state.resume_data,
                    st.session_state.resume_skills,
                    st.session_state.detected_speech_skills,
                    st.session_state.user_registration or {}
                )
                st.session_state.all_questions = all_questions
                st.session_state.current_q = 0
                st.session_state.answers = []
                st.session_state.evaluations = []
            st.success(f"✅ Generated {len(all_questions)} questions for the interview")
            time.sleep(2)
            st.session_state.stage = "questions"
            st.rerun()
    with col2:
        if st.button("← Back to Resume Upload", use_container_width=True):
            st.session_state.stage = "intro"
            st.rerun()

def show_interview_questions():
    show_navbar()
    
    questions = st.session_state.all_questions
    q_idx = st.session_state.current_q
    
    if q_idx >= len(questions):
        st.session_state.stage = "evaluating"
        st.rerun()
    
    q = questions[q_idx]
    total = len(questions)
    topic = q.get("topic", "General")
    q_text = q.get("question", "—")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem;">
        <h2 style="color: white; text-align: center;">🎤 Live Interview</h2>
        <div style="background: white; border-radius: 10px; padding: 1rem; margin-top: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                <span style="color: #667eea; font-weight: bold;">Question {q_idx+1} of {total}</span>
                <span style="color: #10b981; font-weight: bold;">✅ Answered: {len(st.session_state.answers)}</span>
            </div>
            <div class="progress-container">
                <div class="progress-fill" style="width: {(q_idx/total)*100}%"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="modern-card">
        <h3>📌 Topic: {topic}</h3>
        <p style="font-size: 1.2rem; line-height: 1.6;">{q_text}</p>
    </div>
    """, unsafe_allow_html=True)
    
    spoken_key = f"spoken_{q_idx}"
    if spoken_key not in st.session_state or not st.session_state[spoken_key]:
        speak(q_text, key=f"speak_{q_idx}")
        st.session_state[spoken_key] = True
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔊 Replay Question", key=f"replay_{q_idx}", use_container_width=True):
            speak(q_text, key=f"replay_audio_{q_idx}")
    
    st.markdown("---")
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("#### 🎙️ Your Answer")
    st.caption("1. Click **Start Recording** → 2. Speak clearly → 3. Click **Stop Recording** → 4. Click **Submit Answer**")
    
    if not MIC_RECORDER_OK:
        st.error("❌ Voice recording feature not available.")
        st.stop()
    
    audio_data = mic_recorder(
        start_prompt="🎙 Start Recording",
        stop_prompt="⏹ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
        key=f"recorder_q{q_idx}"
    )
    
    captured = ""
    if audio_data:
        st.success("✅ Answer recorded!")
        st.audio(audio_data["bytes"], format="audio/wav")
        with st.spinner("🔍 Transcribing your answer..."):
            captured = transcribe_audio(audio_data["bytes"])
        if captured:
            st.markdown(f"**📝 Your answer:** {captured}")
        else:
            st.warning("⚠️ Could not transcribe. Please re-record.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("✅ Submit Answer", type="primary", use_container_width=True, key=f"submit_{q_idx}", disabled=not bool(captured)):
            with st.spinner("Evaluating your answer..."):
                evaluation = evaluate_answer(topic, q_text, captured, st.session_state.user_registration)
            st.session_state.answers.append({"topic": topic, "question": q_text, "answer": captured})
            st.session_state.evaluations.append(evaluation)
            st.session_state.current_q += 1
            st.rerun()
    with col2:
        if st.button("🔄 Re-record", use_container_width=True, key=f"rerecord_{q_idx}"):
            st.rerun()
    with col3:
        if st.button("⏭️ Skip", use_container_width=True, key=f"skip_{q_idx}"):
            st.session_state.answers.append({"topic": topic, "question": q_text, "answer": "[Skipped]"})
            st.session_state.evaluations.append({"score": 0, "feedback": "Question skipped", "strengths": [], "improvements": ["Please provide an answer for better evaluation"]})
            st.session_state.current_q += 1
            st.rerun()

def show_evaluating():
    show_navbar()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">⚙️ Generating Your Report</h1>
        <p style="color: rgba(255,255,255,0.9);">Analyzing all your answers...</p>
    </div>
    """, unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    progress_bar.progress(30)
    
    st.session_state.final_report = generate_final_report(
        candidate_name=st.session_state.resume_data.get("candidate_name", "Candidate"),
        resume_data=st.session_state.resume_data,
        resume_skills=st.session_state.resume_skills,
        detected_speech_skills=st.session_state.detected_speech_skills,
        answers=st.session_state.answers,
        evaluations=st.session_state.evaluations,
        user_registration=st.session_state.user_registration or {}
    )
    
    progress_bar.progress(70)
    
    session_id = hashlib.md5(f"{st.session_state.user_id}_{datetime.now().timestamp()}".encode()).hexdigest()
    save_interview_session(
        st.session_state.user_id,
        session_id,
        st.session_state.resume_data,
        st.session_state.resume_skills,
        st.session_state.all_questions,
        st.session_state.answers,
        st.session_state.evaluations,
        st.session_state.final_report,
        st.session_state.final_report.get("overall_score", 0),
        st.session_state.final_report.get("recommended_for_next_round", False)
    )
    
    progress_bar.progress(100)
    st.success("✅ Report generated successfully!")
    time.sleep(2)
    st.session_state.stage = "report"
    st.rerun()

def show_report():
    show_navbar()
    
    report = st.session_state.final_report
    if not report:
        st.warning("No report data available.")
        return
    
    overall = report.get("overall_score", 0)
    pct = overall * 10
    grade, grade_label = get_grade(pct)
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white;">📊 Interview Report</h1>
        <p style="color: rgba(255,255,255,0.9);">Candidate: {report.get('candidate_name', 'Candidate')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Technical Score", f"{report.get('technical_score', 0)}/10")
    col2.metric("Communication Score", f"{report.get('communication_score', 0)}/10")
    col3.metric("Confidence Score", f"{report.get('confidence_score', 0)}/10")
    col4.metric("Overall Score", f"{overall}/10")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="modern-card">
            <h3>🏆 Performance Summary</h3>
            <p><strong>Grade:</strong> {grade} {grade_label}</p>
            <p><strong>Next Round:</strong> {'✅ Recommended' if report.get('recommended_for_next_round') else '❌ Not Recommended'}</p>
            <p><strong>Percentile Rank:</strong> {report.get('percentile_rank', 0)}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="modern-card">
            <h3>📊 Experience Analysis</h3>
            <p><strong>Experience Level:</strong> {report.get('experience_display', 'Not specified')}</p>
            <p><strong>Performance vs Expectations:</strong> {'+' if report.get('performance_vs_expectation', 0) >= 0 else ''}{report.get('performance_vs_expectation', 0)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 20px; margin-bottom: 2rem;">
        <h2 style="color: white; text-align: center;">📝 Question-wise Feedback</h2>
        <p style="color: rgba(255,255,255,0.9); text-align: center;">Detailed analysis of each question with your answers and AI evaluation</p>
    </div>
    """, unsafe_allow_html=True)
    
    answers = st.session_state.get('answers', [])
    evaluations = st.session_state.get('evaluations', [])
    
    if answers and evaluations:
        for idx, (answer_data, evaluation) in enumerate(zip(answers, evaluations), 1):
            topic = answer_data.get('topic', 'General')
            question = answer_data.get('question', 'N/A')
            user_answer = answer_data.get('answer', 'No answer provided')
            
            tech_score = evaluation.get('technical_accuracy', 0)
            comm_score = evaluation.get('communication_skills', 0)
            conf_score = evaluation.get('confidence', 0)
            completeness_score = evaluation.get('completeness', 0)
            relevance_score = evaluation.get('relevance', 0)
            total_score = evaluation.get('score', 0)
            feedback = evaluation.get('feedback', 'No feedback available')
            strengths = evaluation.get('strengths', [])
            improvements = evaluation.get('improvements', [])
            
            if total_score >= 7:
                score_icon = "✅"
            elif total_score >= 5:
                score_icon = "⚠️"
            else:
                score_icon = "❌"
            
            with st.expander(f"Question {idx}: {topic} - Score: {total_score}/10 {score_icon}", expanded=(idx == 1)):
                st.markdown(f"""
                <div class="modern-card">
                    <h4>📌 Question:</h4>
                    <p style="font-size: 1.05rem; background: #f8fafc; padding: 1rem; border-radius: 10px; border-left: 4px solid #6366f1;">
                        {question}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="modern-card">
                    <h4>🎤 Your Answer:</h4>
                    <p style="background: #fef3c7; padding: 1rem; border-radius: 10px; border-left: 4px solid #f59e0b;">
                        {user_answer}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Technical", f"{tech_score}/10")
                with col2:
                    st.metric("Communication", f"{comm_score}/10")
                with col3:
                    st.metric("Confidence", f"{conf_score}/10")
                with col4:
                    st.metric("Completeness", f"{completeness_score}/10")
                with col5:
                    st.metric("Relevance", f"{relevance_score}/10")
                
                st.markdown(f"""
                <div class="modern-card">
                    <h4>💬 AI Feedback:</h4>
                    <p style="background: #e0e7ff; padding: 1rem; border-radius: 10px;">
                        {feedback}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                if strengths:
                    st.markdown("**✅ Strengths:**")
                    for strength in strengths:
                        st.markdown(f"- {strength}")
                
                if improvements:
                    st.markdown("**📚 Areas for Improvement:**")
                    for improvement in improvements:
                        st.markdown(f"- {improvement}")
                
                st.markdown("### Score Breakdown")
                st.progress(tech_score/10, text=f"Technical: {tech_score}/10")
                st.progress(comm_score/10, text=f"Communication: {comm_score}/10")
                st.progress(conf_score/10, text=f"Confidence: {conf_score}/10")
                st.progress(completeness_score/10, text=f"Completeness: {completeness_score}/10")
                st.progress(relevance_score/10, text=f"Relevance: {relevance_score}/10")
                
                st.markdown("---")
    else:
        st.warning("No question data available.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="modern-card">
            <h3>✅ Overall Strengths</h3>
        </div>
        """, unsafe_allow_html=True)
        for strength in report.get('strengths', []):
            st.success(f"✓ {strength}")
        if not report.get('strengths'):
            st.info("No specific strengths identified")
    
    with col2:
        st.markdown("""
        <div class="modern-card">
            <h3>📚 Overall Areas for Improvement</h3>
        </div>
        """, unsafe_allow_html=True)
        for improvement in report.get('improvement_areas', []):
            st.warning(f"⚠️ {improvement}")
        if not report.get('improvement_areas'):
            st.info("No specific areas identified")
    
    st.markdown("---")
    
    st.markdown("### 📥 Download Your Report")
    
    report_text = f"""
    ========================================
    AI TECHNICAL INTERVIEW REPORT
    ========================================
    
    Candidate: {report.get('candidate_name', 'Candidate')}
    Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    ========================================
    OVERALL SCORES
    ========================================
    Technical Score: {report.get('technical_score', 0)}/10
    Communication Score: {report.get('communication_score', 0)}/10
    Confidence Score: {report.get('confidence_score', 0)}/10
    Overall Score: {overall}/10
    Grade: {grade} {grade_label}
    
    ========================================
    QUESTION-WISE FEEDBACK
    ========================================
    """
    
    for idx, (answer_data, evaluation) in enumerate(zip(answers, evaluations), 1):
        topic = answer_data.get('topic', 'General')
        question = answer_data.get('question', 'N/A')
        user_answer = answer_data.get('answer', 'No answer provided')
        tech_score = evaluation.get('technical_accuracy', 0)
        comm_score = evaluation.get('communication_skills', 0)
        conf_score = evaluation.get('confidence', 0)
        total_score = evaluation.get('score', 0)
        feedback = evaluation.get('feedback', 'No feedback')
        
        report_text += f"""
        
        Q{idx}. [{topic}] Score: {total_score}/10
        Question: {question}
        Answer: {user_answer}
        Technical: {tech_score}/10 | Communication: {comm_score}/10 | Confidence: {conf_score}/10
        Feedback: {feedback}
        """
        
        if evaluation.get('strengths'):
            report_text += f"\nStrengths: {', '.join(evaluation.get('strengths', []))}"
        if evaluation.get('improvements'):
            report_text += f"\nImprovements: {', '.join(evaluation.get('improvements', []))}"
    
    report_text += f"""
    
    ========================================
    RECOMMENDATIONS
    ========================================
    Next Round Recommendation: {'✅ Recommended' if report.get('recommended_for_next_round') else '❌ Not Recommended'}
    
    Strengths to Maintain:
    {chr(10).join(['- ' + s for s in report.get('strengths', [])]) if report.get('strengths') else '- No specific strengths identified'}
    
    Areas to Focus:
    {chr(10).join(['- ' + i for i in report.get('improvement_areas', [])]) if report.get('improvement_areas') else '- No specific areas identified'}
    
    ========================================
    Report generated by AI Technical Interview Assistant
    ========================================
    """
    
    st.download_button(
        label="📄 Download Full Report (TXT)",
        data=report_text,
        file_name=f"interview_report_{st.session_state.user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Start New Interview", use_container_width=True, type="primary"):
            reset_interview_state()
            st.session_state.stage = "welcome"
            st.rerun()
    with col2:
        if st.button("👤 View My Profile", use_container_width=True):
            st.session_state.stage = "profile"
            st.rerun()
    with col3:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.stage = "welcome"
            st.rerun()

def show_user_profile():
    show_navbar()
    
    user_id = st.session_state.user_id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        st.error("Unable to load user profile.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), AVG(overall_score) FROM interview_sessions WHERE user_id = ?", (user_id,))
    interview_stats = cursor.fetchone()
    total_interviews = interview_stats[0] if interview_stats[0] else 0
    avg_score = interview_stats[1] if interview_stats[1] else 0
    conn.close()
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 2rem;">
                <div style="background: white; width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 48px; color: #667eea;">{user_profile.get('full_name', 'U')[0].upper()}</span>
                </div>
                <div>
                    <h1 style="color: white;">{user_profile.get('full_name', 'User')}</h1>
                    <p style="color: rgba(255,255,255,0.9);">📧 {user_profile.get('email', 'No email')}</p>
                    <p style="color: rgba(255,255,255,0.9);">📱 {user_profile.get('phone', 'Not provided')}</p>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 15px; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: white;">{total_interviews}</div>
                <div style="color: rgba(255,255,255,0.9);">Interviews</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: white; margin-top: 0.5rem;">{avg_score:.1f}/10</div>
                <div style="color: rgba(255,255,255,0.9);">Avg Score</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Personal Info", "🎯 Career Goals", "💡 Skills & Interests", "📊 Interview History"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("**📝 Basic Information**")
            st.markdown(f"- **Full Name:** {user_profile.get('full_name')}")
            st.markdown(f"- **Current Role:** {user_profile.get('current_role') or 'Not specified'}")
            st.markdown(f"- **Experience:** {user_profile.get('experience_years')} years")
            st.markdown(f"- **Education:** {user_profile.get('education_level') or 'Not specified'}")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("**📅 Account Information**")
            st.markdown(f"- **Member Since:** {user_profile.get('registration_date')}")
            st.markdown(f"- **Last Login:** {user_profile.get('last_login')}")
            st.markdown("- **Account Status:** ✅ Active")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown(f"### 🎯 Primary Goal: **{user_profile.get('career_goal') or 'Not specified'}**")
        st.markdown(f"### 🏆 Target Role: **{user_profile.get('target_role') or 'Not specified'}**")
        st.markdown("---")
        st.markdown(f"**📌 Short-term Goal (6 months):** {user_profile.get('short_term_goal') or 'Not specified'}")
        st.markdown(f"**🌟 Long-term Goal (3-5 years):** {user_profile.get('long_term_goal') or 'Not specified'}")
        st.markdown("---")
        st.markdown(f"**💭 Why Technology?** {user_profile.get('why_tech') or 'Not specified'}")
        st.markdown(f"**📚 Learning Focus:** {user_profile.get('learning_goals') or 'Not specified'}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        interests = user_profile.get('interests', [])
        if interests:
            st.markdown("### 💡 Technical Interests")
            tags = "".join([f'<span class="skill-tag">{i}</span>' for i in interests])
            st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)
        
        if st.session_state.resume_skills:
            st.markdown("### 📄 Skills from Resume")
            skill_tags = "".join([f'<span class="skill-tag">{s}</span>' for s in st.session_state.resume_skills[:15]])
            st.markdown(f'<div>{skill_tags}</div>', unsafe_allow_html=True)
    
    with tab4:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT interview_date, overall_score, recommended 
            FROM interview_sessions 
            WHERE user_id = ? 
            ORDER BY interview_date DESC
        ''', (user_id,))
        sessions = cursor.fetchall()
        conn.close()
        
        if sessions:
            for session in sessions:
                date, score, recommended = session
                status = "✅ Recommended" if recommended else "⚠️ Needs Improvement"
                st.markdown(f"""
                <div class="modern-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>📅 {date}</strong><br>
                            Score: <span style="font-size: 1.2rem; font-weight: bold;">{score:.1f}/10</span>
                        </div>
                        <div>{status}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No interviews completed yet. Start your first interview!")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.session_state.stage = "registration"
            st.rerun()
    with col2:
        if st.button("🚀 Start Interview", use_container_width=True, type="primary"):
            reset_interview_state()
            st.session_state.stage = "welcome"
            st.rerun()

# Main router
if not st.session_state.logged_in:
    show_login()
else:
    if st.session_state.stage == "welcome":
        show_welcome()
    elif st.session_state.stage == "profile":
        show_user_profile()
    elif st.session_state.stage == "registration":
        show_registration_form()
    elif st.session_state.stage == "intro":
        show_resume_upload()
    elif st.session_state.stage == "resume":
        show_voice_introduction()
    elif st.session_state.stage == "questions":
        show_interview_questions()
    elif st.session_state.stage == "evaluating":
        show_evaluating()
    elif st.session_state.stage == "report":
        show_report()