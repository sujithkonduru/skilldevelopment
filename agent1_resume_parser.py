import PyPDF2
import re
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ResumeParserAgent:
    def extract_text_from_pdf(self, pdf_file):
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text

    def extract_technical_terms(self, resume_text):
        prompt = f"""Extract technical terms, skills, and technologies from this resume text.
        Return ONLY a JSON array of strings like: ["Python", "Docker", "REST API"]
        
        Resume: {resume_text[:2000]}"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=500
        )
        
        try:
            import json
            text = response.choices[0].message.content
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except:
            return ["Python", "Cloud", "API", "Database", "DevOps"]

    def rank_terms_by_relevance(self, terms, resume_text):
        ranked = []
        for term in terms[:10]:
            count = resume_text.lower().count(term.lower())
            ranked.append({"term": term, "relevance_score": min(count * 10, 100)})
        return sorted(ranked, key=lambda x: x['relevance_score'], reverse=True)