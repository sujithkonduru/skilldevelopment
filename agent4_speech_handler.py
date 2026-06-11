# agent4_speech_handler.py

import streamlit as st
from groq import Groq
import tempfile
import os
import speech_recognition as sr
import pyttsx3
import threading
from pathlib import Path

# Initialize Groq client
client = Groq(api_key="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")

class SpeechHandlerAgent:
    """Agent 4: Handles text-to-speech and speech-to-text operations"""
    
    def __init__(self):
        # Initialize speech recognition (using speech_recognition, not streamlit)
        self.recognizer = sr.Recognizer()
        
        # Initialize TTS engine
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.9)
            
            # Try to set a better voice
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
        except Exception as e:
            print(f"TTS initialization error: {e}")
            self.tts_engine = None
    
    def speak_question_local(self, text: str):
        """Speak question using local TTS (pyttsx3)"""
        if self.tts_engine:
            try:
                def _speak():
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                
                thread = threading.Thread(target=_speak)
                thread.start()
                thread.join(timeout=10)
                return True
            except Exception as e:
                print(f"TTS Error: {e}")
                return False
        return False
    
    def speak_question_browser(self, question_text: str, question_idx: int):
        """Speak question using browser's speech synthesis (tries autoplay; shows lightweight fallback button if blocked)."""
        safe_text = (
            question_text
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("\n", "\\n")
            .replace('"', '\\"')
        )
        html = f"""
        <div id="speech_container_{question_idx}" style="position:relative;">
          <div id="speech_msg_{question_idx}" style="display:none; position:absolute; inset:0; align-items:center; justify-content:center;">
            <button id="enable_btn_{question_idx}" style="padding:10px 16px; font-size:14px; border-radius:8px; cursor:pointer;">
              🔊 Click to enable audio
            </button>
          </div>
        </div>
        <script>
        (function() {{
            const text = `{safe_text}`;
            const container = document.getElementById("speech_container_{question_idx}");
            const enableDiv = document.getElementById("speech_msg_{question_idx}");
            const enableBtn = document.getElementById("enable_btn_{question_idx}");

            function speak() {{
                if (!window.speechSynthesis) return false;
                window.speechSynthesis.cancel();
                const msg = new SpeechSynthesisUtterance(text);
                msg.rate = 0.95;
                msg.pitch = 1.0;
                msg.lang = 'en-US';
                const voices = window.speechSynthesis.getVoices();
                if (voices.length > 0) {{
                    const usVoice = voices.find(v => v.lang.includes('en-US'));
                    if (usVoice) msg.voice = usVoice;
                    else msg.voice = voices[0];
                }}
                try {{
                    window.speechSynthesis.speak(msg);
                    return true;
                }} catch (e) {{
                    return false;
                }}
            }}

            // Try to speak immediately
            const played = speak();

            // If not speaking within 600ms (autoplay likely blocked), show small enable button
            setTimeout(() => {{
                if (!window.speechSynthesis.speaking) {{
                    enableDiv.style.display = "flex";
                    enableDiv.style.alignItems = "center";
                    enableDiv.style.justifyContent = "center";
                    enableDiv.style.background = "transparent";
                    enableBtn.onclick = () => {{
                        speak();
                        enableDiv.style.display = "none";
                    }};
                }}
            }}, 600);
        }})();
        </script>
        """
        # give enough height so script runs reliably
        st.components.v1.html(html, height=120, scrolling=False)

        # lightweight replay control
        if st.button("🔊 Replay Question", key=f"replay_{question_idx}", use_container_width=True):
            st.components.v1.html(html, height=120, scrolling=False)
    
    def record_and_transcribe_microphone(self, question_idx: int, timeout: int = 10) -> str:
        """Record voice answer using microphone and transcribe with Google Speech Recognition"""
        st.markdown("### 🎤 Record your answer using Microphone")
        
        if st.button("🎙️ Start Recording", key=f"start_rec_{question_idx}", type="primary"):
            with st.spinner("Listening... Please speak now:"):
                try:
                    with sr.Microphone() as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        st.info("🎤 Recording... Speak clearly!")
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=30)
                        st.info("🔄 Transcribing...")
                        text = self.recognizer.recognize_google(audio)
                        st.success(f"✅ Transcribed: {text}")
                        return text
                except sr.WaitTimeoutError:
                    st.error("Timeout: No speech detected")
                    return "[No answer provided - Timeout]"
                except sr.UnknownValueError:
                    st.error("Could not understand audio - Please speak clearly")
                    return "[Could not understand audio - Please speak clearly]"
                except sr.RequestError as e:
                    st.error(f"Service error: {e}")
                    return f"[Speech recognition service error: {e}]"
                except Exception as e:
                    st.error(f"Microphone error: {e}")
                    return f"[Microphone error: {e}]"
        return None
    
    def record_and_transcribe_groq(self, question_idx: int) -> str:
        """Record voice answer using file upload and transcribe with Groq Whisper"""
        st.markdown("### 🎤 Record your answer")
        st.info("Click the microphone below, record your answer, then click 'Submit Answer'")
        
        audio_file = st.audio_input(
            "Click mic to record your answer",
            key=f"audio_rec_{question_idx}"
        )

        if audio_file is None:
            return None

        st.audio(audio_file, format="audio/wav")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📤 Submit Answer", key=f"submit_audio_{question_idx}", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    data = audio_file.getbuffer() if hasattr(audio_file, "getbuffer") else audio_file.read()
                    tmp.write(data)
                    tmp_path = tmp.name

                try:
                    with st.spinner("🎙️ Converting speech to text using Groq Whisper..."):
                        with open(tmp_path, "rb") as f:
                            transcript = client.audio.transcriptions.create(
                                file=(tmp_path, f.read()),
                                model="whisper-large-v3-turbo",
                                response_format="text"
                            )

                        answer_text = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))
                        # persist transcript + submitted flag in session_state so agent1.py can act only after submit
                        st.session_state[f"transcript_{question_idx}"] = answer_text
                        st.session_state[f"submitted_{question_idx}"] = True

                        st.success(f"✅ Transcribed: {answer_text}")
                        return answer_text
                except Exception as e:
                    st.error(f"Transcription error: {e}")
                    return None
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

        return None
    
    def record_and_transcribe(self, question_idx: int, method: str = "groq") -> str:
        """Main method to record and transcribe - choose method: 'groq' or 'microphone'"""
        if method == "groq":
            return self.record_and_transcribe_groq(question_idx)
        else:
            return self.record_and_transcribe_microphone(question_idx)
    
    def speak_question(self, question_text: str, question_idx: int, method: str = "browser"):
        """Main method to speak question - choose method: 'browser' or 'local'"""
        if method == "local":
            self.speak_question_local(question_text)
        else:
            self.speak_question_browser(question_text, question_idx)
    
    def speak_feedback(self, feedback_text: str):
        """Speak feedback using local TTS"""
        if self.tts_engine:
            try:
                self.tts_engine.say(feedback_text)
                self.tts_engine.runAndWait()
                return True
            except Exception as e:
                print(f"Feedback TTS Error: {e}")
                return False
        return False
    
    def get_audio_device_info(self):
        """Get information about available microphones"""
        try:
            microphones = sr.Microphone.list_microphone_names()
            return microphones
        except Exception as e:
            return [f"Error: {e}"]

    def save_audio_bytes(self, audio_bytes, question_idx, audio_dir: Path, ext=".wav"):
        output_path = audio_dir / f"personal_answer_{question_idx}{ext}"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        return output_path

    def save_audio_file(self, uploaded_file, question_idx, audio_dir: Path):
        ext = Path(uploaded_file.name).suffix or ".wav"
        output_path = audio_dir / f"personal_answer_{question_idx}{ext}"
        with open(output_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return output_path

    def transcribe_audio_file(self, audio_path):
        """Transcribe audio using Google Speech Recognition"""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 4000
        
        try:
            with sr.AudioFile(str(audio_path)) as source:
                audio = recognizer.record(source)
            
            try:
                transcript = recognizer.recognize_google(audio, language='en-US')
                return transcript
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                return ""
        except Exception as e:
            return ""