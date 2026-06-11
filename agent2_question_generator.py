"""
agent2_question_generator.py
────────────────────────────
Standalone Streamlit page that:
  1. Speaks a greeting and asks the candidate to introduce themselves (audio)
  2. Transcribes the self-intro via Groq Whisper
  3. Extracts technical terms with Groq LLM
  4. If NO technical terms found → asks a follow-up project question (audio)
  5. Merges all terms, generates a rich question set (behavioral + technical)
  6. Saves questions to  st.session_state  so the main interview app can read them
     (or writes them to  questions_output.json  when running standalone)

Run standalone:   streamlit run agent2_question_generator.py
Integrate:        import agent2_question_generator   (it sets st.session_state.questions)
"""

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json, re, tempfile, os, time, random

# ─── Groq client ──────────────────────────────────────────────────────────────
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

# ─── Page config (safe to call multiple times; Streamlit ignores duplicates) ──
st.set_page_config(page_title="Interview Setup", page_icon="🎙️", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_POOL = [
    {"topic": "Self Introduction",  "question": "Tell me about yourself and your professional background."},
    {"topic": "Project Experience", "question": "Describe a recent technical project you worked on and your role in it."},
    {"topic": "Challenge Handling", "question": "What was a difficult technical problem you faced and how did you solve it?"},
    {"topic": "Teamwork",           "question": "How do you collaborate with teammates on a technical project?"},
    {"topic": "Strengths",          "question": "What are your greatest strengths as a developer?"},
    {"topic": "Weaknesses",         "question": "What technical areas are you currently working to improve?"},
    {"topic": "Career Goals",       "question": "Where do you see yourself in the next 3-5 years technically?"},
    {"topic": "Learning",           "question": "How do you keep yourself updated with the latest technology trends?"},
]

def clean_json(text: str) -> str:
    text = re.sub(r"꽁.*?꽁", "", text, flags=re.DOTALL)
    return text.replace("```json", "").replace("```", "").strip()

def groq_chat(prompt: str, max_tokens: int = 600) -> str:
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=max_tokens,
    )
    return r.choices[0].message.content

def transcribe_bytes(audio_bytes: bytes, filename: str = "intro.wav") -> str:
    """Transcribe raw audio bytes with Groq Whisper."""
    suffix = os.path.splitext(filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(filename, f),
                model="whisper-large-v3-turbo",
            )
        return result.text.strip()
    finally:
        os.unlink(tmp_path)

def extract_technical_terms(transcript: str) -> list[str]:
    """Return a list of technical terms from the transcript (may be empty)."""
    if not transcript:
        return []
    raw = groq_chat(
        f"Extract ONLY technical terms (programming languages, frameworks, tools, concepts, platforms). "
        f"Correct obvious speech-to-text mistakes (e.g. 'Quinn' → 'Qwen', 'react' → 'React'). "
        f"If there are NO technical terms at all, return an empty list. "
        f"Return ONLY valid JSON: {{\"technical_terms\": []}}\n\nTranscript:\n{transcript}",
        max_tokens=400,
    )
    try:
        data = json.loads(clean_json(raw))
        terms = data.get("technical_terms", [])
        return [str(t).strip() for t in terms if str(t).strip()]
    except Exception:
        return []

def generate_technical_questions(terms: list[str], count: int) -> list[dict]:
    """Ask Groq to generate `count` technical questions, one per term."""
    if not terms:
        return []
    raw = groq_chat(
        f"Generate exactly one technical interview question for each of these topics: {json.dumps(terms[:count])}.\n"
        f"Return ONLY valid JSON array:\n"
        f'[{{"topic":"Python","question":"Explain decorators in Python."}}]\n'
        f"Limit: {count} questions, one per topic.",
        max_tokens=1200,
    )
    try:
        questions = json.loads(clean_json(raw))
        if isinstance(questions, list):
            return questions[:count]
    except Exception:
        pass
    # fallback
    return [{"topic": t, "question": f"Explain {t} and how you have used it."} for t in terms[:count]]

def build_question_set(terms: list[str], total: int = 10) -> list[dict]:
    """
    Build the final question list:
      • All 8 behavioral questions (shuffled)
      • Technical questions to fill the remaining slots
    """
    behavioral = [q.copy() for q in BEHAVIORAL_POOL]
    random.shuffle(behavioral)

    tech_slots  = max(0, total - len(behavioral))
    technical   = generate_technical_questions(terms, tech_slots) if terms else []

    questions   = behavioral + technical
    return questions[:total]

def speak_component(text: str, auto: bool = True) -> None:
    """Inject a tiny JS snippet that speaks `text` via the browser TTS."""
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    auto_js = "speakNow();" if auto else ""
    components.html(f"""<script>
function speakNow(){{
  window.speechSynthesis.cancel();
  var u=new SpeechSynthesisUtterance(`{safe}`);
  u.rate=0.9;u.pitch=1.0;u.lang='en-US';
  var voices=window.speechSynthesis.getVoices();
  var v=voices.find(x=>x.name.includes('Google US English'))||
        voices.find(x=>x.name.includes('Samantha'))||
        voices.find(x=>x.lang==='en-US');
  if(v)u.voice=v;
  window.speechSynthesis.speak(u);
}}
if(window.speechSynthesis.getVoices().length>0){{{auto_js}}}
else window.speechSynthesis.onvoiceschanged=speakNow;
</script>""", height=0)

def voice_recorder_component(prompt_label: str, component_key: str) -> str | None:
    """
    Render an inline Web-Speech-API recorder.
    Returns the transcribed text string when the user stops,
    or None while still recording / not yet started.
    Uses st.session_state keyed by `component_key` to persist the result
    across Streamlit reruns.
    """
    result_key = f"_rec_result_{component_key}"
    if result_key not in st.session_state:
        st.session_state[result_key] = None

    safe_label = prompt_label.replace("`", "'").replace("\\", "\\\\")

    html_code = f"""
<!DOCTYPE html><html><head>
<style>
 *{{box-sizing:border-box;margin:0;padding:0;font-family:sans-serif}}
 body{{background:transparent;padding:6px}}
 #ta{{width:100%;min-height:130px;padding:10px;border:2px solid #4CAF50;
      border-radius:10px;font-size:15px;line-height:1.5;
      background:#f0fdf0;color:#111;resize:vertical;margin-bottom:8px}}
 #ta.rec{{border-color:#e53935;background:#fff5f5}}
 .row{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}}
 button{{padding:9px 18px;border:none;border-radius:7px;font-size:14px;
         font-weight:600;cursor:pointer}}
 button:disabled{{opacity:.4;cursor:not-allowed}}
 #sb{{background:#e53935;color:#fff}}
 #pb{{background:#1565c0;color:#fff}}
 #st2{{margin-top:6px;font-size:13px;color:#555;min-height:18px}}
 @keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
 .blink{{animation:blink 1s infinite}}
</style></head><body>
<p style="font-size:14px;margin-bottom:6px;font-weight:600">{safe_label}</p>
<textarea id="ta" placeholder="Your speech appears here in real-time..."></textarea>
<div class="row">
  <button id="sb">🎙️ Start Recording</button>
  <button id="pb" disabled>⏹ Stop &amp; Save</button>
</div>
<div id="st2">Click Start Recording, speak, then click Stop &amp; Save.</div>
<script>
const SR = window.SpeechRecognition||window.webkitSpeechRecognition;
const ta=document.getElementById('ta'),sb=document.getElementById('sb'),
      pb=document.getElementById('pb'),st=document.getElementById('st2');
let rec,listening=false,final_="",done=false;

if(!SR){{st.textContent="❌ Use Chrome or Edge for speech recognition.";sb.disabled=true;}}

sb.onclick=()=>{{
  if(!SR||done)return;
  final_="";ta.value="";
  rec=new SR();
  rec.continuous=true;rec.interimResults=true;rec.lang='en-US';
  rec.onstart=()=>{{listening=true;sb.disabled=true;pb.disabled=false;
    ta.classList.add('rec');
    st.innerHTML='<span class="blink">🔴</span> Listening — speak clearly...';
  }};
  rec.onresult=(e)=>{{
    let interim="",nf="";
    for(let i=e.resultIndex;i<e.results.length;i++){{
      if(e.results[i].isFinal)nf+=e.results[i][0].transcript+" ";
      else interim+=e.results[i][0].transcript;
    }}
    if(nf)final_+=nf;
    ta.value=final_+interim;
    ta.scrollTop=ta.scrollHeight;
  }};
  rec.onerror=(e)=>{{st.textContent="❌ "+e.error;stopRec();}};
  rec.onend=()=>{{if(listening)rec.start();}};  // auto-restart
  rec.start();
}};

function stopRec(){{
  listening=false;
  if(rec){{rec.onend=null;rec.stop();}}
  sb.disabled=false;pb.disabled=true;
  ta.classList.remove('rec');
  const txt=final_.trim();
  if(txt.length>3){{
    done=true;sb.disabled=true;
    st.textContent="✅ Saved! Review above then click Continue.";
    window.parent.postMessage({{type:"streamlit:setComponentValue",value:txt}},"*");
  }}else{{
    st.textContent="⚠️ Nothing captured. Try again.";
  }}
}}
pb.onclick=stopRec;
</script></body></html>
"""
    raw = components.html(html_code, height=280)
    if raw and isinstance(raw, str) and len(raw.strip()) > 3:
        st.session_state[result_key] = raw.strip()

    return st.session_state[result_key]


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
DEFAULTS = dict(
    ag2_stage          = "intro",        # intro | project | building | done
    ag2_intro_text     = "",
    ag2_project_text   = "",
    ag2_terms          = [],
    ag2_questions      = [],
    ag2_greeted        = False,
)
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════
st.title("🎙️ Interview Setup — Tell Us About Yourself")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE A: Self Introduction
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.ag2_stage == "intro":

    st.subheader("Step 1 of 2 — Self Introduction")
    st.markdown(
        "The AI will greet you. Click **Start Recording**, introduce yourself "
        "(mention your skills, technologies, tools you work with), then click **Stop & Save**."
    )

    # Greet once
    if not st.session_state.ag2_greeted:
        speak_component(
            "Hello! Welcome to the AI Interview Assistant. "
            "Please introduce yourself. Tell me about your background, "
            "the technologies you work with, and your recent projects.",
            auto=True,
        )
        st.session_state.ag2_greeted = True

    intro_text = voice_recorder_component(
        "🎤 Introduce yourself — mention technologies, tools & projects you've worked on:",
        component_key="self_intro",
    )

    if intro_text:
        st.success("✅ Introduction recorded!")
        st.info(f"**You said:** {intro_text}")

        if st.button("▶ Continue →  Extract Skills", type="primary"):
            with st.spinner("Extracting technical terms from your introduction..."):
                terms = extract_technical_terms(intro_text)
            st.session_state.ag2_intro_text = intro_text
            st.session_state.ag2_terms      = terms

            if terms:
                st.success(f"✅ Found {len(terms)} technical term(s): {', '.join(terms)}")
                time.sleep(1)
                st.session_state.ag2_stage = "building"
            else:
                st.warning(
                    "⚠️ No technical terms detected in your introduction. "
                    "Let's ask about a specific project you've worked on."
                )
                time.sleep(1.5)
                st.session_state.ag2_stage = "project"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STAGE B: Project Follow-up  (only if no terms found in intro)
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.ag2_stage == "project":

    st.subheader("Step 1b — Tell Us About a Project")
    st.markdown(
        "We didn't catch any specific technologies from your intro. "
        "Please describe a **recent project** — the tech stack, tools and frameworks you used."
    )

    speak_component(
        "Could you describe a recent project you worked on? "
        "Please mention the technologies, frameworks and tools you used.",
        auto=True,
    )

    project_text = voice_recorder_component(
        "🎤 Describe a recent project — include tech stack, frameworks, tools:",
        component_key="project_desc",
    )

    if project_text:
        st.success("✅ Project description recorded!")
        st.info(f"**You said:** {project_text}")

        if st.button("▶ Continue →  Extract Skills", type="primary"):
            with st.spinner("Extracting technical terms from your project description..."):
                terms = extract_technical_terms(project_text)

            # Merge with any from intro (usually none here)
            all_terms = list(dict.fromkeys(
                st.session_state.ag2_terms + terms
            ))

            st.session_state.ag2_project_text = project_text
            st.session_state.ag2_terms        = all_terms

            if all_terms:
                st.success(f"✅ Found {len(all_terms)} technical term(s): {', '.join(all_terms)}")
            else:
                st.warning(
                    "Still no specific technical terms found. "
                    "We'll use standard behavioral + general technical questions."
                )
            time.sleep(1)
            st.session_state.ag2_stage = "building"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STAGE C: Build Questions
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.ag2_stage == "building":

    st.subheader("⚙️ Generating Your Interview Questions…")

    terms = st.session_state.ag2_terms
    if terms:
        st.markdown(f"**Technical topics detected:** {', '.join(f'`{t}`' for t in terms)}")
    else:
        st.markdown("No specific technical terms — using general technical questions.")

    with st.spinner("Building personalized question set..."):
        questions = build_question_set(terms, total=10)

    st.session_state.ag2_questions = questions

    # Also write to session state key used by the main interview app
    st.session_state.questions        = questions
    st.session_state.intro_transcript = (
        st.session_state.ag2_intro_text + " " + st.session_state.ag2_project_text
    ).strip()

    # Save to JSON for standalone / integration use
    output = {
        "intro_transcript" : st.session_state.intro_transcript,
        "technical_terms"  : terms,
        "questions"        : questions,
    }
    with open("questions_output.json", "w") as f:
        json.dump(output, f, indent=2)

    st.session_state.ag2_stage = "done"
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STAGE D: Done — show summary + hand off
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.ag2_stage == "done":

    questions = st.session_state.ag2_questions
    terms     = st.session_state.ag2_terms

    speak_component(
        f"Great! I've prepared {len(questions)} interview questions based on your background. "
        "Your interview will now begin. Good luck!",
        auto=True,
    )

    st.success(f"✅ {len(questions)} questions generated and ready!")

    # Summary metrics
    behavioral_topics = {b["topic"] for b in BEHAVIORAL_POOL}
    b_count = sum(1 for q in questions if q.get("topic") in behavioral_topics)
    t_count = len(questions) - b_count

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Questions",      len(questions))
    col2.metric("Behavioral Questions", b_count)
    col3.metric("Technical Questions",  t_count)

    if terms:
        st.markdown(f"**Technical areas covered:** {', '.join(f'`{t}`' for t in terms)}")

    st.markdown("---")
    st.subheader("📋 Generated Questions Preview")

    for i, q in enumerate(questions, 1):
        with st.expander(f"Q{i}: [{q.get('topic','—')}] {q.get('question','')[:80]}…"):
            st.markdown(f"**Topic:** `{q.get('topic','—')}`")
            st.markdown(f"**Question:** {q.get('question','—')}")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.download_button(
            "📥 Download Questions (JSON)",
            data=json.dumps({
                "intro_transcript" : st.session_state.intro_transcript,
                "technical_terms"  : terms,
                "questions"        : questions,
            }, indent=2),
            file_name="questions_output.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_b:
        if st.button("🔄 Start Over", use_container_width=True):
            for k in list(DEFAULTS.keys()):
                del st.session_state[k]
            st.rerun()

    st.info(
        "💡 **Integration tip:** `st.session_state.questions` is now populated. "
        "Switch to your main interview page — it will pick up the questions automatically."
    )

class QuestionGeneratorAgent:
    def __init__(self):
        self.personal_questions = [
            {
                "question": "Tell me about yourself.",
                "term": "Personal",
                "category": "personal",
                "expected_keywords": ["experience", "background", "career", "strengths"]
            },
            {
                "question": "Describe a project you worked on and the impact it had.",
                "term": "Project Experience",
                "category": "personal",
                "expected_keywords": ["project", "impact", "role", "outcome"]
            },
            {
                "question": "What is your greatest strength, and how have you applied it professionally?",
                "term": "Personal",
                "category": "personal",
                "expected_keywords": ["strength", "application", "professional", "example"]
            },
            {
                "question": "Tell me about a challenge you faced and how you resolved it.",
                "term": "Personal",
                "category": "personal",
                "expected_keywords": ["challenge", "solution", "learning", "result"]
            }
        ]

    def generate_questions(self, terms, total_questions=12, include_personal=True):
        personal_questions = self.personal_questions if include_personal else []
        technical_count = max(0, total_questions - len(personal_questions))

        technical_questions = []
        for term in terms[:technical_count]:
            term_text = term if isinstance(term, str) else term.get("term", "")
            keywords = [word for word in term_text.split() if len(word) > 2]
            technical_questions.append({
                "question": f"Explain {term_text} and describe a time you used it in a real project.",
                "term": term_text,
                "category": "technical",
                "expected_keywords": keywords or [term_text]
            })

        questions = technical_questions + personal_questions
        random.shuffle(questions)
        return questions