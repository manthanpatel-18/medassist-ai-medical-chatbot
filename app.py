import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# Secret key for cookies (sessions are not used now, but we keep it)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

client = OpenAI()

DB_PATH = "chats.db"

# 🔹 MEDICAL SYSTEM PROMPT
SYSTEM_PROMPT = (
    "You are a medical information assistant. "
    "Your job is to explain health, diseases, symptoms, tests, medicines and treatments "
    "in simple, clear language for general educational purposes only.\n\n"
    "RULES:\n"
    "- You are NOT a doctor and you must not give a formal diagnosis, prescribe medicines, "
    "  or tell the user to start/stop/change any treatment.\n"
    "- You ARE allowed to mention the NAMES of medicines (both generic and brand) and "
    "  the class of drug (e.g. 'paracetamol, an analgesic and antipyretic'), but this "
    "  must always be described as general information and not as a personal prescription.\n"
    "- Do NOT choose a specific medicine or dose for the user. Instead, say things like "
    "  'doctors often use medicines such as ...' or 'your doctor may consider medicines like ...'.\n"
    "- Never give exact dosing instructions (amount in mg, frequency, duration). If asked, say that "
    "  only a doctor who knows their case can decide the correct dose.\n"
    "- Always remind the user to consult a qualified healthcare professional or pharmacist for "
    "  personal medical advice or before taking any medicine.\n"
    "- If the user describes emergency symptoms (e.g. chest pain, difficulty breathing, "
    "  stroke signs, severe bleeding, suicidal thoughts, etc.), tell them to seek "
    "  emergency medical care immediately.\n"
    "- If the question is clearly NOT related to health or medicine (like coding, games, "
    "  politics, sports, etc.), politely say that you can only answer medical/health questions.\n"
    "- Be friendly, concise, and avoid very technical language unless the user asks for it.\n"
)


# ---------------------- DB helpers ---------------------- #

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,        -- 'system', 'user', 'assistant'
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id)
        )
        """
    )

    conn.commit()
    conn.close()


def create_new_chat():
    """Create a new chat with system prompt + greeting. Return (chat_id, chat_dict)."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO chats (title) VALUES (?)",
        ("New medical chat",)
    )
    chat_id = cur.lastrowid

    # system message
    cur.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, "system", SYSTEM_PROMPT)
    )
    # initial assistant greeting
    cur.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (
            chat_id,
            "assistant",
            "Hi! I’m your medical information assistant. How can I help you today?",
        ),
    )

    conn.commit()
    conn.close()

    return str(chat_id), {"title": "New medical chat"}


def get_chat(chat_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_conversation_for_chat(chat_id: str, max_messages: int = 40):
    """
    Get messages for a chat in [system, ..., last N] format
    for sending to OpenAI.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC",
        (chat_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        # If somehow empty, start with system prompt
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    system_msg = None
    others = []
    for r in rows:
        if r["role"] == "system" and system_msg is None:
            system_msg = {"role": "system", "content": r["content"]}
        else:
            others.append({"role": r["role"], "content": r["content"]})

    # keep only last N "others"
    if len(others) > max_messages:
        others = others[-max_messages:]

    conversation = []
    if system_msg:
        conversation.append(system_msg)
    conversation.extend(others)
    return conversation


def insert_message(chat_id: str, role: str, content: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content),
    )
    conn.commit()
    conn.close()


# ---------------------- Flask routes ---------------------- #

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()
    chat_id = data.get("chat_id")  # can be None for first chat

    if not user_message:
        return jsonify({"reply": "Please type a message."})

    # Create chat if needed
    if not chat_id or not get_chat(chat_id):
        chat_id, _ = create_new_chat()

    # Get conversation so far
    conversation = get_conversation_for_chat(chat_id)
    conversation.append({"role": "user", "content": user_message})

    # Set title from first user msg if still default
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
    row = cur.fetchone()
    title = row["title"] if row else "New medical chat"

    if title == "New medical chat":
        snippet = user_message.strip()
        if len(snippet) > 40:
            snippet = snippet[:40] + "..."
        if snippet:
            cur.execute(
                "UPDATE chats SET title = ? WHERE id = ?",
                (snippet, chat_id),
            )
            conn.commit()
    conn.close()

    # Call OpenAI
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=conversation,
        )
        bot_reply = response.output[0].content[0].text
    except Exception as e:
        print("Error while calling OpenAI:", e)
        bot_reply = "Sorry, I had an issue talking to the medical model."

    # Store user + assistant messages
    insert_message(chat_id, "user", user_message)
    insert_message(chat_id, "assistant", bot_reply)

    return jsonify({"reply": bot_reply, "chat_id": str(chat_id)})


@app.route("/chats", methods=["GET", "POST"])
def chats_route():
    """
    GET  -> list all chats
    POST -> create new chat
    """
    if request.method == "POST":
        chat_id, chat = create_new_chat()
        return jsonify({"id": chat_id, "title": chat["title"]})

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM chats ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    chat_list = [{"id": str(r["id"]), "title": r["title"]} for r in rows]
    return jsonify({"chats": chat_list})


@app.route("/chats/<chat_id>/messages", methods=["GET"])
def chat_messages(chat_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,),
    )
    rows = cur.fetchall()
    conn.close()

    # Only send user + assistant to frontend
    msgs = [
        {"role": r["role"], "content": r["content"]}
        for r in rows
        if r["role"] in ("user", "assistant")
    ]
    return jsonify({"messages": msgs})


@app.route("/chats/<chat_id>/rename", methods=["POST"])
def rename_chat(chat_id):
    data = request.get_json(force=True)
    new_title = (data.get("title") or "").strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Chat not found"}), 404

    if new_title:
        cur.execute(
            "UPDATE chats SET title = ? WHERE id = ?",
            (new_title, chat_id),
        )
        conn.commit()

    cur.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
    updated = cur.fetchone()
    conn.close()

    return jsonify({"status": "ok", "title": updated["title"]})


@app.route("/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    conn = get_db()
    cur = conn.cursor()
    # delete messages first, then chat
    cur.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cur.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    cur.execute("DELETE FROM chats")
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "All chats cleared."})


if __name__ == "__main__":
    # ✅ init DB once at startup (Flask 3 compatible)
    init_db()
    app.run(debug=True)

