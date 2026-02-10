import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app)

limiter = Limiter(get_remote_address, app=app, default_limits=["60 per hour"])

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"story": "Too many requests — please wait a minute before trying again."}), 429

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

APP_NAME = "dream_logic_engine"
USER_ID = "user_01"
SESSION_ID = "session_dream_01"

dream_agent = Agent(
    name="Awake",
    model="gemini-2.5-flash",
    description="Transforms short dreams into complete stories.",
    instruction="""
You are a storyteller who writes dream-like stories.
When given a short dream:
1. Expand the dream into a full story
2. Keep coherence
3. Add atmosphere and emotions
4. End with a satisfying conclusion
""",
    tools=[]
)

runner = None
runner_initialized = False

async def init_runner():
    global runner
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=dream_agent, app_name=APP_NAME, session_service=session_service)

def ensure_runner():
    global runner_initialized
    if not runner_initialized:
        loop.run_until_complete(init_runner())
        runner_initialized = True

async def generate_story(dream_text: str) -> str:
    content = types.Content(role="user", parts=[types.Part(text=dream_text)])
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    async for event in events:
        if event.is_final_response():
            return event.content.parts[0].text
    return "Failed to generate story."

@app.route("/")
def health():
    return "Awake backend is running."

@app.route("/run", methods=["POST"])
@limiter.limit("5 per minute")
def run():
    ensure_runner()
    data = request.get_json(silent=True) or {}
    dream = data.get("dream", "").strip()
    if not dream:
        return jsonify({"story": "No dream provided!"})
    try:
        story = loop.run_until_complete(generate_story(dream))
        return jsonify({"story": story})
    except:
        return jsonify({"story": "Error generating story"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
