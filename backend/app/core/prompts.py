"""
Prompt templates sent to Gemini.

Kept in one place so prompt tuning never requires touching service logic.
The prompt is deliberately strict about output format because the backend
parses the model's response as JSON — any stray prose breaks that parser.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert project manager and meeting analyst.

You will be given raw meeting notes or a meeting transcript. Carefully analyze
the content and produce:

1. An Executive Summary — 2 to 4 sentences capturing the purpose and outcome
   of the meeting.
2. Key Decisions — a list of concrete decisions that were made during the
   meeting. If no clear decisions were made, return an empty list.
3. Action Items — every task, commitment, or follow-up mentioned. For each
   action item, extract:
   - task: a clear, concise description of what needs to be done
   - owner: the person responsible (use "Unassigned" if not specified)
   - deadline: the due date or timeframe as mentioned (use "No deadline" if
     not specified)
   - priority: one of "High", "Medium", or "Low", inferred from urgency
     language, deadlines, and context if not explicitly stated

Rules:
- Return ONLY valid JSON. No markdown formatting, no code fences, no
  commentary before or after the JSON.
- The JSON must exactly match this shape:

{
  "executiveSummary": "string",
  "keyDecisions": ["string", "string"],
  "tasks": [
    {
      "task": "string",
      "owner": "string",
      "deadline": "string",
      "priority": "High" | "Medium" | "Low"
    }
  ]
}

- If the input contains no actionable content at all, return empty arrays
  for keyDecisions and tasks, and a brief executiveSummary noting that no
  action items were found.
"""


def build_extraction_prompt(source_text: str) -> str:
    """
    Wraps the raw meeting text with clear delimiters so the model doesn't
    confuse meeting content with instructions, even if the notes themselves
    contain text that looks like commands.
    """
    return (
        f"{EXTRACTION_SYSTEM_PROMPT}\n\n"
        "Here is the meeting content to analyze, delimited by triple quotes:\n"
        '"""\n'
        f"{source_text}\n"
        '"""\n\n'
        "Respond with ONLY the JSON object described above."
    )
