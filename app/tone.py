"""
Vigie — Message tone constants.

All user-facing messages use a warm, human, empathetic tone.
No robotic language. No jargon. No cold notifications.

The voice of Vigie is:
  - Calm (never panicked, even in critical situations)
  - Caring (shows concern for beneficiaries AND volunteers)
  - Clear (short sentences, no jargon)
  - Grateful (thanks volunteers for their work)
  - Present (uses "I" not "the system")
"""


# Greetings by time of day
def greeting_for_time(hour: int) -> str:
    """Return a warm greeting based on the hour."""
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 18:
        return "Good afternoon"
    elif 18 <= hour < 22:
        return "Good evening"
    else:
        return "Hello"


# Volunteer appreciation messages (rotated randomly)
VOLUNTEER_THANKS = [
    "Thank you for watching over them. 💜",
    "Your calls make a real difference today.",
    "Every check-in matters. Thank you for being here.",
    "You're doing important work. Thank you.",
    "They're not alone because of you. Thank you.",
]

# Check-in confirmations (human, warm)
CHECKIN_OK = [
    "Got it — {name} is doing okay. I've logged the check-in. Thank you for calling. 💜",
    "Thank you! I've recorded that {name} is fine. Your call matters more than you know.",
    "Noted — {name} is okay. Thank you for taking the time to check on them today.",
]

CHECKIN_WEAK = [
    "I've flagged a weak signal for {name}. I'm looking up the nearest pharmacy now. Thank you for the careful observation.",
    "Thank you for noticing that about {name}. I've flagged it and I'm finding nearby help. You may have just prevented something serious.",
    "Noted — {name} has a weak signal. I'm on it. Thank you for being attentive.",
]

CHECKIN_UNREACHABLE = [
    "No answer from {name}. I've notified the neighbor referent to check on them. Don't worry — we're on it.",
    "{name} didn't answer. I've alerted their neighbor referent. If they can't be reached either, I'll escalate to the medical coordinator. Thank you for trying.",
    "I've flagged {name} as unreachable. The neighbor referent has been contacted. We'll make sure they're okay.",
]

CHECKIN_CRITICAL = [
    ":rotating_light: I've triggered a critical SAMU escalation for {name}. The crisis cell has been alerted with a full context summary. Please stay available — the medical coordinator may need you.",
    "A SAMU escalation has been launched for {name}. Everything is in motion. Thank you for acting quickly — this is exactly what Vigie is for.",
]

# Escalation messages (calm but urgent)
ESCALATION_CONTEXT = (
    "Here's what I know about {name}: {summary}. "
    "This alert has been posted in #cellule-crise with a SAMU call button. "
    "The medical coordinator and neighbor referent have been notified."
)

# Daily report intro
REPORT_INTRO = (
    "Here's today's summary. "
    "Every number on this screen represents a person who wasn't alone today — because of you. 💜"
)

# Status messages
STATUS_NO_SCENARIO = (
    "No active heatwave alert right now. "
    "I'm here if you need me — type /vigie help anytime."
)

STATUS_ACTIVE = (
    "Heatwave vigilance is active. Here's where we stand right now:"
)

# Welcome message for new volunteers
WELCOME_VOLUNTEER = (
    ":wave: Hi {name}, I'm Vigie.\n\n"
    "I help coordinate check-in calls for isolated elderly people during heatwaves. "
    "When there's a heatwave alert, I'll send you a list of people to call. "
    "You just click a button after each call — I handle the rest.\n\n"
    "No commands to memorize. No technical stuff. Just click buttons and help people.\n\n"
    "If you ever need me, just send me a message. I'm always here."
)

# Reset confirmation
RESET_CONFIRM = (
    "Done — I've cleared the current situation. We're ready for the next alert."
)

# No beneficiary found
NO_BENEFICIARY = (
    "I couldn't find that beneficiary. "
    "Make sure you're using the name from your assignment list, "
    "or just click the Check-in button next to their name in our conversation."
)
