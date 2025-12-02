import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from prometheus_client import (Counter, Histogram, generate_latest,
                               start_http_server)
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("email_responder")

# Prometheus metrics
email_requests_total = Counter(
    "email_requests_total", "Total email requests", ["response_type", "source"]
)
response_time_seconds = Histogram(
    "response_time_seconds", "Response generation time", ["method"]
)
cache_operations_total = Counter(
    "cache_operations_total", "Cache operations", ["operation", "result"]
)
ai_api_calls_total = Counter("ai_api_calls_total", "AI API calls", ["model", "status"])
database_operations_total = Counter(
    "database_operations_total", "Database operations", ["operation"]
)

load_dotenv()

response_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30 minutes


def get_cache_key(email_content: str, response_type: str) -> str:
    """Generate cache key"""
    content = f"{email_content.lower().strip()}:{response_type}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_response(email_content: str, response_type: str) -> Optional[str]:
    """Get cached response if available"""
    key = get_cache_key(email_content, response_type)
    if key in response_cache:
        cached_item = response_cache[key]
        if time.time() - cached_item["timestamp"] < CACHE_TTL:
            cache_operations_total.labels(operation="get", result="hit").inc()
            logger.info(f"Cache HIT for key: {key[:8]}...")
            return cached_item["response"]
        else:
            cache_operations_total.labels(operation="get", result="expired").inc()
            logger.info(f"Cache EXPIRED for key: {key[:8]}...")
            del response_cache[key]
    cache_operations_total.labels(operation="get", result="miss").inc()
    return None


def cache_response(email_content: str, response_type: str, response: str):
    """Cache a response"""
    key = get_cache_key(email_content, response_type)
    response_cache[key] = {"response": response, "timestamp": time.time()}
    cache_operations_total.labels(operation="set", result="success").inc()
    logger.info(f"Cached response for key: {key[:8]}...")


QUICK_PATTERNS = {
    # Temporarily disabled to force AI responses
    # "thank you": "You're welcome! Happy to help.",
    # "thanks": "You're welcome!",
    # "meeting": "I'll check my calendar and get back to you with available times.",
    # "urgent": "I understand this is urgent. Reviewing now and will respond shortly.",
    # "follow up": "Thank you for following up. I'll provide an update soon.",
    # "schedule": "Let me check my availability and propose some meeting times.",
}


def get_instant_response(email_content: str) -> Optional[str]:
    """Check for patterns that can get instant responses"""
    email_lower = email_content.lower()
    for pattern, response in QUICK_PATTERNS.items():
        if pattern in email_lower:
            return response
    return None


try:
    import google.generativeai as genai

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-pro")
        AI_ENABLED = True
        print("✅ Gemini AI initialized successfully")
    else:
        AI_ENABLED = False
        print("⚠️  Gemini API key not configured - using fallback responses")
except ImportError:
    AI_ENABLED = False
    print("⚠️  google-generativeai not installed - using fallback responses")

app = FastAPI(title="Email Response Generator", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics endpoint for Prometheus
@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def init_db():
    database_operations_total.labels(operation="init").inc()
    db_path = os.path.join(BASE_DIR, "email_responses.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_responses (
            id INTEGER PRIMARY KEY,
            original_email TEXT,
            generated_response TEXT,
            response_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS response_templates (
            id INTEGER PRIMARY KEY,
            name TEXT,
            template TEXT,
            category TEXT
        )
    """
    )

    # Add some default templates
    templates = [
        (
            "Professional Thank You",
            "Thank you for your email. I appreciate you reaching out about {topic}. I'll review this and get back to you within 24 hours.",
            "professional",
        ),
        (
            "Meeting Request",
            "Thank you for the meeting request. I'm available {availability}. Please let me know what works best for you.",
            "scheduling",
        ),
        (
            "Quick Acknowledgment",
            "Thanks for your message! I've received it and will respond shortly.",
            "quick",
        ),
        (
            "Follow Up",
            "Following up on our previous conversation about {topic}. Please let me know if you need any additional information.",
            "followup",
        ),
    ]

    for name, template, category in templates:
        conn.execute(
            "INSERT OR IGNORE INTO response_templates (name, template, category) VALUES (?, ?, ?)",
            (name, template, category),
        )
    conn.commit()
    conn.close()


init_db()


class EmailRequest(BaseModel):
    email_content: str
    sender: Optional[str] = None
    subject: Optional[str] = None
    response_type: str = "professional"


class EmailResponse(BaseModel):
    generated_response: str
    confidence: float
    response_type: str
    suggestions: List[str] = []
    processing_time: Optional[float] = None
    cached: bool = False


class Template(BaseModel):
    id: Optional[int] = None
    name: str
    template: str
    category: str


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return templates.TemplateResponse(
        "index.html", {"request": request, "current_time": current_time}
    )


@app.get("/api")
def api_root():
    return {
        "message": "Email Response Generator API - OPTIMIZED",
        "status": "running",
        "optimizations": [
            "Response caching (30min TTL)",
            "Pattern matching for instant responses",
            "Shorter AI prompts",
            "Performance timing",
        ],
        "cache_size": len(response_cache),
        "endpoints": ["/generate-response", "/templates", "/history", "/cache/clear"],
    }


@app.get("/cache/clear")
def clear_cache():
    """Clear the response cache"""
    global response_cache
    response_cache = {}
    return {"message": "Cache cleared successfully", "cache_size": 0}


@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics"""
    return {
        "cache_size": len(response_cache),
        "ttl_seconds": CACHE_TTL,
        "cached_keys": list(response_cache.keys())[:5],  # Show first 5 keys
    }


@app.post("/generate-response", response_model=EmailResponse)
async def generate_response(request: EmailRequest):
    """Generate an AI-powered email response - OPTIMIZED VERSION"""

    start_time = time.time()

    try:
        # OPTIMIZATION 1: Check cache first (fastest - ~0.001s)
        cached_response = get_cached_response(
            request.email_content, request.response_type
        )
        if cached_response:
            end_time = time.time()
            return EmailResponse(
                generated_response=cached_response,
                confidence=0.95,
                response_type=request.response_type,
                suggestions=["Cached response - instant delivery"],
                processing_time=end_time - start_time,
                cached=True,
            )

        # OPTIMIZATION 2: Check for instant pattern matches (very fast - ~0.01s)
        instant_response = get_instant_response(request.email_content)
        if instant_response:
            cache_response(
                request.email_content, request.response_type, instant_response
            )
            end_time = time.time()
            return EmailResponse(
                generated_response=instant_response,
                confidence=0.85,
                response_type="instant",
                suggestions=["Pattern-matched response"],
                processing_time=end_time - start_time,
                cached=False,
            )

        # OPTIMIZATION 3: Use AI with improved prompt (1-2s)
        if AI_ENABLED:
            try:
                # Improved prompt for better, more contextual responses
                email_preview = request.email_content[:500]  # Use more context

                # Determine context and tone
                context_prompt = f"""
You are a professional email assistant. Analyze this email and write a thoughtful, appropriate response:

EMAIL TO RESPOND TO:
{email_preview}

RESPONSE REQUIREMENTS:
- Tone: {request.response_type}
- Be specific and relevant to the email content
- Include actionable next steps when appropriate
- Keep it concise but complete (2-4 sentences)
- Sound natural and human-like
- Address the main points raised

Write only the email response, no explanations:"""

                ai_start = time.time()
                response = model.generate_content(context_prompt)
                ai_end = time.time()

                generated_response = response.text.strip()

                # Clean up the response
                if generated_response.startswith('"') and generated_response.endswith(
                    '"'
                ):
                    generated_response = generated_response[1:-1]

                confidence = 0.95

                # Cache the AI response for future use
                cache_response(
                    request.email_content, request.response_type, generated_response
                )

                print(f"✅ AI response generated in {ai_end - ai_start:.2f}s")
            except Exception as ai_error:
                print(f"❌ AI generation failed: {ai_error}")
                generated_response = generate_fallback_response(request.email_content)
                confidence = 0.5
        else:
            generated_response = generate_fallback_response(request.email_content)
            confidence = 0.7
            print("ℹ️  Using fallback response (AI not available)")

        # Quick response type detection
        email_lower = request.email_content.lower()
        if "meeting" in email_lower or "schedule" in email_lower:
            response_type = "scheduling"
        elif "thank" in email_lower:
            response_type = "acknowledgment"
        elif "urgent" in email_lower:
            response_type = "urgent"
        else:
            response_type = request.response_type

        # Store in database (keep this for history)
        try:
            db_path = os.path.join(BASE_DIR, "email_responses.db")
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO email_responses (original_email, generated_response, response_type) VALUES (?, ?, ?)",
                (request.email_content, generated_response, response_type),
            )
            conn.commit()
            conn.close()
        except Exception as db_error:
            print(f"⚠️  Database error (non-critical): {db_error}")
        suggestions = ["Adjust tone as needed", "Add timeline if applicable"]

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"🚀 Total processing time: {processing_time:.2f}s")

        return EmailResponse(
            generated_response=generated_response,
            confidence=confidence,
            response_type=response_type,
            suggestions=suggestions,
            processing_time=processing_time,
            cached=False,
        )

    except Exception as e:
        print(f"Error in generate_response: {str(e)}")
        # Fallback response
        fallback_response = generate_fallback_response(request.email_content)

        end_time = time.time()
        processing_time = end_time - start_time

        return EmailResponse(
            generated_response=fallback_response,
            confidence=0.5,
            response_type="general",
            suggestions=["AI service temporarily unavailable"],
            processing_time=processing_time,
            cached=False,
        )


def generate_fallback_response(email_content: str) -> str:
    """Generate a contextual fallback response when AI is unavailable"""
    email_lower = email_content.lower()

    # Check for return/refund requests first (most specific)
    if any(word in email_lower for word in ["return", "refund", "exchange"]):
        return "Thank you for contacting us regarding your return request. I'll review your order details and get back to you within 24 hours with the return procedure and next steps for processing your refund."

    # Check for billing/payment issues
    elif any(
        word in email_lower for word in ["invoice", "payment", "billing", "charge"]
    ):
        return "Thank you for your message regarding billing. I'll review the details with our accounting team and get back to you with an update within 1-2 business days."

    # Check for meeting/scheduling requests
    elif any(
        word in email_lower for word in ["meeting", "schedule", "call", "appointment"]
    ):
        return "Thank you for reaching out about scheduling. I'll check my calendar and send you some available time slots within the next 24 hours."

    # Check for urgent matters
    elif any(
        word in email_lower for word in ["urgent", "asap", "immediately", "priority"]
    ):
        return "I understand this is urgent and requires immediate attention. I'm prioritizing this request and will provide a detailed response within the next few hours."

    # Check for questions/help requests
    elif any(
        word in email_lower for word in ["question", "help", "assistance", "support"]
    ):
        return "Thank you for your question. I'll review the details carefully and provide you with a comprehensive response shortly."

    # Check for follow-ups
    elif any(
        word in email_lower for word in ["follow up", "following up", "checking in"]
    ):
        return "Thank you for following up on this matter. I appreciate your patience and will provide you with an update on the current status soon."

    # Check for proposals/projects
    elif any(word in email_lower for word in ["proposal", "project", "collaboration"]):
        return "Thank you for sharing this opportunity. I'm interested in learning more and will review the details to provide you with thoughtful feedback."

    # Only match "thank you" if it's clearly a thank you message (not part of a request)
    elif (
        email_lower.strip().startswith(("thank you", "thanks"))
        and len(email_content.split()) < 20
    ):
        return "You're very welcome! I'm glad I could help. Please don't hesitate to reach out if you need anything else."

    else:
        return "Thank you for your email. I've received your message and will review it carefully to provide you with an appropriate response soon."


@app.get("/templates", response_model=List[Template])
def get_templates():
    """Get all response templates"""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "email_responses.db"))
    cursor = conn.execute("SELECT id, name, template, category FROM response_templates")
    templates = [
        Template(id=row[0], name=row[1], template=row[2], category=row[3])
        for row in cursor.fetchall()
    ]
    conn.close()
    return templates


@app.get("/history")
def get_history(limit: int = 10):
    """Get recent email response history"""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "email_responses.db"))
    cursor = conn.execute(
        "SELECT original_email, generated_response, response_type, created_at FROM email_responses ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    history = []
    for row in cursor.fetchall():
        history.append(
            {
                "original_email": row[0][:100] + "..." if len(row[0]) > 100 else row[0],
                "generated_response": row[1],
                "response_type": row[2],
                "created_at": row[3],
            }
        )
    conn.close()
    return {"history": history}


@app.post("/templates", response_model=Template)
def create_template(template: Template):
    """Create a new response template"""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "email_responses.db"))
    cursor = conn.execute(
        "INSERT INTO response_templates (name, template, category) VALUES (?, ?, ?)",
        (template.name, template.template, template.category),
    )
    template.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return template


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
