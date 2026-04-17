import requests
import json
from config.settings import Config
from db.chroma_store import ChromaMemory
import uuid

class LLMReportingService:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.memory = ChromaMemory()

    def generate_report(self, fusion_data, verification_data):
        prompt = f"""
        You are an official Carbon Market Auditor. Generate a formal 2-paragraph certification report based on this data:
        - AWD Practiced: {fusion_data.get('awd_status')}
        - Methane Detected: {fusion_data.get('methane_value')} kg/ha
        - Verification Confidence: {verification_data.get('confidence_score') * 100}%
        - Auditor Note: {verification_data.get('explanation')}
        
        Return ONLY the formal text of the report.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free", # Free tier OpenRouter model for hackathons
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            report_text = response.json()['choices'][0]['message']['content']
            
            # Save to Vector DB
            report_id = str(uuid.uuid4())
            self.memory.save_report(
                report_id=report_id, 
                text=report_text, 
                metadata={"location": str(fusion_data.get("location"))}
            )
            
            return {
                "report_id": report_id,
                "certificate_text": report_text
            }
        except Exception as e:
            return {"error": f"LLM Generation failed: {str(e)}"}