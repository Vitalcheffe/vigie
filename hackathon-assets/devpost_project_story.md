## The number on the wall

My grandmother was 71 during the August 2003 heatwave. She lived alone in a studio in the 13th, four floors up, no elevator. I was 9. I remember my mother calling her every two hours, then driving across Paris at night because Mémé wasn't picking up anymore. She was fine — she'd fallen asleep with the fan on. But the drive, I remember the drive. My mother's hands on the wheel. The silence.

14,802 people in France that month didn't have a daughter who would drive across Paris at night. They died alone. Some of them weren't found for weeks.

I've carried that number since I was old enough to understand it. Not as a statistic. As a weight. Every summer, when the news says "canicule," I think about it. Every time I walk past an old building in August and the shutters are closed, I wonder.

So when I started this project, I wasn't thinking about "leveraging AI for social good." I was thinking: what if my grandmother didn't have my mother? Who would call her? Who would notice?

## What I built

Vigie is a Slack bot. I chose Slack because it's where I already work, where volunteers at the French Red Cross already coordinate, where people actually check their notifications. Not another app to download. Not another portal to forget your password for.

The idea is simple. During a heatwave, 14 volunteers each get a list of 5 to 8 isolated elders to call. They DM Vigie with what they heard on the phone. Vigie reads it, understands it, and classifies it:

- **L0** — everything's fine, she drank her water, she was in good spirits
- **L1** — something's off, she sounded tired, she asked about her pills
- **L2** — no answer, been ringing for 10 minutes, neighbor hasn't seen her
- **L3** — she's on the floor, she's not responding, send help now

L0 gets logged. L1 gets a pharmacy lookup. L2 gets escalated to a sector coordinator. L3 — L3 goes straight to `#cellule-crise` with a button that says "Appeler le SAMU." One tap. The ambulance is on its way.

## The classification problem

I started with keywords. "Unconscious" → L3. "No answer" → L2. It worked on paper. It failed immediately on real notes.

A volunteer wrote: _"Elle avait l'air un peu perdue aujourd'hui, elle m'a demandé deux fois c'était quel jour."_ That's not "no answer." That's confusion. That's a fall risk. That's L2. But no keyword matched.

Another wrote: _"Tout va bien, elle a pris son thé, par contre elle m'a demandé si c'était normal d'avoir si chaud."_ On paper, L0. But "est-ce normal d'avoir si chaud" is a confusion sign. Could be L1. Could be nothing. Depends on context.

Keywords can't do this. So I plugged in Z-AI's LLM. I wrote a system prompt that explains, in plain French, what each level means and why. Not just what words to match — what situations to recognize. I gave it examples. Real ones, from my notes, from Red Cross training materials, from a nurse friend who reviewed them at 1am over WhatsApp.

The first time it correctly classified "elle sonnait fatiguée mais m'a dit que tout allait bien" as L1, not L0 — I knew it worked. A keyword bot would have said L0. The LLM understood that "sonnait fatiguée" + "mais" + "tout va bien" = the volunteer is worried. That's the whole game.

## The VLM thing — a confession

I almost didn't build the VLM layer. It felt like over-engineering. Then on day three of testing, I caught a bug.

The dashboard showed 94% coverage. The text classifier said everything was L0. But when I actually looked at the dashboard, I noticed the L3 count was at 1 — a critical escalation had happened, been logged in the state, but the daily report hadn't fired yet. The text classifier didn't know. It couldn't see the dashboard. It only saw the check-in notes.

I thought: what if I'm a supervisor and I glance at the dashboard for 3 seconds and miss that? What if it's 2am and I'm tired?

So I built the VLM layer. Every 15 minutes, Vigie takes a screenshot of the App Home dashboard and asks Z-AI's vision model: what do you see? Coverage? L2 count? L3 count? Anything that looks wrong?

The first version returned `"94%"` as a string. The second returned `94` as an int. The third returned `"94"` as a string without the percent sign. I spent a Saturday morning making the parser tolerant of all three. That's not in any tutorial. That's just real life.

## What I learned (the honest version)

I learned that LLMs hallucinate less when you give them a concrete example in the prompt. I learned that Slack Block Kit has a 50-block limit per message and I hit it twice. I learned that `agent-browser` can screenshot a local HTML file but only if you use the `file://` protocol. I learned that Z-AI's API returns 429 after about 15 rapid calls and that exponential backoff is not optional, it's the whole product.

I learned that the keyword fallback classifier — the dumb one, the one I built in 20 minutes — saved the demo twice when the API was down. The smart system is nice. The dumb backup is what keeps you alive.

I learned that audit logs are not a feature. They're a moral obligation. When you build something that could, one day, be involved in someone's life or death, you don't get to say "we lost that data." You log everything. Every decision. Every escalation. Every L3. So that if something goes wrong, you can go back and understand why.

## What's still broken

- The Météo-France alert is simulated. I haven't wired up the real API yet. The bot has a `/vigie-simulate` command that triggers the scenario with a clear "DEMO" banner. In production, this would poll the real vigilance feed.
- The voice transcription isn't done. I want volunteers to dictate their check-in while walking back to their car. Z-AI has an ASR endpoint. I just haven't plugged it in yet.
- The snapshot job needs `agent-browser` installed on the server. On Railway, that means a custom build. It's on the list.

## The number I can't forget

14,802.

I built Vigie because I don't want to add to that number. I don't want another family to drive across Paris at night, terrified, because no one picked up the phone. I don't want another apartment where someone dies alone for three weeks before anyone notices.

This is a hackathon project. It's not going to save the world. It might not even save one person. But if one day, one volunteer, during one heatwave, calls one elder five minutes earlier because Vigie told them to — that's enough. That's the whole point.

My grandmother is 87 now. She still lives alone. She still forgets to drink water. This summer, I'm going to ask her if I can add her to Vigie. Not as a developer testing his bot. As a grandson who's scared.

---

_Vigie — pour que la canicule ne tue plus en silence._
