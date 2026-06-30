import json
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OUTPUT_FILE = "ask_conduit_answers.json"

QUESTIONS = [
    "Where should Spectrum prioritize expansion next?",
    "Which county has the strongest builder momentum?",
    "What are the strongest telecom opportunities?"
]

def load_json(filename, fallback):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return fallback

data_package = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "executive_brief": load_json("executive_brief.json", {}),
    "activity_feed": load_json("activity_feed.json", []),
    "projects_count": len(load_json("projects.json", [])),
    "land_count": len(load_json("land_intelligence.json", [])),
    "builders_count": len(load_json("builder_portfolios.json", [])),
    "locate_patterns": load_json("locate_patterns.json", []),
    "locate_correlations": load_json("locate_correlations.json", [])
}

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

answers = {}

for question in QUESTIONS:
    prompt = f"""
You are Conduit Analyst, a telecom development intelligence analyst.

Answer the user's question using only the Conduit intelligence package below.

Return valid JSON only with these keys:
recommendation
confidence
reasoning
next_action

Rules:
- Be concise.
- Do not invent facts.
- Focus on telecom expansion, builder momentum, land signals, GIS, and infrastructure signals.
- reasoning must be a list of 3 to 5 bullet strings.

QUESTION:
{question}

CONDUIT INTELLIGENCE PACKAGE:
{json.dumps(data_package, indent=2)}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        content = response.output_text.strip()

        if content.startswith("```json"):
            content = content.replace("```json", "", 1).strip()
        if content.startswith("```"):
            content = content.replace("```", "", 1).strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        answers[question] = json.loads(content)

    except Exception as error:
        answers[question] = {
            "recommendation": "Ask Conduit analysis could not be generated.",
            "confidence": "Unavailable",
            "reasoning": [str(error)],
            "next_action": "Review system logs."
        }

output = {
    "generated_at": data_package["generated_at"],
    "answers": answers
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(output, file, indent=2)

print("Ask Conduit analyst answers generated.")
print("Saved:", OUTPUT_FILE)