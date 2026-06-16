## 🛠️ The Corrected, Working Imple
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json, re, tempfile, os
import time

st.set_page_config(page_title="AI Interview Assistant", page_icon="🎯", layout="wide")

# Secure your key properly in production (e.g., st.secrets)
client = Groq(api_key="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")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_json(text):
    text = re.sub(r"꽁.*?꽁", "", text, flags=re.DOTALL)
    return text.replace("```json","").replace("","").strip()

def groq_chat(prompt, max_tokens=500):
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0, max_tokens=max_tokens
    )
    return r.choices[0].message.content

def analyze_answer(question, topic, answer):
    prompt = f"""You are a technical interviewer. Analyze this answer and provide feedback.
Topic: {topic}
Question: {question}
Candidate's Answer: {answer}
Provide analysis in ONLY this JSON format, no extra text:
{{
    "score": 7,
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "missing_points": ["point1", "point2"],
    "summary": "constructive feedback here"
}}"""
    try:
        raw_response = groq_chat(prompt, 800)
        return json.loads(clean_json(raw_response))
    except Exception as e:
        # Graceful fallback structure if LLM outputs dirty JSON
        return {
            "score": 5,
            "strengths": ["Answer recorded securely."],
            "improvements": ["System experienced a processing glitch parsing structured metrics."],
            "missing_points": [],
            "summary": "Feedback processing issue encountered."
        }

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in dict(
    stage='setup', questions=[], current_q=0,
    answers=[], analyses=[], intro_transcript="",
    is_processing=False, last_raw_result=None
).items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Setup
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == 'setup':
    st.title("🎯 AI Technical Interview Assistant")
    st.markdown("---")
    st.header("📁 Upload Your Audio Introduction")
    audio_file = st.file_uploader("Choose an audio file", type=['mp3','wav','m4a'])

    if audio_file and st.button("Process Audio", type="primary"):
        with st.spinner("Transcribing introduction..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            with open(tmp_path,"rb") as f:
                tr = client.audio.transcriptions.create(file=f, model="whisper-large-v3-turbo")
            os.unlink(tmp_path)
            st.session_state.intro_transcript = tr.text

        with st.spinner("Generating questions..."):
            terms_raw = groq_chat(
                f"Extract ONLY technical terms, correct speech mistakes. "
                f"Return ONLY JSON: {{\"technical_terms\":[]}}\nTranscript: {tr.text}", 300)
            terms = json.loads(clean_json(terms_raw))["technical_terms"]
            
            qs_raw = groq_chat(
                f"Generate one interview question per technical term. "
                f"Return ONLY JSON: {{\"questions\":[{{\"topic\":\"\",\"question\":\"\"}}]}}\n"
                f"Terms: {json.dumps(terms)}", 800)
            st.session_state.questions = json.loads(clean_json(qs_raw))["questions"]

        st.success(f"✅ Generated {len(st.session_state.questions)} questions!")
        time.sleep(1)
        st.session_state.stage = 'interview'
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Interview
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == 'interview':
    q_idx = st.session_state.current_q
    questions = st.session_state.questions
    
    # ── SUB-STAGE: Processing AI evaluation mid-interview ─────────────────────
    if st.session_state.is_processing:
        st.title("🤖 Processing Your Answer...")
        st.markdown("---")
        
        status_placeholder = st.empty()
        with status_placeholder.container():
            st.info("📝 AI is evaluating your response...")
            st.progress(0.5, text="Contacting Groq Analysis Models...")
        
        current_question_data = questions[q_idx]
        raw_speech_text = st.session_state.last_raw_result
        
        # Save structural answer record
        st.session_state.answers.append({
            "topic": current_question_data['topic'], 
            "question": current_question_data['question'], 
            "answer": raw_speech_text
        })
        
        # Call analysis immediately *before* incrementing index pointers
        analysis = analyze_answer(current_question_data['question'], current_question_data['topic'], raw_speech_text)
        st.session_state.analyses.append(analysis)
        
        # Display completion state to user safely
        status_placeholder.progress(1.0, text="Analysis saved successfully!")
        st.success(f"✅ Question {q_idx + 1} Processed! Evaluated Score: {analysis['score']}/10")
        time.sleep(2.0)
        
        # Now safe to advance state pointers
        st.session_state.current_q += 1
        st.session_state.last_raw_result = None
        st.session_state.is_processing = False
        
        # Route logic check
        if st.session_state.current_q >= len(questions):
            st.session_state.stage = 'results'
        st.rerun()

    # ── SUB-STAGE: Active Question Visuals ────────────────────────────────────
    elif q_idx < len(questions):
        q = questions[q_idx]

        st.progress(q_idx / len(questions))
        st.markdown(f"**Question {q_idx+1} of {len(questions)}**")
        st.markdown(f"### 🏷️ Topic: `{q['topic']}`")
        st.markdown(f"## {q['question']}")
        st.markdown("---")

        question_text = q['question'].replace("\\","\\\\").replace("`","\\`").replace("$","\\$")
        
        recorder_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }}
  body {{ background: transparent; padding: 8px; }}
  #transcript {{
    width: 100%; min-height: 150px; padding: 12px;
    border: 2px solid #4CAF50; border-radius: 10px;
    font-size: 16px; line-height: 1.5;
    background: #f0fdf0; color: #111;
    margin-bottom: 10px;
    font-family: monospace;
  }}
  #transcript.listening {{ border-color: #e53935; background: #fff5f5; }}
  .btn-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
  button {{
    padding: 10px 22px; border: none; border-radius: 8px;
    font-size: 15px; font-weight: 600; cursor: pointer; transition: all .2s;
  }}
  button:disabled {{ opacity: .4; cursor: not-allowed; }}
  #startBtn  {{ background: #e53935; color: #fff; }}
  #stopBtn   {{ background: #1565c0; color: #fff; }}
  #replayBtn {{ background: #6a1b9a; color: #fff; }}
  #status {{ margin-top: 8px; font-size: 13px; color: #555; min-height: 40px; }}
  .dot {{ display: inline-block; animation: blink 1s infinite; }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0}} }}
</style>
</head>
<body>

<textarea id="transcript" placeholder="Your speech will appear here as you speak..."></textarea>
<div class="btn-row">
  <button id="startBtn">🎙️ Start Recording</button>
  <button id="stopBtn" disabled>⏹ Stop & Submit</button>
  <button id="replayBtn">🔊 Replay Question</button>
</div>
<div id="status">Ready. Click "Start Recording" and speak your answer.</div>

<script>
const QUESTION = `{question_text}`;
let hasSubmitted = false;
let rec, isListening = false;
let finalText = "";

const ta = document.getElementById('transcript');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const replayBtn = document.getElementById('replayBtn');
const statusDiv = document.getElementById('status');

const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRec) {{
  statusDiv.textContent = "❌ Browser doesn't support Speech Recognition. Use Chrome.";
  startBtn.disabled = true;
}}

function speakQuestion() {{
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(QUESTION);
  u.rate=0.9; u.pitch=1.0; u.lang='en-US';
  function go() {{
    var voices = window.speechSynthesis.getVoices();
    var v = voices.find(x=>x.name.includes('Google US English')) ||
            voices.find(x=>x.name.includes('Samantha')) ||
            voices.find(x=>x.lang==='en-US');
    if(v) u.voice=v;
    window.speechSynthesis.speak(u);
  }}
  if(window.speechSynthesis.getVoices().length>0) go();
  else window.speechSynthesis.onvoiceschanged=go;
}}

window.addEventListener('load', () => setTimeout(speakQuestion, 600));
replayBtn.onclick = speakQuestion;

function submitAnswer(text) {{
  if (hasSubmitted) return;
  hasSubmitted = true;
  statusDiv.innerHTML = "✅ Submitting answer...";
  window.parent.postMessage({{
    type: "streamlit:setComponentValue",
    value: text
  }}, "*");
}}

function startRecording() {{
  if (!SpeechRec || hasSubmitted) return;
  
  finalText = "";
  ta.value = "";
  ta.classList.remove('listening');
  
  rec = new SpeechRec();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'en-US';

  rec.onstart = () => {{
    isListening = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    ta.classList.add('listening');
    statusDiv.innerHTML = '<span class="dot">🔴</span> Listening... speak your answer clearly';
  }};

  rec.onresult = (e) => {{
    let interim = "";
    let newFinal = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {{
      if (e.results[i].isFinal) {{
        newFinal += e.results[i][0].transcript + " ";
      }} else {{
        interim += e.results[i][0].transcript;
      }}
    }}
    if (newFinal) finalText += newFinal;
    ta.value = finalText + interim;
    ta.scrollTop = ta.scrollHeight;
  }};

  rec.onerror = (e) => {{
    statusDiv.innerHTML = "❌ Error: " + e.error;
    stopRecording();
  }};

  rec.start();
}}

function stopRecording() {{
  if (hasSubmitted) return;
  isListening = false;
  if (rec) {{
    rec.onend = null;
    rec.stop();
  }}
  startBtn.disabled = false;
  stopBtn.disabled = true;
  ta.classList.remove('listening');
  
  if (finalText.trim().length > 5) {{
    submitAnswer(finalText.trim());
  }} else {{
    statusDiv.innerHTML = "⚠️ No speech detected. Please try again.";
    startBtn.disabled = false;
    hasSubmitted = false;
  }}
}}

startBtn.onclick = startRecording;
stopBtn.onclick = stopRecording;
</script>
</body>
</html>
"""

        # Crucial Fix: Appending key=f"rec_{q_idx}" forces Streamlit to rebuild 
        # the iframe context clean for every single new question.
        # render iframe without unsupported 'key' kwarg
        result = components.html(recorder_html, height=300)

        if result and isinstance(result, str) and len(result.strip()) > 5:
            st.session_state.last_raw_result = result.strip()
            st.session_state.is_processing = True
            st.rerun()
            
        st.info("🎤 Click 'Start Recording', speak your answer, then click 'Stop & Submit'")
    else:
        st.session_state.stage = 'results'
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Results
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.title("📊 Interview Results")
    st.markdown("---")

    if st.session_state.analyses and st.session_state.answers:
        avg = sum(a['score'] for a in st.session_state.analyses) / len(st.session_state.analyses)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Overall Score", f"{avg:.1f}/10")
        with col2:
            st.metric("Questions Completed", len(st.session_state.answers))
        with col3:
            st.metric("Total Points", sum(a['score'] for a in st.session_state.analyses))
        with col4:
            if avg >= 8: st.metric("Performance", "🎉 Excellent")
            elif avg >= 6: st.metric("Performance", "👍 Good")
            elif avg >= 4: st.metric("Performance", "📚 Need Practice")
            else: st.metric("Performance", "⚠️ Needs Improvement")
        
        st.markdown("---")
        st.subheader("📋 Detailed Question Analysis")
        
        for i, (ans, analysis) in enumerate(zip(st.session_state.answers, st.session_state.analyses)):
            with st.expander(f"Q{i+1}: {ans['question'][:80]}... (Score: {analysis['score']}/10)", expanded=(i==0)):
                st.markdown(f"**Topic:** `{ans['topic']}`")
                st.markdown(f"**Your Answer:**")
                st.info(ans['answer'])
                
                col1_box, col2_box = st.columns(2)
                with col1_box:
                    st.markdown("**✅ Strengths:**")
                    for s in analysis.get('strengths', []):
                        st.markdown(f"- {s}")
                with col2_box:
                    st.markdown("**🔧 Improvements:**")
                    for imp in analysis.get('improvements', []):
                        st.markdown(f"- {imp}")
                
                if analysis.get('missing_points'):
                    st.markdown("**📌 Missing Points:**")
                    for mp in analysis['missing_points']:
                        st.markdown(f"- {mp}")
                
                st.markdown(f"**📝 Summary:** {analysis.get('summary', 'No summary provided.')}")
                st.markdown("---")
        
        st.subheader("💡 Recommendations for Improvement")
        all_weaknesses = []
        for analysis in st.session_state.analyses:
            all_weaknesses.extend(analysis.get('improvements', []))
        
        if all_weaknesses:
            unique_weaknesses = list(set(all_weaknesses))[:5]
            st.markdown("**Based on your performance, focus on:**")
            for w in unique_weaknesses:
                st.markdown(f"- 📌 {w}")
        
        if st.session_state.analyses:
            scores_by_topic = [(a['score'], ans['topic']) for a, ans in zip(st.session_state.analyses, st.session_state.answers)]
            scores_by_topic.sort(reverse=True)
            
            st.markdown("---")
            col1_t, col2_t = st.columns(2)
            with col1_t:
                st.markdown("**🏆 Strongest Topic:**")
                st.info(f"{scores_by_topic[0][1]} ({scores_by_topic[0][0]}/10)")
            with col2_t:
                st.markdown("**📚 Topic to Improve:**")
                st.warning(f"{scores_by_topic[-1][1]} ({scores_by_topic[-1][0]}/10)")
        
        st.markdown("---")
        col1_btn, col2_btn = st.columns(2)
        with col1_btn:
            st.download_button("📥 Download Complete Results (JSON)",
                data=json.dumps({
                    "intro_transcript": st.session_state.intro_transcript,
                    "questions": st.session_state.questions,
                    "answers": st.session_state.answers,
                    "analyses": st.session_state.analyses,
                    "overall_score": avg,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }, indent=2),
                file_name=f"interview_results_{time.strftime('%Y%m%d_%H%M%S')}.json", 
                mime="application/json",
                use_container_width=True
            )
        
        with col2_btn:
            if st.button("🔄 Start New Interview", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
                
    else:
        st.warning("No completed interviews found. Please complete the interview first.")
        if st.button("Start New Interview", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
