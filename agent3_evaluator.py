import json, os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

class AnswerEvaluatorAgent:
    def capture_voice_answer(self):
        return "This is a sample answer about the technical topic. It demonstrates understanding of key concepts and best practices."

    def evaluate_answer(self, question_data, answer):
        prompt = f"""Evaluate this technical interview answer:
        
        Question: {question_data['question']}
        Expected Keywords: {', '.join(question_data['expected_keywords'])}
        Answer: {answer}
        
        Return ONLY valid JSON:
        {{
            "total_score": 0,
            "keyword_score": 0.8,
            "confidence_score": 0.7,
            "feedback": "Good explanation...",
            "missing_keywords": ["concept1"]
        }}"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=500
        )
        
        try:
            text = response.choices[0].message.content
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            result["term"] = question_data["term"]
            return result
        except:
            return {
                "term": question_data["term"],
                "total_score": 70,
                "keyword_score": 0.7,
                "confidence_score": 0.7,
                "feedback": "Answer recorded.",
                "missing_keywords": []
            }