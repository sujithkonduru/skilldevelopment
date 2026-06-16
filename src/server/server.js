import express from 'express';
import cors from 'cors';
import multer from 'multer';
import Groq from 'groq-sdk';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY || "YOUR_GROQ_API_KEY"
});

function cleanJson(text) {
  let cleaned = text.replace(/<think>.*?<\/think>/gs, '');
  cleaned = cleaned.replace(/```json/g, '');
  cleaned = cleaned.replace(/```/g, '');
  return cleaned.trim();
}

async function groqChat(prompt, maxTokens = 500) {
  const response = await groq.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    messages: [{ role: "user", content: prompt }],
    temperature: 0,
    max_tokens: maxTokens
  });
  return response.choices[0].message.content;
}

app.post('/api/transcribe', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file uploaded' });
    }

    const transcription = await groq.audio.transcriptions.create({
      file: fs.createReadStream(req.file.path),
      model: "whisper-large-v3-turbo"
    });

    fs.unlinkSync(req.file.path);
    res.json({ success: true, transcript: transcription.text });
  } catch (error) {
    console.error('Transcription error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/setup', async (req, res) => {
  try {
    const { transcript } = req.body;

    const termPrompt = `
      Extract ONLY technical terms.
      Correct speech mistakes.
      Example: Quinn -> Qwen
      Return ONLY JSON: {"technical_terms":[]}
      
      Transcript: ${transcript}
    `;
    
    const terms = await groqChat(termPrompt, 300);
    const termsData = JSON.parse(cleanJson(terms));

    const questionPrompt = `
      Generate one interview question for each technical term.
      Return ONLY JSON: {"questions":[{"topic":"","question":""}]}
      
      Terms: ${JSON.stringify(termsData.technical_terms)}
    `;
    
    const questions = await groqChat(questionPrompt, 800);
    const questionsData = JSON.parse(cleanJson(questions));

    res.json({
      success: true,
      technicalTerms: termsData.technical_terms,
      questions: questionsData.questions
    });
  } catch (error) {
    console.error('Setup error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/analyze', async (req, res) => {
  try {
    const { question, topic, answer } = req.body;
    
    const analysisPrompt = `
      You are a technical interviewer. Analyze this answer and provide feedback.

      Topic: ${topic}
      Question: ${question}
      Candidate's Answer: ${answer}

      Provide analysis in JSON format:
      {
        "score": (1-10 integer),
        "strengths": ["strength1", "strength2"],
        "improvements": ["what they should learn/improve"],
        "missing_points": ["what a good answer would include"],
        "learning_resources": ["resource1", "resource2"],
        "summary": "constructive feedback"
      }

      Be helpful and educational.
    `;
    
    const analysis = await groqChat(analysisPrompt, 800);
    const analysisData = JSON.parse(cleanJson(analysis));
    
    res.json({ success: true, analysis: analysisData });
  } catch (error) {
    console.error('Analysis error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/final-report', async (req, res) => {
  try {
    const { answers, analyses } = req.body;
    
    const allAnswersText = answers.map((item, i) => 
      `Q${i+1}: ${item.question}\nA: ${item.answer}\nScore: ${analyses[i].score}/10`
    ).join('\n');

    const finalPrompt = `
      Based on these interview answers, provide a comprehensive analysis:
      
      ${allAnswersText}
      
      Return JSON with:
      {
        "total_score": (average score),
        "strengths_overall": ["strength1", "strength2"],
        "weaknesses_overall": ["weakness1", "weakness2"],
        "recommendations": ["recommendation1", "recommendation2"],
        "hiring_recommendation": "Strong Hire/Hire/Lean Hire/No Hire",
        "detailed_feedback": "paragraph summary"
      }
    `;
    
    const finalAnalysis = await groqChat(finalPrompt, 1000);
    const finalData = JSON.parse(cleanJson(finalAnalysis));
    
    res.json({ success: true, finalReport: finalData });
  } catch (error) {
    console.error('Final report error:', error);
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});