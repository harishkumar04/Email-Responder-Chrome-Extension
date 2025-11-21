from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import time
import hashlib
import logging
from prometheus_client import Counter, Histogram, generate_latest

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Email Response Generator", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Models
class EmailRequest(BaseModel):
    email_content: str
    sender_name: Optional[str] = None
    context: Optional[str] = None

class EmailResponse(BaseModel):
    response: str
    confidence: float
    source: str
    timestamp: str

# Database setup
def init_db():
    conn = sqlite3.connect('email_responses.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_hash TEXT UNIQUE,
            response TEXT,
            confidence REAL,
            source TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Cache
response_cache = {}
CACHE_TTL = 1800  # 30 minutes

# AI Configuration
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if AI_ENABLED and GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        logger.info("AI enabled with Gemini")
    except Exception as e:
        logger.error(f"AI initialization failed: {e}")
        AI_ENABLED = False
else:
    logger.info("AI disabled or no API key")
    AI_ENABLED = False

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Email Response Generator started")

@app.get("/")
async def root():
    return {"message": "Email Response Generator API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/generate-response", response_model=EmailResponse)
async def generate_response(request: EmailRequest):
    start_time = time.time()
    REQUEST_COUNT.labels(method="POST", endpoint="/generate-response").inc()
    
    try:
        # Create email hash for caching
        email_hash = hashlib.md5(request.email_content.encode()).hexdigest()
        
        # Check cache first
        current_time = time.time()
        if email_hash in response_cache:
            cached_response, cache_time = response_cache[email_hash]
            if current_time - cache_time < CACHE_TTL:
                REQUEST_DURATION.observe(time.time() - start_time)
                return EmailResponse(**cached_response)
        
        # Generate AI response if enabled
        if AI_ENABLED:
            try:
                email_preview = request.email_content[:500]
                context_prompt = f"""
You are a professional email assistant. Analyze this email and write a thoughtful, appropriate response:

Email Content: {email_preview}
Sender: {request.sender_name or 'Unknown'}
Context: {request.context or 'General business communication'}

Guidelines:
- Be professional and courteous
- Match the tone of the original email
- Keep response concise but complete
- Address key points mentioned
- End with appropriate next steps if needed

Write only the email response, no explanations:
"""
                
                response = model.generate_content(context_prompt)
                ai_response = response.text.strip()
                
                result = {
                    "response": ai_response,
                    "confidence": 0.9,
                    "source": "AI Generated",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Cache the response
                response_cache[email_hash] = (result, current_time)
                
                # Save to database
                save_to_db(email_hash, result)
                
                REQUEST_DURATION.observe(time.time() - start_time)
                return EmailResponse(**result)
                
            except Exception as e:
                logger.error(f"AI generation failed: {e}")
        
        # Fallback response
        fallback_response = generate_fallback_response(request.email_content)
        result = {
            "response": fallback_response,
            "confidence": 0.7,
            "source": "Template",
            "timestamp": datetime.now().isoformat()
        }
        
        response_cache[email_hash] = (result, current_time)
        save_to_db(email_hash, result)
        
        REQUEST_DURATION.observe(time.time() - start_time)
        return EmailResponse(**result)
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

def generate_fallback_response(email_content: str) -> str:
    """Generate a contextual fallback response"""
    content_lower = email_content.lower()
    
    if any(word in content_lower for word in ['meeting', 'schedule', 'calendar']):
        return "Thank you for reaching out. I'll check my calendar and get back to you with available times shortly."
    elif any(word in content_lower for word in ['opportunity', 'position', 'job']):
        return "Thank you for sharing this opportunity. I'm interested in learning more and will review the details to provide you with thoughtful feedback."
    elif any(word in content_lower for word in ['urgent', 'asap', 'immediately']):
        return "I understand this is urgent. I'm reviewing your message now and will respond with the requested information as quickly as possible."
    else:
        return "Thank you for your email. I've received your message and will review it carefully to provide you with a comprehensive response."

def save_to_db(email_hash: str, result: dict):
    """Save response to database"""
    try:
        conn = sqlite3.connect('email_responses.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO responses 
            (email_hash, response, confidence, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            email_hash,
            result["response"],
            result["confidence"],
            result["source"],
            result["timestamp"]
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database save failed: {e}")

@app.get("/stats")
async def get_stats():
    """Get API usage statistics"""
    try:
        conn = sqlite3.connect('email_responses.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM responses")
        total_responses = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM responses GROUP BY source")
        source_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_responses": total_responses,
            "source_breakdown": source_stats,
            "cache_size": len(response_cache),
            "ai_enabled": AI_ENABLED
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": "Could not fetch stats"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
