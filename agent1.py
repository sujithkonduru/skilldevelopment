"""
agent1.py — AI Technical Interview Assistant (FIXED VERSION)
Fixed: Prevents infinite question generation and duplicate questions
"""

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from dotenv import load_dotenv
import json, re, tempfile, os, time, random, base64

load_dotenv()
from io import BytesIO
from typing import List, Dict, Any

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

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Technical Interview Assistant",
    page_icon="🎯", layout="wide",
    initial_sidebar_state="expanded",
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Behavioral question pool
BEHAVIORAL_POOL = [
    {"topic": "Challenging Project", "question": "Tell me about a challenging project you worked on. What was your role and how did you overcome obstacles?"},
    {"topic": "Team Conflict", "question": "Describe a situation where you had to resolve a team conflict. What was the outcome?"},
    {"topic": "Missed Deadline", "question": "Explain a time when you missed a deadline and how you handled it."},
    {"topic": "Technical Problem Solving", "question": "Describe a difficult technical problem you faced and how you solved it."},
    {"topic": "Learning from Failure", "question": "Describe a project that didn't go as planned. What did you learn from it?"},
    {"topic": "Team Collaboration", "question": "How do you collaborate with cross-functional teams on technical projects?"},
]

GRADE_MAP = [
    (90, "A+", "🏆 Outstanding"),
    (80, "A",  "🎉 Excellent"),
    (70, "B",  "👍 Good"),
    (60, "C",  "📚 Average"),
    (50, "D",  "⚠️ Below Average"),
    (0,  "F",  "❌ Needs Improvement"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
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
    """Play text as audio."""
    if GTTS_OK:
        try:
            buf = BytesIO()
            gTTS(text=text, lang="en", slow=False).write_to_fp(buf)
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode()
            components.html(
                f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
                height=0,
            )
            return
        except Exception:
            pass
    # Web Speech API fallback
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
    """Transcribe audio bytes using Groq's Whisper API."""
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

# ═══════════════════════════════════════════════════════════════════════════════
# RESUME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def extract_text_from_pdf(pdf_file) -> str:
    if not PDF_OK:
        return ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        return " ".join(p.extract_text() or "" for p in reader.pages)
    except Exception:
        return ""

def parse_resume(resume_text: str) -> Dict[str, Any]:
    """Extract structured information from resume."""
    prompt = f"""
    Parse the following resume and extract structured information.
    Return ONLY valid JSON with this exact structure:
    {{
        "candidate_name": "",
        "professional_summary": "",
        "skills": {{
            "technical": [],
            "non_technical": []
        }},
        "projects": [],
        "work_experience": [],
        "education": [],
        "certifications": []
    }}
    
    Resume text:
    {resume_text[:4000]}
    """
    
    response = groq_chat(prompt, max_tokens=1000)
    return safe_parse(response, {
        "candidate_name": "Unknown",
        "professional_summary": "",
        "skills": {"technical": [], "non_technical": []},
        "projects": [],
        "work_experience": [],
        "education": [],
        "certifications": []
    })

def extract_technical_terms_from_resume(resume_data: Dict) -> List[str]:
    """Extract technical skills from parsed resume."""
    technical_skills = resume_data.get("skills", {}).get("technical", [])
    return list(set(technical_skills))  # Remove duplicates

# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION GENERATION (ONLY ONCE)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_behavioral_questions(resume_data: Dict, count: int = 5) -> List[Dict]:
    """Generate behavioral questions based on candidate's experience."""
    selected = random.sample(BEHAVIORAL_POOL, min(count, len(BEHAVIORAL_POOL)))
    return selected

def determine_skill_level(skill: str, resume_data: Dict) -> str:
    """Determine difficulty level based on where skill appears."""
    skill_lower = skill.lower()
    
    for work in resume_data.get("work_experience", []):
        if skill_lower in work.get("description", "").lower():
            return "advanced"
    
    for project in resume_data.get("projects", []):
        if skill_lower in project.get("description", "").lower():
            return "intermediate"
    
    return "beginner"

def generate_skill_question(skill: str, level: str) -> Dict:
    """Generate a single question for a specific skill."""
    prompt = f"""
    Generate exactly ONE interview question for the technical skill "{skill}".
    Difficulty level: {level.upper()}
    
    Return ONLY valid JSON: {{"topic": "{skill}", "question": "your question here"}}
    """
    
    response = groq_chat(prompt, max_tokens=200)
    result = safe_parse(response, {"topic": skill, "question": f"Explain {skill} and describe a scenario where you would use it."})
    return result

def generate_all_questions(resume_data: Dict, resume_skills: List[str], detected_skills: List[str]) -> List[Dict]:
    """Generate ALL questions ONCE at the beginning of the interview."""
    all_skills = list(dict.fromkeys(resume_skills + detected_skills))
    
    # Limit to 8 skills to keep interview reasonable
    selected_skills = all_skills[:8]
    
    # Generate behavioral questions (5 questions)
    behavioral_questions = generate_behavioral_questions(resume_data, count=5)
    
    # Generate skill-based questions (1 per skill)
    skill_questions = []
    for skill in selected_skills:
        level = determine_skill_level(skill, resume_data)
        skill_q = generate_skill_question(skill, level)
        skill_questions.append(skill_q)
    
    # Combine and shuffle
    all_questions = behavioral_questions + skill_questions
    random.shuffle(all_questions)
    
    return all_questions

# ═══════════════════════════════════════════════════════════════════════════════
# ANSWER EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════
def evaluate_answer(topic: str, question: str, answer: str) -> Dict:
    """Evaluate answer with scores for multiple categories."""
    if answer.strip() in ("", "[Skipped]"):
        return {
            "technical_accuracy": 0,
            "communication_skills": 0,
            "confidence": 0,
            "completeness": 0,
            "relevance": 0,
            "score": 0,
            "feedback": "No answer provided."
        }
    
    prompt = f"""
    You are a Senior Technical Interviewer. Evaluate this candidate's answer.
    
    Topic: {topic}
    Question: {question}
    Answer: {answer}
    
    Rate each category from 1-10:
    - Technical accuracy: Is the technical content correct?
    - Communication skills: How clearly is the answer expressed?
    - Confidence: Does the answer show assurance?
    - Completeness: Does it fully address the question?
    - Relevance: Is the answer on-topic?
    
    Return ONLY valid JSON:
    {{
        "technical_accuracy": 7,
        "communication_skills": 8,
        "confidence": 7,
        "completeness": 6,
        "relevance": 9,
        "score": 7,
        "feedback": "Brief feedback summary",
        "strengths": ["strength1", "strength2"],
        "improvements": ["improvement1", "improvement2"]
    }}
    """
    
    response = groq_chat(prompt, max_tokens=500)
    result = safe_parse(response, {
        "technical_accuracy": 5,
        "communication_skills": 5,
        "confidence": 5,
        "completeness": 5,
        "relevance": 5,
        "score": 5,
        "feedback": "Evaluation completed.",
        "strengths": [],
        "improvements": []
    })
    
    avg_score = (
        result.get("technical_accuracy", 5) +
        result.get("communication_skills", 5) +
        result.get("confidence", 5) +
        result.get("completeness", 5) +
        result.get("relevance", 5)
    ) / 5
    
    result["score"] = round(avg_score, 1)
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_final_report(
    candidate_name: str,
    resume_skills: List[str],
    detected_speech_skills: List[str],
    answers: List[Dict],
    evaluations: List[Dict]
) -> Dict:
    """Generate comprehensive final report."""
    
    technical_scores = []
    communication_scores = []
    confidence_scores = []
    
    for eval_data in evaluations:
        communication_scores.append(eval_data.get("communication_skills", 5))
        confidence_scores.append(eval_data.get("confidence", 5))
        technical_scores.append(eval_data.get("technical_accuracy", 5))
    
    technical_score = sum(technical_scores) / len(technical_scores) if technical_scores else 0
    communication_score = sum(communication_scores) / len(communication_scores) if communication_scores else 0
    confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    overall_score = (technical_score + communication_score + confidence_score) / 3
    
    all_strengths = []
    all_improvements = []
    for eval_data in evaluations:
        all_strengths.extend(eval_data.get("strengths", []))
        all_improvements.extend(eval_data.get("improvements", []))
    
    unique_strengths = list(dict.fromkeys(all_strengths))[:5]
    unique_improvements = list(dict.fromkeys(all_improvements))[:5]
    
    recommended = overall_score >= 6.5
    
    return {
        "candidate_name": candidate_name,
        "resume_skills": resume_skills,
        "detected_skills_from_speech": detected_speech_skills,
        "technical_score": round(technical_score, 1),
        "communication_score": round(communication_score, 1),
        "confidence_score": round(confidence_score, 1),
        "overall_score": round(overall_score, 1),
        "strengths": unique_strengths,
        "improvement_areas": unique_improvements,
        "recommended_for_next_round": recommended
    }

def get_grade(pct: float):
    for threshold, grade, label in GRADE_MAP:
        if pct >= threshold:
            return grade, label
    return "F", "❌ Needs Improvement"

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULTS = dict(
    stage="welcome",
    input_method=None,
    resume_data=None,
    resume_skills=[],
    detected_speech_skills=[],
    all_questions=[],           # ALL questions generated ONCE
    current_q=0,
    answers=[],
    evaluations=[],
    final_report=None,
    greeted=False,
)
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🎯 Interview Progress")
    st.markdown("---")
    stage_labels = {
        "welcome": "🏠 Welcome",
        "intro": "📄 Resume Upload",
        "resume": "📋 Analysis",
        "questions": "❓ Interview",
        "evaluating": "⚙️ Evaluating",
        "report": "📊 Report",
    }
    st.markdown(f"**Stage:** {stage_labels.get(st.session_state.stage, '—')}")

    if st.session_state.stage == "questions" and st.session_state.all_questions:
        total = len(st.session_state.all_questions)
        done = st.session_state.current_q
        st.progress(done / total)
        st.markdown(f"**Q {done} / {total}**")

    if st.session_state.resume_skills:
        st.markdown("---")
        st.markdown("**📌 Skills to Assess:**")
        for t in st.session_state.resume_skills[:8]:
            st.markdown(f"- `{t}`")

    st.markdown("---")
    if st.button("🔄 Restart", use_container_width=True):
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: WELCOME
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "welcome":
    st.title("🎯 AI Technical Interview Assistant")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
### Complete Interview Process:
1. 📄 **Upload your Resume (PDF)** — AI analyzes your skills and experience
2. 🎤 **Voice Introduction** — Tell us about yourself
3. ❓ **Personalized Interview** — 10-12 questions (behavioral + technical)
4. 📊 **Comprehensive Report** — Scores, feedback, and recommendations

**Note:** Questions are generated ONCE based on your resume. No new questions are added during the interview.
        """)
    
    with col2:
        if st.button("📄 Start Interview", use_container_width=True, type="primary"):
            st.session_state.stage = "intro"
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: INTRO (Resume Upload)
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "intro":
    st.title("📄 Step 1 — Upload Your Resume")
    st.markdown("---")
    
    pdf = st.file_uploader("Choose your resume PDF", type=["pdf"])
    
    if pdf:
        if st.button("▶ Analyze Resume", type="primary"):
            with st.spinner("Reading and analyzing resume..."):
                resume_text = extract_text_from_pdf(pdf)
            
            if not resume_text.strip():
                st.error("Could not read PDF. Please try a different file.")
                st.stop()
            
            with st.spinner("🧠 Extracting structured information..."):
                resume_data = parse_resume(resume_text)
                resume_skills = extract_technical_terms_from_resume(resume_data)
            
            st.session_state.resume_data = resume_data
            st.session_state.resume_skills = resume_skills
            
            st.success(f"✅ Found {len(resume_skills)} technical skills")
            st.json({
                "candidate_name": resume_data.get("candidate_name", "Not found"),
                "technical_skills": resume_skills[:10],
            })
            
            st.session_state.stage = "resume"
            time.sleep(1)
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: RESUME (Voice Introduction)
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "resume":
    st.title("🎤 Step 2 — Voice Introduction")
    st.markdown("---")
    
    st.markdown("""
    **Tell me about yourself.**
    
    Please introduce yourself — mention your name, background, and the technologies you work with.
    """)
    
    if not st.session_state.greeted:
        speak(
            "Please introduce yourself. Tell me about your background and the technologies you work with.",
            key="intro_greet"
        )
        st.session_state.greeted = True
    
    st.info("📌 Click **Start recording**, speak your introduction, then click **Stop recording**.")
    
    if not MIC_RECORDER_OK:
        st.error("❌ streamlit-mic-recorder not installed.")
        st.stop()
    
    audio_data = mic_recorder(
        start_prompt="🎙 Start Recording",
        stop_prompt="⏹ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
    )
    
    intro_text = ""
    if audio_data:
        st.success("✅ Recording captured!")
        st.audio(audio_data["bytes"], format="audio/wav")
        
        with st.spinner("🔍 Transcribing your introduction..."):
            intro_text = transcribe_audio(audio_data["bytes"])
        
        if intro_text:
            st.markdown(f"**📝 Your introduction:** {intro_text}")
    
    st.markdown("---")
    
    if st.button("▶ Generate Questions & Start Interview", type="primary", use_container_width=True,
                disabled=not intro_text):
        
        with st.spinner("🔧 Generating personalized interview questions (this happens ONCE)..."):
            # Generate ALL questions once at the beginning
            all_questions = generate_all_questions(
                st.session_state.resume_data,
                st.session_state.resume_skills,
                st.session_state.detected_speech_skills
            )
            
            st.session_state.all_questions = all_questions
            st.session_state.current_q = 0
            st.session_state.answers = []
            st.session_state.evaluations = []
        
        st.success(f"✅ Generated {len(all_questions)} questions for the interview")
        time.sleep(1)
        st.session_state.stage = "questions"
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: QUESTIONS (Fixed - No dynamic generation during interview)
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "questions":
    questions = st.session_state.all_questions
    q_idx = st.session_state.current_q
    
    if q_idx >= len(questions):
        st.session_state.stage = "evaluating"
        st.rerun()
    
    q = questions[q_idx]
    total = len(questions)
    topic = q.get("topic", "General")
    q_text = q.get("question", "—")
    
    # Header
    st.title("🎤 Live Interview")
    st.progress(q_idx / total)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Question {q_idx+1} of {total}** • Topic: `{topic}`")
    with col2:
        st.markdown(f"✅ Answered: {len(st.session_state.answers)}")
    
    st.markdown("---")
    st.markdown(f"### {q_text}")
    st.markdown("---")
    
    # Speak question once
    spoken_key = f"spoken_{q_idx}"
    if spoken_key not in st.session_state or not st.session_state[spoken_key]:
        speak(q_text, key=f"speak_{q_idx}")
        st.session_state[spoken_key] = True
    
    if st.button("🔊 Replay Question", key=f"replay_{q_idx}"):
        speak(q_text, key=f"replay_audio_{q_idx}")
    
    st.markdown("#### 🎙️ Your Answer")
    st.caption("1. Click **Start Recording** → 2. Speak clearly → 3. Click **Stop Recording** → 4. Click **Submit Answer**")
    
    if not MIC_RECORDER_OK:
        st.error("❌ streamlit-mic-recorder not installed.")
        st.stop()
    
    audio_data = mic_recorder(
        start_prompt="🎙 Start Recording",
        stop_prompt="⏹ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
        key=f"recorder_q{q_idx}",
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
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        submit_disabled = not bool(captured)
        if st.button("✅ Submit Answer", type="primary", use_container_width=True,
                    key=f"submit_{q_idx}", disabled=submit_disabled):
            
            with st.spinner("Evaluating your answer..."):
                evaluation = evaluate_answer(topic, q_text, captured)
            
            st.session_state.answers.append({
                "topic": topic,
                "question": q_text,
                "answer": captured
            })
            st.session_state.evaluations.append(evaluation)
            
            st.session_state.current_q += 1
            st.rerun()
    
    with col2:
        if st.button("🔄 Re-record", use_container_width=True, key=f"rerecord_{q_idx}"):
            st.rerun()
    
    with col3:
        if st.button("⏭️ Skip", use_container_width=True, key=f"skip_{q_idx}"):
            st.session_state.answers.append({
                "topic": topic,
                "question": q_text,
                "answer": "[Skipped]"
            })
            st.session_state.evaluations.append({
                "score": 0,
                "feedback": "Question skipped",
                "strengths": [],
                "improvements": ["Please provide an answer for better evaluation"]
            })
            st.session_state.current_q += 1
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: EVALUATING
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "evaluating":
    st.title("⚙️ Generating Final Report")
    st.markdown("---")
    st.info("Analyzing all your answers...")
    
    progress_bar = st.progress(0)
    
    progress_bar.progress(0.5)
    st.session_state.final_report = generate_final_report(
        candidate_name=st.session_state.resume_data.get("candidate_name", "Candidate"),
        resume_skills=st.session_state.resume_skills,
        detected_speech_skills=st.session_state.detected_speech_skills,
        answers=st.session_state.answers,
        evaluations=st.session_state.evaluations
    )
    
    progress_bar.progress(1.0)
    st.success("✅ Report generated successfully!")
    time.sleep(1)
    st.session_state.stage = "report"
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE: REPORT
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "report":
    report = st.session_state.final_report
    
    if not report:
        st.warning("No report data available.")
        st.stop()
    
    overall = report.get("overall_score", 0)
    pct = overall * 10
    grade, grade_label = get_grade(pct)
    
    speak(
        f"Your interview is complete. Your overall score is {overall} out of 10, "
        f"achieving a grade of {grade}.",
        key="report_speak"
    )
    
    st.title("📊 Interview Report")
    st.markdown(f"**Candidate:** {report.get('candidate_name', 'Unknown')}")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Technical Score", f"{report.get('technical_score', 0)}/10")
    col2.metric("Communication Score", f"{report.get('communication_score', 0)}/10")
    col3.metric("Confidence Score", f"{report.get('confidence_score', 0)}/10")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Score", f"{overall}/10")
    col2.metric("Grade", f"{grade} {grade_label}")
    col3.metric("Next Round", "✅ Yes" if report.get('recommended_for_next_round') else "❌ No")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Strengths")
        for strength in report.get('strengths', []):
            st.success(f"✓ {strength}")
    with col2:
        st.subheader("📚 Areas for Improvement")
        for improvement in report.get('improvement_areas', []):
            st.warning(f"⚠️ {improvement}")
    
    st.markdown("---")
    
    st.subheader("📝 Question-by-Question Analysis")
    for i, (answer, evaluation) in enumerate(zip(st.session_state.answers, st.session_state.evaluations)):
        score = evaluation.get("score", 0)
        icon = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
        
        with st.expander(f"{icon} Q{i+1}: {answer.get('topic', 'General')} — Score: {score}/10"):
            st.markdown(f"**Question:** {answer.get('question', '')}")
            st.markdown(f"**Your Answer:** {answer.get('answer', '')}")
            st.markdown(f"**Feedback:** {evaluation.get('feedback', '')}")
    
    st.markdown("---")
    
    report_json = json.dumps({
        "candidate_name": report.get('candidate_name'),
        "resume_skills": report.get('resume_skills'),
        "overall_score": report.get('overall_score'),
        "recommended_for_next_round": report.get('recommended_for_next_round'),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }, indent=2)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Report (JSON)",
            data=report_json,
            file_name=f"interview_report_{time.strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        if st.button("🔄 Start New Interview", use_container_width=True):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()