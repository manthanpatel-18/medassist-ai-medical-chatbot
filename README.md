# 🩺 MedAssist - AI Medical Information Assistant

MedAssist is an AI-powered medical information assistant designed to provide **safe, educational health guidance** while strictly avoiding medical diagnosis, prescriptions, or dosage recommendations.

The project focuses on **responsible AI usage**, conversation memory, multilingual support, and a clean healthcare-focused user interface.

---

## 🚀 Key Features

- 🧠 **Medical-Only AI Responses**
  - Answers only health and medical-related questions
  - Politely refuses non-medical queries

- 💬 **Conversation Memory**
  - Stores chat history using SQLite (`chats.db`)
  - Maintains context across multiple messages

- 💊 **Medicine Awareness (Safe Use)**
  - Suggests commonly used medicine categories and names
  - No dosage, prescription, or treatment advice

- 🏥 **Nearby Hospital Suggestions**
  - Recommends well-known hospitals based on user-provided location

- 🌍 **Multilingual Support**
  - Translates medical responses into multiple languages on request

- 🔐 **Secure API Usage**
  - OpenAI API key handled via environment variables

---

## 🧠 How It Works

1. User enters a medical query through the web interface
2. The backend processes the request using Flask
3. Conversation history is stored in SQLite (`chats.db`)
4. The AI responds using a medical-restricted system prompt
5. Responses are displayed in a clean, healthcare-friendly UI

---

## 🛠 Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **AI Model:** OpenAI API

---

## 📂 Project Structure
```
medassist-ai-medical-chatbot/
│
├── app.py
├── index.html
├── chats.db
├── requirements.txt
└── README.md
```

## ⚠️ Medical Disclaimer

MedAssist does **not** provide medical diagnosis, prescriptions, or treatment plans.

This application is intended **only for educational and informational purposes** and should not replace professional medical advice.


## ▶️ Running the Project Locally

1. Install dependencies:
```
pip install -r requirements.txt
```
2. Set your OpenAI API key as an environment variable:
```
export OPENAI_API_KEY=your_api_key_here
```
(Windows PowerShell)
```
setx OPENAI_API_KEY "your_api_key_here"

```
3. Run the application:
```
python app.py
```

## 👤 Author

**Manthan Patel**
- Linkedin: [Manthan Patel](https://www.linkedin.com/in/manthan-patel18)
- Portfolio: [yourwebsite.com](https://yourwebsite.com)
