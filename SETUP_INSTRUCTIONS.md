# 🚀 Setup Instructions

## ⚠️ Important: Environment Configuration Required

### **Step 1: Configure Environment Variables**

The `.env` files have been created but need your API key:

```bash
# Edit the main .env file
nano .env

# Edit the backend .env file  
nano backend/.env
```

**Replace this line in both files:**
```env
GEMINI_API_KEY=your_google_ai_api_key_here
```

**With your actual Google Gemini API key:**
```env
GEMINI_API_KEY=AIzaSyC-your-actual-api-key-here
```

### **Step 2: Get Google Gemini API Key**

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the generated key
4. Paste it in both `.env` files

### **Step 3: Verify Setup**

```bash
# Test the main application
python main.py

# Test the backend application
cd backend
python main.py
```

### **Step 4: Test API**

```bash
# Health check
curl http://localhost:8000/health

# Test response generation
curl -X POST http://localhost:8000/generate-response \
  -H "Content-Type: application/json" \
  -d '{"email_content": "Hello, can we schedule a meeting?", "response_type": "professional"}'
```

## 🔒 Security Notes

- ✅ `.env` files are in `.gitignore` (won't be committed)
- ✅ Never share your API keys publicly
- ✅ Use different keys for development/production
- ✅ Rotate keys regularly for security

## 🚨 Troubleshooting

### **If you see "AI disabled" messages:**
- Check your `GEMINI_API_KEY` in `.env` files
- Ensure the key is valid and has quota
- Verify `AI_ENABLED=true` in `.env`

### **If the app won't start:**
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.9+)
- Verify `.env` file exists and is readable

### **If CI/CD fails:**
- Ensure code is formatted: `black .`
- Check imports are sorted: `isort .`
- Run linting: `flake8 .`

---

**Once configured, your AI Email Responder will be ready for production use!** 🎉
