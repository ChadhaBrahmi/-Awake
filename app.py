import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
app = Flask(__name__)
CORS(app)

APP_NAME = "dream_logic_engine"
USER_ID = "user_01"
SESSION_ID = "session_dream_01"

dream_agent = Agent(
    name="Awake",
    model="gemini-2.5-flash",
    description="Makes short dreams into complete stories.",
    instruction="""
You are a storyteller who writes dream-like stories.
When given a short dream:
1. EXPAND the dream into a full story.
2. Keep coherence.
3. Add atmosphere and emotions.
4. End with a satisfying conclusion.
""",
    tools=[]
)

loop = asyncio.get_event_loop()
runner = None

async def init_runner():
    global runner
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    runner = Runner(
        agent=dream_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

loop.run_until_complete(init_runner())

async def generate_story(dream_text):
    content = types.Content(
        role="user",
        parts=[types.Part(text=dream_text)]
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )

    async for event in events:
        if event.is_final_response():
            return event.content.parts[0].text

@app.route("/run", methods=["POST"])
def run():
    data = request.json or {}
    dream = data.get("dream", "")

    if not dream:
        return jsonify({"story": "No dream provided!"})

    story = loop.run_until_complete(generate_story(dream))
    return jsonify({"story": story})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
