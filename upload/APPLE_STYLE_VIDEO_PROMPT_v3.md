#
#  ╔══════════════════════════════════════════════════════════════╗
#  ║   THE DEFINITIVE GUIDE TO CREATING A PRODUCT LAUNCH FILM   ║
#  ║   THAT MAKES PEOPLE SAY "THIS IS THE FUTURE"               ║
#  ╚══════════════════════════════════════════════════════════════╝
#
#  Version 3.0 — v2 had no audio enforcement and weak MP4 output.
#               v3 fixes both. No more silent HTML5 "videos".
#
#  This is universal. Works for ANY product. ANY industry. ANY agent.
#
#  WHAT THIS ISN'T: A slide deck. A screen recording. A demo.
#                    An HTML animation. A silent video.
#  WHAT THIS IS: A film. Apple WWDC quality. Tesla launch energy.
#                 The kind of video that makes jaws drop.
#                 WITH SOUND. IN MP4 FORMAT.
#
#  ═══════════════════════════════════════════════════════════════
#  HOW TO USE THIS DOCUMENT
#  ═══════════════════════════════════════════════════════════════
#
#  Priority system:
#    [P0] = NON-NEGOTIABLE. Violating this = instant amateur hour.
#    [P1] = CRITICAL. Missing this = noticeable quality gap.
#    [P2] = ELEVATION. Having this = separates great from legendary.
#
#  Read sections in order. Each builds on the last.
#  The scene blueprint (Section 6) references everything before it.
#
#  Study references (watch these before you start):
#    - Apple WWDC 2023 intro film
#    - Apple MacBook Air M2 reveal
#    - Tesla Cybertruck unveiling
#    - Stripe Sessions 2024 opening
#    - Notion 2023 redo video
#    - Linear's homepage animation
#
#══════════════════════════════════════════════════════════════════
#  SECTION 0: OUTPUT FORMAT — READ THIS FIRST OR YOU WILL FAIL
#══════════════════════════════════════════════════════════════════
#
#  ┌─────────────────────────────────────────────────────────────────┐
#  │              THE FINAL DELIVERABLE IS AN MP4 FILE              │
#  │                    THIS IS [P0] — NON-NEGOTIABLE               │
#  └─────────────────────────────────────────────────────────────────┘
#
#  FORMAT REQUIREMENTS [P0 — ALL of these are mandatory]:
#    - Container:  MP4 (.mp4)
#    - Video codec: H.264
#    - Resolution:  1920×1080 (Full HD)
#    - Frame rate:  60fps (30fps is acceptable but not preferred)
#    - Duration:    minimum 3 minutes, target 4:18
#    - Audio codec: AAC
#    - Audio:       MUST HAVE A SOUNDTRACK (see Section 7)
#    - File size:   expect 50-150MB for a 4-min video
#
#  ╔═══════════════════════════════════════════════════════════════╗
#  ║  WHAT IS NOT ACCEPTABLE AS FINAL OUTPUT:                     ║
#  ║                                                               ║
#  ║  ❌ An HTML5 file (no matter how beautiful the animation)     ║
#  ║  ❌ A URL to a web page with animations                       ║
#  ║  ❌ Instructions to "open in browser and screen-record"       ║
#  ║  ❌ A silent video (no audio track)                           ║
#  ║  ❌ A GIF or WebM                                            ║
#  ║  ❌ A directory of PNG frames                                 ║
#  ║                                                               ║
#  ║  THE ONLY ACCEPTABLE OUTPUT IS: product-launch.mp4           ║
#  ║  WITH VIDEO + AUDIO COMBINED IN A SINGLE FILE.               ║
#  ╚═══════════════════════════════════════════════════════════════╝
#
#  TECHNICAL APPROACH — How to actually produce the MP4:
#
#  Step 1: Create the HTML5 animation (Canvas/CSS/GSAP/SVG).
#          This is your RENDER SOURCE, not your deliverable.
#
#  Step 2: Capture the animation as video frames.
#          RECOMMENDED: Use Playwright or Puppeteer to:
#            a) Open the HTML file in a headless browser at 1920×1080
#            b) Use page.video.startRecording() or equivalent
#            c) Record the full animation duration at 60fps
#          Example (Playwright):
#            const browser = await chromium.launch();
#            const context = await browser.newContext({
#              recordVideo: { dir: 'output/', size: { width: 1920, height: 1080 } }
#            });
#            const page = await context.newPage();
#            await page.goto('file:///path/to/animation.html');
#            await page.waitForTimeout(totalDurationMs + 2000); // wait for animation to finish
#            await context.close(); // saves the video
#            await browser.close();
#
#  Step 3: Generate or obtain the audio track.
#          See Section 7 (Sound Design) for full details.
#          Options:
#            a) Use Web Audio API in the HTML itself (Playwright captures it)
#            b) Generate audio separately and merge with FFmpeg
#            c) Use TTS/music generation APIs for narration + music
#
#  Step 4: Combine video + audio using FFmpeg.
#          ffmpeg -i video.webm -i audio.mp3 -c:v libx264 -preset slow \
#                 -crf 18 -c:a aac -b:a 192k -pix_fmt yuv420p \
#                 -movflags +faststart product-launch.mp4
#
#  FFmpeg quality flags explained:
#    -preset slow   → better compression (worth the wait)
#    -crf 18        → visually lossless quality (lower = better, 0-51)
#    -b:a 192k      → high quality audio
#    -pix_fmt yuv420p → maximum compatibility
#    -movflags +faststart → streaming-friendly MP4
#
#  IF YOU CANNOT PRODUCE AN MP4: Produce the best video you can
#  AND clearly state what additional step is needed to get to MP4.
#  But your PRIMARY goal is to produce the MP4 file directly.
#  An HTML file alone is a FAILED deliverable.
#
#══════════════════════════════════════════════════════════════════
#  SECTION 1: THE PSYCHOLOGY — WHY SOME VIDEOS HIT AND OTHERS DON'T
#══════════════════════════════════════════════════════════════════

Most product videos fail for the same reason: they're INFORMATIONAL.
Great product videos are TRANSFORMATIONAL.

The viewer should not LEARN about the product.
The viewer should EXPERIENCE a world where the product exists.

Here are the 5 laws that govern this transformation:

┌─────────────────────────────────────────────────────────────────┐
│ LAW 1: THE 3-SECOND HOOK                    [P0 — EVERYTHING]  │
│                                                                 │
│ The first 3 seconds decide if someone keeps watching.          │
│ You must create a moment so visually arresting that it's       │
│ physically uncomfortable to look away.                          │
│                                                                 │
│ NOT loud. NOT chaotic. ARRESTING.                               │
│                                                                 │
│ A single point of light in absolute darkness.                   │
│ A shape forming from nothing.                                   │
│ A breath before the storm.                                      │
│                                                                 │
│ If you lose them in 3 seconds, nothing else matters.            │
│ THIS IS THE MOST IMPORTANT 3 SECONDS OF THE ENTIRE VIDEO.      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAW 2: THE RHYTHM OF REVELATION                       [P0]      │
│                                                                 │
│ A great product film is MUSIC. It has:                          │
│                                                                 │
│   VERSES   (problem, context)     → slower, atmospheric, tense  │
│   CHORUS   (product, features)    → faster, brighter, release   │
│   BRIDGE   (comparison, proof)    → shift in tone, surprise     │
│   CODA     (closing CTA)          → emotional peak, resolution  │
│                                                                 │
│ The pace should NEVER be flat.                                  │
│ It breathes. It accelerates. It pulls back. It DROPS.           │
│                                                                 │
│ Visual energy waveform across 4.5 minutes:                      │
│                                                                 │
│  ▲                                                              │
│  │    ╱╲        ╱╲╱╲╱╲       ╱╲      ╱╲                       │
│  │   ╱  ╲  ╱╲ ╱     ╲     ╱  ╲    ╱  ╲                      │
│  │  ╱    ╲╱  ╲╱       ╲   ╱    ╲  ╱    ╲                    │
│  │ ╱                  ╲ ╱      ╲╱      ╲                     │
│  │╱                    ╳               ╲╱╲                   │
│  └──────────────────────────────────────────▶ time             │
│   S1  S2 S3   S4    S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15   │
│   void chaos cost REVEAL  features     comp  team sec  $  END  │
│                                                                 │
│ KEY: S4 (the reveal) is the FIRST peak.                         │
│      S5-S9 (features) is the SUSTAINED energy.                  │
│      S15 (the finale) is the HIGHEST peak.                      │
│      S2-S3 (problem) is the VALLEY that makes peaks matter.     │
│      NEVER let energy flatline between peaks.                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAW 3: SHOW, DON'T TELL                               [P0]      │
│                                                                 │
│ Every claim must be VISIBLE.                                    │
│                                                                 │
│ Don't write "AI-powered"  → show the AI thinking               │
│ Don't write "fast"        → show things moving fast             │
│ Don't write "connected"   → show connections forming live       │
│ Don't write "beautiful"   → make the video itself beautiful    │
│                                                                 │
│ THE MEDIUM IS THE MESSAGE.                                      │
│ If you have to WRITE a feature benefit, you've already lost.    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAW 4: THE IMPOSSIBILITY MOMENT                       [P1]      │
│                                                                 │
│ Every great product film has at least one moment where the      │
│ viewer thinks "How did they do that?" or "That's not possible." │
│                                                                 │
│ This is the moment they SHARE. The moment they REMEMBER.        │
│                                                                 │
│ Build toward it. Earn it. Deliver it.                           │
│                                                                 │
│ Examples:                                                       │
│   - Knowledge graph that connects across team members auto      │
│   - AI response that shows its sources with connecting lines    │
│   - A visualization that grows from 1 to 100 elements in 5s    │
│   - Stats that shatter like glass revealing light inside        │
│   - A zoom transition that dives INTO an element into a new scene│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAW 5: MAGICAL BUT CREDIBLE                           [P1]      │
│                                                                 │
│ The magic must serve the product, not distract from it.         │
│ Every stunning visual must communicate a REAL feature.          │
│                                                                 │
│ Pretty without purpose = decoration.                            │
│ Pretty WITH purpose = design.                                   │
│                                                                 │
│ The viewer should think "I want THAT" not "that's cool."       │
│ "THAT" = the product. "cool" = just the video.                 │
│                                                                 │
│ Test: If you remove the effect, does the product suffer?        │
│       If no → the effect is decoration. Remove it.              │
│       If yes → the effect is design. Keep it.                   │
└─────────────────────────────────────────────────────────────────┘


#══════════════════════════════════════════════════════════════════
#  SECTION 2: THE LOOK — VISUAL IDENTITY SYSTEM
#══════════════════════════════════════════════════════════════════

# ─── BACKGROUND [P0] ───────────────────────────────────────────
#
# Deep space black: #09090B
# NOT dark gray. BLACK. But infinite, not empty.
#
# MANDATORY: Add at least ONE texture layer on top of black:
#   a) Dot-grid pattern (1px dots, 40px spacing, primary color, 6-8% opacity)
#   b) Particle field (1-3px dots drifting upward, primary color, 10-15% opacity)
#   c) Subtle radial gradient (primary color at 3-5% from center)
#   d) Film grain noise (2-3% opacity, animated)
#
# NEVER flat solid backgrounds. The background is a STAGE, not a void.

# ─── COLOR [P0] ────────────────────────────────────────────────
#
# PRIMARY ACCENT: Pick ONE color. This is your brand.
#   Used for: emphasis, highlights, CTAs, key moments, ALL "pop".
#   NEVER appears flat — always gradient (lighter → base) + glow/bloom.
#
# SECONDARY PALETTE: 3-4 colors for data types/categories ONLY.
#   NEVER used randomly. Each color = a specific meaning.
#
# TEXT HIERARCHY:
#   Primary:   #FAFAFA (white)
#   Secondary: #A1A1AA (muted gray)
#   Tertiary:  #71717A (dim gray)
#
# SURFACES:
#   Glass morphism — backdrop-filter: blur(20-24px)
#   Borders: rgba(255,255,255,0.06)
#   NOT flat cards. NOT solid rectangles. GLASS. DEPTH. DIMENSION.

# ─── TYPOGRAPHY [P0] ──────────────────────────────────────────
#
# Font: Inter or equivalent geometric sans-serif (300-900 weights)
#
#   TYPE        WEIGHT  SIZE       TRACKING   USAGE
#   ──────────  ──────  ─────────  ────────   ─────────────────
#   Hero        900     80px+      -0.05em    Product name
#   Headline    700-900 48-96px    -0.03em    Scene titles
#   Subhead     400-500 20-28px    0          Scene descriptions
#   Label       600-700 11-13px    +0.08em    Categories, badges
#   Body        400     14-16px    0          Descriptions
#   Stat        900     80-110px   -0.04em    Big numbers
#
# MINIMUM SIZES (at 1080p): Body 24px, Headline 48px.
# If text can't be read on a phone, it's too small.

# ─── LIGHT & SHADOW [P1] ──────────────────────────────────────
#
# This is the single biggest difference between amateur and pro.
#
# 1. CONSISTENT LIGHT SOURCE: top-left, slightly warm.
#    Every shadow, every highlight follows this.
#
# 2. PRIMARY COLOR EMITS LIGHT.
#    When a primary-colored element appears, the darkness AROUND IT
#    subtly brightens. A 50-80px radius of soft primary glow.
#    This makes primary elements feel LUMINOUS, not just colored.
#
# 3. DEPTH OF FIELD.
#    Foreground = sharp. Background = subtle blur.
#    This sells 3D in a 2D medium.
#
# 4. REFLECTIONS.
#    Key UI elements: faint reflection below (8px offset, 30% opacity, blur).
#    Creates "floating in space" feel.
#
# 5. AMBIENT OCCLUSION.
#    Where elements meet surfaces: subtle dark gradient.
#    Grounds objects in space.


#══════════════════════════════════════════════════════════════════
#  SECTION 3: THE FEEL — MOTION PHYSICS
#══════════════════════════════════════════════════════════════════

# ─── EASING [P0 — THE MOST IMPORTANT TECHNICAL RULE] ──────────
#
# Default:    cubic-bezier(0.16, 1, 0.3, 1)  — ease-out-expo
#             Starts fast, decelerates smooth. APPLE'S SIGNATURE.
#
# Softer:     cubic-bezier(0.25, 0.46, 0.45, 0.94)  — ease-out-quart
#             For gentle, warm movements.
#
# DRAGON RULES (instant amateur if violated):
#   NEVER use linear easing on UI elements. EVER.
#   NEVER use bouncy/elastic easing. This isn't a cartoon.
#   NEVER use the same easing for everything. Vary intentionally.

# ─── ENTER ANIMATIONS [P0] ────────────────────────────────────
#
# Default: scale(0.92→1.0) + opacity(0→1) + translateY(20px→0)
# Duration: 0.5-0.7s with ease-out-expo
#
# Each element enters ONE AT A TIME or in small groups.
# NEVER everything simultaneously.
# NEVER an element appearing without animation.

# ─── EXIT ANIMATIONS [P1] ─────────────────────────────────────
#
# Reverse of enter, 30% faster (0.3-0.4s).
# OR: dissolve into particles for dramatic exits.
# NEVER just opacity 1→0. That's a PowerPoint fade.

# ─── STAGGER [P0] ─────────────────────────────────────────────
#
# Siblings: 0.07s delay between each.
#   NOT 0.1s (too slow, feels robotic).
#   NOT 0.04s (too uniform, feels mechanical).
#   0.07s creates ORGANIC rhythm. Like humans speaking in turns.
#
# Groups: 0.15-0.25s between major groups.
# Lists: 0.04s between items (fast but visible).

# ─── SPRING PHYSICS [P1] ──────────────────────────────────────
#
# For "settling" animations (card drops, button presses, pops):
#   stiffness: 300, damping: 25
#   The element slightly OVERSHOOTS then settles.
#   This is what makes things feel ALIVE, not programmed.

# ─── AMBIENT MOTION [P0 — ZERO EXCEPTIONS] ───────────────────
#
# EVERY "static" frame must have AT LEAST 2 of these:
#   a) Subtle particle drift (1-3px dots, upward, 10-15% opacity)
#   b) Gentle glow pulse (opacity 0.3→0.6→0.3, 3-4s cycle)
#   c) Slow parallax shift (background moves at 0.3x)
#   d) Breathing scale (1.0→1.02→1.0, 5s cycle)
#
# IF A FRAME HAS ZERO MOTION FOR MORE THAN 0.5s, IT HAS FAILED.
# This is non-negotiable. Dead frames = dead video.

# ─── CAMERA [P1] ──────────────────────────────────────────────
#
# Rule of thirds: key elements on third lines, not dead center
#   (unless deliberate "hero" moment like logo reveal).
#
# Parallax layers: background 0.3x, midground 0.6x, foreground 1.0x
#   Creates REAL depth in 2D.
#
# Zoom transitions: zoom INTO an element, emerge into next scene.
#   This is how you create INFINITE DEPTH.
#   Use at least 2 zoom transitions in the video.
#
# Rack focus: shift focus from foreground to background.
#   Cinematic. Use once or twice.
#
# Aspect ratio tricks: briefly pillarbox for drama, expand for release.
#
# NO dutch angles. This isn't a music video.
# NO whip-pans. This isn't an action movie.


#══════════════════════════════════════════════════════════════════
#  SECTION 4: THE MAGIC — POST-PRODUCTION EFFECTS
#══════════════════════════════════════════════════════════════════
#
# These are what separate "good" from "how is this possible."
# They're ordered by impact. Implement ALL of them.

# ─── BLOOM / GLOW [P0] ────────────────────────────────────────
#
# Every primary-colored element gets bloom:
#   Soft, bright glow extending 15-30px beyond the edge.
#   Glow pulses subtly (opacity 0.3→0.6→0.3, 3-4s cycles).
#   NEW primary elements: bloom flashes bright (1.0) then settles (0.4, 0.8s).
#
# WITHOUT bloom, primary elements look like colored rectangles.
# WITH bloom, they look like they're MADE OF LIGHT.
# This is the single most important visual effect.

# ─── PARTICLE SYSTEMS [P0] ────────────────────────────────────
#
# Present in EVERY SCENE. No exceptions.
#
# AMBIENT PARTICLES:
#   Tiny (1-3px) primary-colored dots drifting upward slowly.
#   Like embers. 10-15% opacity. Creates atmosphere of "alive."
#
# CONNECTION PARTICLES:
#   When two nodes connect: 3-5 particles travel along the edge
#   from source to target over 0.8s. Makes connections feel ACTIVE.
#
# DISSOLVE PARTICLES:
#   When elements disappear: break into 20-30 particles that drift
#   and fade over 1.2s. NOT "fade out." DISSOLVE.
#
# CELEBRATION PARTICLES:
#   Milestone moments: burst of 40-50 particles from center.

# ─── FILM GRAIN [P0] ──────────────────────────────────────────
#
# Ultra-subtle animated noise overlay at 2-3% opacity.
# Across the ENTIRE video. No exceptions.
#
# Why:
#   - Prevents color banding on dark gradients
#   - Adds organic texture (digital = sterile, grain = cinematic)
#   - Makes it feel like FILM, not screen recording
#
# If the grain is VISIBLE, it's too much. If it's ABSENT, it fails.

# ─── LIGHT RAYS / GOD RAYS [P2] ───────────────────────────────
#
# For the BIGGEST reveal (product name/logo):
#   4-6 subtle rays emanating from behind, 30% opacity, slow rotation.
#
# Use ONCE or TWICE in the entire video. Earned, not gratuitous.
# More than 2 = cheap. Zero = missed opportunity.

# ─── LENS FLARE [P2] ──────────────────────────────────────────
#
# EXACTLY ONE in the entire video.
# At the product logo/name reveal (Scene 4).
# Anamorphic horizontal streak, tinted primary, 0.6s.
#
# ONE makes it special. TWO makes it cheap. ZERO is fine too.
# But ONE is the sweet spot.

# ─── CHROMATIC ABERRATION [P2] ────────────────────────────────
#
# On fast-moving transitions only: 1-2px RGB channel offset.
# Sells SPEED and IMPACT.
#
# MUST be subtle. Felt, not seen.
# If you notice it consciously, it's 3x too strong.

# ─── VOLUMETRIC LIGHT [P2] ────────────────────────────────────
#
# For "warm" scenes (morning, welcome, optimism):
#   A light cone from above-left, as if sunlight through a window.
#   Dust particles float in the beam.
#
# Use once or twice for EMOTIONAL CONTRAST against the darkness.
# The contrast is what makes it powerful.

# ─── SCREEN CAPTURE REALISM [P1] ──────────────────────────────
#
# When showing app UI, it must look REAL:
#   - Realistic browser chrome (dark theme, minimal)
#   - Cursor moves on SMOOTH BEZIER paths, NOT linear
#   - Scroll behavior with MOMENTUM (deceleration)
#   - Hover states activate as cursor passes over elements
#   - Loading states and transitions between views
#   - Keyboard shortcuts briefly highlighted
#
# If the cursor moves in a straight line, it's obviously fake.
# Real humans move mice in CURVES with variable speed.


#══════════════════════════════════════════════════════════════════
#  SECTION 5: COMMON AI-GENERATED VIDEO MISTAKES
#══════════════════════════════════════════════════════════════════
#
# These are mistakes that AI video generators make OVER AND OVER.
# If you catch yourself doing any of these, STOP and fix it.
#
# 1. FLAT PACING
#    Every scene has the same energy level and duration.
#    FIX: Vary scene lengths. Some 10s, some 20s. Vary energy.
#
# 2. SIMULTANEOUS ENTRIES
#    All elements in a scene appear at the same time.
#    FIX: Stagger EVERYTHING. 0.07s between siblings.
#
# 3. LINEAR CURSOR MOVEMENT
#    The cursor moves in straight lines at constant speed.
#    FIX: Bezier curves. Variable speed. Hesitations. Overshoots.
#
# 4. NO BREATHING ROOM
#    Scene after scene with no pauses. No silence. No stillness.
#    FIX: After every major beat, 0.8-1.5s of calm. Let it land.
#
# 5. TOO MUCH TEXT
#    Paragraphs of text on screen. Bullet point lists.
#    FIX: Max headline + one subline per scene. That's it.
#
# 6. GENERIC TRANSITIONS
#    Every scene transition is the same cross-dissolve.
#    FIX: Mix transitions: cross-dissolve, zoom-in, slide, dissolve-to-particles.
#
# 7. STATIC BACKGROUNDS
#    Pure black with nothing happening behind the content.
#    FIX: Always particles, grid, gradient, or grain. ALWAYS.
#
# 8. COLOR WITHOUT GLOW
#    Primary color appears as flat color, not luminous.
#    FIX: Bloom on EVERY primary-colored element. No exceptions.
#
# 9. NO EMOTIONAL ARC
#    The video is informative but doesn't make you FEEL anything.
#    FIX: The problem must FRUSTRATE. The reveal must THRILL.
#         The features must AMAZE. The close must INSPIRE.
#
# 10. WEAK ENDING
#     The video just... stops. Or fades out with no punch.
#     FIX: The last 10 seconds must be the MOST emotionally
#          charged moment. End on a HIGH, not a fade.
#
# 11. NO AUDIO / SILENT VIDEO
#     The MP4 has no audio track at all. Just visuals.
#     FIX: Sound is 50% of the experience. Every visual event needs sound.
#          Background music is MANDATORY. SFX for key moments.
#          A silent video is a SCREENSAVER, not a film.
#          See Section 7 for the full sound design spec.
#
# 12. DELIVERING HTML INSTEAD OF MP4
#     The "video" is actually an HTML file with animations.
#     The user is told to "open in browser and screen-record."
#     FIX: HTML is the RENDER SOURCE, not the deliverable.
#          Use Playwright/Puppeteer to capture video, then FFmpeg
#          to encode as MP4 with audio. See Section 0 for the pipeline.
#          An HTML file alone is a FAILED deliverable.


#══════════════════════════════════════════════════════════════════
#  SECTION 6: THE 15-SCENE BLUEPRINT
#══════════════════════════════════════════════════════════════════
#
# This structure works for ANY product. The emotional arc is fixed.
# The CONTENT adapts to your product. Follow the arc.
#
# Replace [brackets] with your product's specific content.
# The [EMOTION] and [PURPOSE] are fixed — don't change them.
#
# ────────────────────────────────────────────────────────────────
#  SCENE MAP (with energy levels)
# ────────────────────────────────────────────────────────────────
#
#  #   TIME       NAME             ENERGY    PURPOSE
#  ──  ─────────  ───────────────  ────────  ─────────────────────
#  1   0:00-0:16  THE VOID         ▁▁▂▃▅     Hook + establish aesthetic
#  2   0:16-0:36  THE CHAOS        ▃▃▄▃▂     Make them FEEL the problem
#  3   0:36-0:58  THE COST         ▃▃▅▅▃     Quantify the pain with data
#  4   0:58-1:18  THE REVEAL       ▅▅▇▇▇     Hero moment. Product appears.
#  5   1:18-1:44  FEATURE: ALIVE   ▆▆▆▅▅     Most visual/dynamic feature
#  6   1:44-2:04  FEATURE: SMART   ▅▅▆▆▅     AI/automation feature
#  7   2:04-2:28  FEATURE: CHAT    ▅▅▆▆▅     Conversational/query feature
#  8   2:28-2:44  FEATURE: ORG     ▅▅▅▅▅     Organization/management feature
#  9   2:44-2:58  METRICS          ▅▅▆▅▅     Analytics/scores/charts
#  10  2:58-3:18  COMPARISON       ▅▅▇▅▅     Why this product wins
#  11  3:18-3:32  TEAM             ▅▅▆▆▅     Collaboration/multi-user
#  12  3:32-3:46  TRUST            ▃▃▄▄▃     Security/architecture
#  13  3:46-4:02  SOCIAL PROOF     ▃▃▄▃▃     Testimonials
#  14  4:02-4:18  PRICING          ▃▃▅▅▃     Plans + CTA
#  15  4:18-4:36  THE FINALE       ▅▅▇▇▉     Emotional peak. Close.
#
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
#  SCENE 1: THE VOID (0:00 – 0:16)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▁▁▂▃▅  (zero → rising)
#  PURPOSE: Hook in 3 seconds. Create tension. Establish aesthetic.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Pure black. Film grain only. Hold 2 FULL SECONDS.
#        The emptiness creates anticipation. DO NOT RUSH THIS.
#
#  2.0s  A single point of light in [primary color]. Center screen.
#        2px. Pulses once (opacity 0.3→1.0→0.6, 1s).
#        A RIPPLE RING expands outward from it and fades.
#
#  3.5s  The point splits into two. A connection DRAW between them —
#        traveling like a spark along a wire (0.4s).
#        When it reaches the second point, that point pulses.
#
#  4.5s  Both split again. More connections. Network grows ORGANICALLY.
#        Each node: micro-ripple on appear. Each connection: spark.
#        This should feel like neurons forming. Bioelectric. ALIVE.
#
#  7.0s  Network has ~25 nodes. Beautiful. Different category colors
#        emerging. Connections cross and weave.
#
#  8.0s  Camera SLOWLY pushes in (zoom 1.0→1.3x over 3s).
#        Parallax: background particles 0.3x, network 1.0x.
#
#  9.5s  Network begins to STRAIN — connections stretch, glitch:
#        brief 1px position offsets, momentary opacity dips.
#        Something is wrong.
#
# 11.0s  Network SHATTERS. Not all at once — one snap, then another,
#        then cascade. Each snap = micro-flash. Nodes drift apart.
#        Beautiful destruction.
#
# 12.5s  Near-darkness. A few orphaned nodes drift.
#
# 13.0s  [YOUR MANIFESTO/LINE] appears — words materializing from
#        colored particles that swirl and condense, one word at a time.
#        The LAST word lands with a subtle camera shake (2px, 0.1s).
#
# 15.0s  Below, in [primary color] with soft glow:
#        [YOUR TAGLINE]
#
# 16.0s  Cross-dissolve to Scene 2.

# ────────────────────────────────────────────────────────────────
#  SCENE 2: THE CHAOS (0:16 – 0:36)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▃▃▄▃▂  (tense → chaotic → deflating)
#  PURPOSE: Make them FEEL the problem. Not describe it. SHOW it.
#  TRANSITION TO NEXT: Dissolve into particles
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Scattered fragments across viewport — glass-morphism cards
#        each representing [a tool/concept in the user's scattered workflow].
#        Each has icon + label. Float gently (sinusoidal, different phases).
#        Beautiful individually. CHAOTIC together.
#        NO connections. NO order.
#
#  3.0s  Fragments move FASTER. More erratic. More overlapping.
#
#  5.0s  Headline materializes center, pushing fragments aside:
#        "Your [workflow/data/process] is scattered across [N]+ tools"
#        Number in [primary color] with glow.
#
#  7.0s  Fragments start GLITCHING:
#        - Random 2px position jumps (every 0.3s)
#        - Brief opacity dips to 0.3
#        - Text labels briefly corrupt
#        - Connection lines flash between fragments but FAIL (20% then snap)
#
#  9.0s  Headline changes (old dissolves down, new rises up):
#        "None of them talk to each other."
#        Hits harder because we SAW the connection attempts fail.
#
# 11.0s  Everything FREEZES. Then fragments slowly shrink and dim,
#        converging toward center.
#
# 13.0s  Just before meeting, they DISSOLVE into particles
#        (each card → 15-20 embers drifting upward and fading).
#
# 14.0s  Beat of silence. Cross-dissolve to Scene 3.

# ────────────────────────────────────────────────────────────────
#  SCENE 3: THE COST (0:36 – 0:58)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▃▃▅▅▃  (heavy → impactful → settling)
#  PURPOSE: Quantify the pain. Make it undeniable with DATA.
#  TRANSITION TO NEXT: Glass shatter into particles
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Dark screen. Subtle particles drifting upward (lost things).
#
#  1.5s  STAT 1: Giant number counter 0→[N] over 2s.
#        ENORMOUS — fills ~40% of screen height.
#        [Primary] gradient + bloom. Each digit change = screen pulse.
#        Below: [stat label] in muted text.
#
#  3.5s  Hold 0.8s. Stat drifts to left third, shrinks to 60%.
#
#  4.3s  STAT 2: Counter 0→[N]% over 2s. Same treatment.
#        Below: [stat label].
#
#  6.3s  Hold 0.8s. Stat drifts to right third.
#
#  7.1s  STAT 3: Counter $0→$[N]M over 2.5s.
#        Currency symbol first, then numbers roll, suffix last
#        with subtle camera shake.
#        Below: [stat label].
#
#  9.6s  All three stats visible simultaneously (left/center/right).
#        They pulse ONCE together — shared heartbeat.
#
# 10.5s  Stats CRACK — fracture lines (like breaking glass).
#        Through the cracks, [primary]-colored light glows behind.
#
# 11.5s  Stats SHATTER. Glass-shard particle explosion.
#        40-50 shards per number, reflecting colored light.
#        Shards tumble and fade.
#
# 12.5s  Black. Cross-dissolve to Scene 4.

# ────────────────────────────────────────────────────────────────
#  SCENE 4: THE REVEAL (0:58 – 1:18)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▇▇▇  (building → THE PEAK)
#  PURPOSE: The hero moment. The product appears. UNFORGETTABLE.
#  TRANSITION TO NEXT: Zoom INTO the logo
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Black. A HORIZONTAL STREAK of [primary] light SWEEPS
#        across screen (0.6s). Band of light ~100px tall,
#        bright core, soft falloff, like a scanner.
#
#  0.6s  As the sweep passes, it REVEALS a subtle dot-grid pattern
#        (1px dots, 40px spacing, [primary] color, 8% opacity).
#        They were always there. The light just showed them.
#
#  1.5s  Grid pulses once (dots brighten to 20%, 0.3s, return to 8%).
#
#  2.0s  [PRODUCT LOGO] forms, center screen:
#
#        Step 1 (0.5s): Main shape fades in from center outward.
#        Ripple becoming solid. Inner gradient for 3D curvature.
#
#        Step 2 (1.0s): Internal details DRAW (SVG stroke-dashoffset).
#        Left side first (0.5s), then right (0.5s).
#        Each stroke has a bright "leading edge" at the drawing tip.
#
#        Step 3 (0.4s): Accent details pop in with SPRING PHYSICS.
#        Overshoot to 1.15x, settle to 1.0x. Staggered 0.07s.
#        Each pop emits a tiny ripple.
#
#        Step 4 (0.3s): Connecting elements draw themselves.
#        Sparks travel along completed paths.
#
#  4.2s  Logo pulses: scale 1.0→1.06→1.0, glow brightens→dims.
#        THE ONE LENS FLARE: anamorphic horizontal streak,
#        tinted [primary], 0.6s.
#
#  5.0s  [PRODUCT NAME] appears via REVEAL:
#        A bright line sweeps across text left→right.
#        Letters REVEALED behind it.
#        Huge text (80px+), weight 900, tracking -0.05em, white.
#
#  6.5s  Let the name BREATHE. Its presence is commanding.
#
#  7.0s  Subtitle types character by character (0.03s each):
#        [YOUR TAGLINE]
#        Tiny [primary] cursor blinks at end, blinks twice more, fades.
#
#  9.0s  Logo pulses again. Grid brightens. Everything alive.
#
# 10.0s  Beat of stillness. Then camera PUSHES IN toward logo
#        (zoom 1.0→2.5x over 1.5s). We pass THROUGH it
#        and emerge into Scene 5. ZOOM TRANSITION.

# ────────────────────────────────────────────────────────────────
#  SCENE 5: FEATURE — THE "ALIVE" FEATURE (1:18 – 1:44)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▆▆▆▅▅  (high sustained)
#  PURPOSE: Most visual/dynamic feature. The "wow" feature.
#  TRANSITION TO NEXT: Zoom INTO an element
# ────────────────────────────────────────────────────────────────
#
#  WHAT THIS IS FOR YOUR PRODUCT:
#    Knowledge app  → knowledge graph forming
#    Design tool    → canvas elements connecting
#    Data tool      → visualizations drawing themselves
#    Dev tool       → code flowing and compiling
#    AI tool        → neural network activating
#    Finance tool   → transaction flows visualizing
#    Any app        → the most VISUALLY DYNAMIC thing it does
#
#  0.0s  Emerge from zoom into vast dark space.
#        Single [primary]-colored node/element, center. Pulses.
#
#  1.0s  Second element appears (spring). Connection draws (0.3s),
#        spark traveling. When complete, particles travel along edge.
#
#  2.0s  More elements — each ripple + spring, different category
#        colors. Connections with traveling particles. GROWING.
#
#  3.5s  Growth accelerates — 2-3 at a time. Camera pulls back.
#        Parallax depth.
#
#  6.0s  ~30+ elements, ~40+ connections. Fills ~60% of screen.
#
#  7.0s  CURSOR appears — white dot with [primary] trail.
#        Smooth bezier path. Elements grow (1.0→1.1x) as it nears.
#        Cursor moves with PURPOSE.
#
#  8.5s  Cursor hovers an element. PREVIEW CARD pops out:
#        Glass morphism. Title, type badge, preview, metadata.
#        Spring physics, overshoot, settle.
#
# 10.0s  Cursor moves on. Card closes. Visualization pulses.
#
# 11.5s  Headline top-center: "[Feature line] — [key word] in [primary]"
#        Doesn't cover the visualization (top 15% only).
#        Subtext below headline.
#
# 14.0s  Zoom INTO an element (1.0→8x, 1.5s).
#        Pass through → emerge into Scene 6.

# ────────────────────────────────────────────────────────────────
#  SCENE 6: FEATURE — THE "SMART" FEATURE (1:44 – 2:04)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▆▆▅  (warm → bright → settling)
#  PURPOSE: AI/automation/intelligence. Something that thinks for you.
#  TRANSITION TO NEXT: Card slides to side, making room for Scene 7
# ────────────────────────────────────────────────────────────────
#
#  WHAT THIS IS FOR YOUR PRODUCT:
#    Knowledge app  → morning digest / daily summary
#    Design tool    → AI layout suggestions
#    Data tool      → automated insights / anomaly detection
#    Dev tool       → AI code review / auto-fix
#    Productivity   → smart summaries / priority inbox
#    Finance tool   → spending insights / forecast
#    Any app        → something the AI does AUTOMATICALLY
#
#  0.0s  Warm glow rises from bottom (volumetric light, amber/golden).
#        Light cone as if sunlight through window.
#        Dust particles float in the beam.
#
#  2.0s  Headline: "[Feature line] — [key word] in [primary]"
#        Text appears in the lit area, light REVEALS it.
#
#  3.5s  Card/interface materializes — rising from below, spring physics.
#        Glass-dark card containing:
#        - Header label (uppercase, small, [primary] color)
#        - AI-generated content appearing LINE BY LINE
#          (gradient bars filling, OR typing animation)
#        - 2-3 insight/action cards sliding in from right,
#          staggered, each with colored left-border accent
#        - Optional: progress bars, status badges, mood indicators
#
#  7.5s  Subtext: "[Feature description]"
#
#  9.0s  Card gently scales down and moves to one side,
#        making room for Scene 7. SMOOTH TRANSITION —
#        both features briefly COEXIST. Continuity.

# ────────────────────────────────────────────────────────────────
#  SCENE 7: FEATURE — THE "CONVERSATIONAL" FEATURE (2:04 – 2:28)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▆▆▅  (building → magical → satisfied)
#  PURPOSE: Product responds to user input in real-time.
#  TRANSITION TO NEXT: Both features scale down, cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  WHAT THIS IS FOR YOUR PRODUCT:
#    Knowledge app  → AI chat with sources
#    Design tool    → natural language to design
#    Data tool      → query interface / SQL from text
#    Dev tool       → AI pair programming
#    Any app        → command palette / search
#
#  0.0s  Scene 6's card on one side. Conversational UI slides in.
#
#  1.0s  Headline: "Ask anything. [Product] knows." — [Product] in [primary]
#
#  2.0s  User message bubble slides from right:
#        [primary] gradient background, white text, spring physics.
#
#  3.5s  AI response appears — dark surface. Text streams WORD BY WORD
#        (0.035s per word) with blinking [primary] cursor.
#        Key terms appear in [primary] then settle to white with underline.
#        This shows the AI pulls from SPECIFIC knowledge, not generic.
#
#  7.0s  Text completes. Cursor blinks twice, disappears.
#        SOURCE/REFERENCE badges pop in below (staggered 0.1s):
#        small pills with category colors, each with tiny pulse.
#        Optional: connection lines from badges to text portions.
#
#  9.0s  Feedback icon appears (thumbs up, checkmark). Subtle pulse.
#        Subtext: "[Feature description]"
#
# 11.0s  Both features scale down. Cross-dissolve to Scene 8.

# ────────────────────────────────────────────────────────────────
#  SCENE 8: FEATURE — THE "ORGANIZATION" FEATURE (2:28 – 2:44)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▅▅▅  (steady, satisfying)
#  PURPOSE: How the product organizes/manages content.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  WHAT THIS IS FOR YOUR PRODUCT:
#    Knowledge app  → typed notes grid
#    Design tool    → asset library / component library
#    Data tool      → dataset manager
#    Dev tool       → project files / repo view
#    Any app        → categorized content / collections
#
#  0.0s  Headline: "Capture everything. [Key promise]" — promise in [primary]
#        Subtext: "[N] types, smart categorization, instant search."
#
#  2.0s  Grid of cards appears. Each does a 3D FLIP reveal.
#        Face-down → rotates on Y-axis → reveals content.
#        Staggered 0.1s. Perspective 800px.
#
#        Each card: colored left border (3px), type badge (uppercase, 11px),
#        title (14px bold), preview (12px muted), tag pill.
#        Different types = different colors.
#
#  5.0s  Tags gently float upward 5px, settle (spring).
#
#  6.0s  Search bar appears. Cursor types query (0.08s/char).
#        Grid FILTERS IN REAL-TIME: non-matching dim (30% opacity, 0.95x),
#        matching brighten (1.02x). Spring transitions.
#
#  8.0s  Search clears. All cards spring back to full visibility.
#
#  9.5s  Cross-dissolve to Scene 9.

# ────────────────────────────────────────────────────────────────
#  SCENE 9: ANALYTICS / METRICS (2:44 – 2:58)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▆▅▅  (building → satisfying peak → settling)
#  PURPOSE: Measurable results. Scores, charts, numbers.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Headline: "Measure [what matters]" — in [primary]
#
#  1.5s  CIRCULAR GAUGE, center-left:
#        Arc draws clockwise to ~87% over 2s.
#        Leading edge has bright glow.
#        Inside: number 0→[N] counts up (2s), weight 900, 56px,
#        [primary] gradient text.
#
#  3.5s  3-4 PROGRESS BARS, center-right (staggered 0.12s):
#        Each: label (uppercase, 11px), bar (6px, rounded), value counting up.
#        Different colors per bar.
#
#  6.0s  Mini AREA CHART draws itself below:
#        7-day sparkline. Line draws left→right (1s),
#        gradient fill fades in (0.5s). [Primary] gradient.
#
#  7.5s  Subtext: "[Metric description]"
#
#  8.5s  Cross-dissolve to Scene 10.

# ────────────────────────────────────────────────────────────────
#  SCENE 10: COMPARISON (2:58 – 3:18)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▇▅▅  (confident → THE MIC DROP → settling)
#  PURPOSE: Why THIS product wins. Objectively. Undeniably.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Headline: "Not just another [competitor category]"
#        — category in [primary] with subtle glow.
#
#  1.5s  Comparison table RISES from bottom.
#        Glass-dark, subtle grid lines.
#        Columns: [Feature] | [Your Product] | [Competitor 1] | [Competitor 2]
#
#  3.0s  Header row first — your product's header in [primary] + glow,
#        others muted white.
#
#  3.5s  Feature rows stagger in (0.25s each), sliding from right:
#        Your product: ✓ in [primary] (spring pop + glow per checkmark)
#        Competitors: ✗ (dim) or △ (orange, partial)
#        Pick 5-6 features where you WIN.
#
#  6.0s  Your product's column gets [primary] background gradient
#        sweeping down (0.5s). Other columns dim to 0.7 opacity.
#
#  7.5s  Your column header scales up (1.0→1.15→1.0) + bright glow.
#        THE MIC DROP MOMENT.
#
#  8.5s  Hold. Cross-dissolve to Scene 11.

# ────────────────────────────────────────────────────────────────
#  SCENE 11: TEAM / COLLABORATION (3:18 – 3:32)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▆▆▅  (multiplying → magical → awe)
#  PURPOSE: Product for groups. Multiple users. Shared value.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Scene 5's visualization reappears — LARGER, more complex.
#        Pulsing with life.
#
#  1.0s  THREE cursors appear simultaneously — different colors,
#        different team members. Independent smooth bezier paths.
#
#  3.0s  Each cursor creates new elements where it "clicks".
#        MAGIC: connections auto-form between DIFFERENT team members'
#        elements. The product connects work ACROSS people.
#
#  5.0s  Cross-team connections get SPECIAL treatment:
#        BRIGHT spark travels along, both elements pulse.
#        This is the IMPOSSIBILITY MOMENT.
#
#  7.0s  Headline: "Built for [teams]" — key word in [primary]
#        Subtext: "[Collaboration promise]"
#
#  8.5s  Visualization zooms OUT to show scale. Awe.
#        Cross-dissolve to Scene 12.

# ────────────────────────────────────────────────────────────────
#  SCENE 12: TRUST / SECURITY / ARCHITECTURE (3:32 – 3:46)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▃▃▄▄▃  (solid → confident → grounded)
#  PURPOSE: Serious. Reliable. Trustworthy. Enterprise-grade.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Stylized GLOBE assembles from wireframe circles.
#        3 orbital rings at different angles, low-opacity [primary].
#        Region dots. Slow rotation.
#
#  2.0s  SHIELD/LOCK draws itself (SVG stroke, [primary], 0.8s).
#        Checkmark/key draws after outer shape.
#        Fills with subtle [primary] gradient.
#
#  3.5s  Data channels animate around globe — thin lines tracing
#        between region dots. Dots pulse when reached.
#
#  5.0s  Headline: "[Trust headline]. [Key promise] in [primary]"
#        Subtext: "[Architecture description]"
#        Optional: technology name in [primary] with glow.
#
#  7.0s  Hold. Cross-dissolve to Scene 13.

# ────────────────────────────────────────────────────────────────
#  SCENE 13: SOCIAL PROOF (3:46 – 4:02)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▃▃▄▃▃  (warm → trusting → validated)
#  PURPOSE: Real people, real results. Peer validation.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  3 testimonial cards slide in from alternating sides
#        (left, right, left), staggered 0.3s:
#        - Glass-dark, avatar circle with initials, name + role
#        - Stars pop one by one (0.08s each): ★★★★★
#        - Italic quote. Key metrics in [primary] color.
#        - Different accent colors per card border.
#
#  6.0s  Row of company/team names fades in below:
#        Muted text, spaced evenly.
#
#  8.0s  Hold. Cross-dissolve to Scene 14.

# ────────────────────────────────────────────────────────────────
#  SCENE 14: PRICING (4:02 – 4:18)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▃▃▅▅▃  (simple → clear → confident)
#  PURPOSE: Accessible. No friction. Easy decision.
#  TRANSITION TO NEXT: Cross-dissolve
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Headline: "Simple, transparent [pricing]" — in [primary]
#
#  1.5s  3 pricing cards RISE from below (translateY 60→0, spring,
#        staggered 0.12s):
#
#        FREE/STARTER:
#          Basic features, secondary CTA button
#
#        PRO/STANDARD (FEATURED):
#          [Primary] border + GLOW, "Most Popular" badge,
#          [primary] CTA button, best value features
#
#        ENTERPRISE/CUSTOM:
#          All features, secondary CTA button
#
#  4.0s  Feature items stagger in per card (0.04s each).
#
#  6.0s  Featured card CTA pulses with glow (0.3→0.7→0.3, 2s).
#
#  8.0s  Hold. Cross-dissolve to Scene 15.

# ────────────────────────────────────────────────────────────────
#  SCENE 15: THE FINALE (4:18 – 4:36)
# ────────────────────────────────────────────────────────────────
#  ENERGY: ▅▅▇▇▉  (building → THE HIGHEST PEAK)
#  PURPOSE: Seal the deal. Make them ACT. Emotional climax.
#  TRANSITION: Slow fade to black (2s)
# ────────────────────────────────────────────────────────────────
#
#  0.0s  Core visualization fills ENTIRE screen — massive, pulsing.
#        Particles drift. Sparks travel. ALIVE. EVERYWHERE.
#        This is the CULMINATION of everything shown.
#
#  2.0s  Visualization dims to 25% — luminous background.
#        Product logo fades in center (80px, completed from Scene 4).
#
#  3.5s  First line fades up (0.8s), large, white:
#        "Stop [core pain point]"
#        Hold 1.5s.
#
#  5.0s  Second line fades up below, SAME SIZE, in [PRIMARY] WITH GLOW:
#        "Start [core action / product name]"
#        The glow expands, briefly brightening the background.
#        THIS IS THE EMOTIONAL PEAK OF THE ENTIRE VIDEO.
#
#  6.5s  Large CTA button materializes (spring physics):
#        "Get started free →"
#        [Primary] gradient, white text, 18px.
#        Shadow creates pool of [primary] light beneath it.
#
#  7.5s  Below: [product URL] in muted text, 20px.
#
#  8.0s  CTA pulses: glow 100% → settles (1s).
#        Logo pulses in sync: scale 1.0→1.1→1.0 with glow.
#
#  9.0s  HOLD. Breathe. Background pulses gently.
#        [Primary] glow creates warm, inviting atmosphere.
#        This is the moment of DECISION.
#
# 11.0s  SLOW fade to black — 2 FULL SECONDS.
#        [Primary] glow is the LAST thing visible.
#        It lingers like an afterimage.
#
# 13.0s  Black. Film grain only. Hold 1s.
#
# 14.0s  A single [primary]-colored dot appears center, 0.5s.
#        The SAME dot from Scene 1. Then fades.
#        Full circle. The end.


#══════════════════════════════════════════════════════════════════
#  SECTION 7: SOUND DESIGN — [P0] MANDATORY, NOT OPTIONAL
#══════════════════════════════════════════════════════════════════
#
#  ┌─────────────────────────────────────────────────────────────────┐
#  │  A VIDEO WITHOUT SOUND IS NOT A FILM. IT IS A SCREENSAVER.    │
#  │  SOUND IS [P0]. NO EXCEPTIONS. NO "IF AUDIO IS SUPPORTED."    │
#  │  EVERY MP4 MUST CONTAIN AN AUDIO TRACK.                        │
#  └─────────────────────────────────────────────────────────────────┘
#
#  WHY THIS MATTERS:
#    - Apple never ships a silent keynote. NEVER.
#    - Sound creates 50% of the emotional impact.
#    - A "beautiful silent video" is an oxymoron at this quality level.
#    - The reveal without a bass swell is just a logo appearing.
#    - The shatter without glass sound is just shapes moving.
#    - WITHOUT SOUND, EVERYTHING IN SECTIONS 1-5 LOSES 50% OF ITS POWER.
#
#  SOUND IS NOT A POST-PRODUCTION AFTERTHOUGHT.
#  SOUND IS A FIRST-CLASS CITIZEN OF THE FILM.
#  PLAN FOR IT FROM THE START.
#
#  ─── HOW TO ADD AUDIO — TECHNICAL APPROACHES ─────────────────
#
#  APPROACH A: Web Audio API in the HTML (RECOMMENDED for Playwright)
#    - Build the audio directly into the HTML animation using
#      AudioContext, OscillatorNode, GainNode, etc.
#    - Synchronize sound events with GSAP timeline callbacks.
#    - Playwright's recordVideo captures the audio alongside video.
#    - This is the cleanest approach — one file, sync is automatic.
#
#  APPROACH B: Generate audio file separately, merge with FFmpeg
#    - Create a music/soundtrack file (MP3/WAV) using:
#      * TTS API for narration
#      * Music generation API for background score
#      * Pre-recorded sound effects library
#    - Merge with video using FFmpeg:
#      ffmpeg -i video.webm -i soundtrack.mp3 \
#             -c:v libx264 -c:a aac -shortest \
#             product-launch.mp4
#
#  APPROACH C: Combine both
#    - Web Audio API for sound effects (synced to animation)
#    - Background music as separate file, mixed in with FFmpeg
#    - ffmpeg -i video_with_sfx.webm -i music.mp3 \
#             -filter_complex "[1:a]volume=0.3[music];[0:a][music]amix=inputs=2:duration=longest[a]" \
#             -map 0:v -map "[a]" -c:v libx264 -c:a aac \
#             product-launch.mp4
#
#  ─── SOUND EFFECTS [P0] ──────────────────────────────────────
#
#  EVERY major visual event MUST have a corresponding sound.
#  This is the audio-visual contract. Break it = break immersion.
#
#  ┌────────────────────────┬───────────────────────────────────┐
#  │ Moment                 │ Sound                             │
#  ├────────────────────────┼───────────────────────────────────┤
#  │ Scene 1 dot pulse      │ Soft bass hit, reverb tail        │
#  │ Connections forming    │ Tiny crystalline "tink" each      │
#  │ Network shattering     │ Glass break, reversed, lowpassed  │
#  │ Stat counters          │ Subtle digital tick per increment │
#  │ Product logo reveal    │ Deep resonant bass swell          │
#  │ Product name reveal    │ Subtle impact + reverb            │
#  │ Text typing            │ Soft key clicks, very muted       │
#  │ AI streaming           │ Gentle electronic hum             │
#  │ Cursor hover           │ Micro "whoosh" (barely audible)   │
#  │ Card pop-in            │ Soft "thud" with spring tail      │
#  │ Particle bursts        │ Gentle sparkle/shimmer            │
#  │ Transitions (zoom)     │ Subtle rushing air / whoosh       │
#  │ Comparison checkmarks  │ Satisfying "ding"                 │
#  │ Stats shattering       │ Glass crack + deep impact         │
#  │ Closing CTA            │ Uplifting chord, major key        │
#  │ Final dot fade         │ Soft reverb tail, fading to silence│
#  └────────────────────────┴───────────────────────────────────┘
#
#  Sound effect principles:
#    - SOUNDS ARE FELT, NOT HEARD. If any SFX is jarring, it's 3x too loud.
#    - Every SFX should be at 30-50% of what you think it should be.
#    - Layer: background music (loudest) → SFX (medium) → silence (rest).
#    - NEVER use stock "corporate" sounds. Generate or curate carefully.
#
#  ─── BACKGROUND MUSIC [P0] ───────────────────────────────────
#
#  The music IS the emotional arc. It's not decoration.
#  The energy waveform in Section 1 applies to MUSIC too.
#
#  Ambient electronic. Arc follows the energy waveform:
#    - Scenes 1-3: Minimal, dark, tension-building. Low drones.
#                   Sparse piano. Reverb-heavy. BREATHING.
#    - Scene 4:    Bass swell → hopeful emergence. First melody.
#                   THE TRANSFORMATION MOMENT in audio form.
#    - Scenes 5-9: Warm, rhythmic, optimistic. Full arrangement.
#                   Percussion enters. Energy sustained.
#    - Scene 10:   Drops to minimal. Comparison = serious moment.
#                   Music pulls back. Let the data speak.
#    - Scenes 11-14: Building again. Energy rising. Layers added.
#    - Scene 15:   FULL POWER. Emotional peak. All instruments.
#                   Then 2s of silence. Then the final note.
#                   The silence before the end is CRUCIAL.
#
#  Reference artists: Jon Hopkins, Olafur Arnalds, Nils Frahm,
#  Max Richter, Hania Rani.
#
#  Music mixing rules:
#    - Music should be at -20dB to -15dB during narration/text
#    - Music can swell to -10dB during pure visual moments
#    - Music DUCKS when SFX play (sidechain compression)
#    - The mix should feel like ONE unified sound, not layers
#
#  ─── OPTIONAL: VOICEOVER / NARRATION [P2] ────────────────────
#
#  If you choose to add voiceover:
#    - Use TTS with a calm, confident, slightly warm voice
#    - Speak ONLY during Scene 4 (reveal) and Scene 15 (finale)
#    - 3-5 words maximum. e.g. "This changes everything."
#    - Volume: below music. The voice SUPPORTS the visuals, not vice versa.
#    - NEVER narrate the entire video. This isn't a tutorial.


#══════════════════════════════════════════════════════════════════
#  SECTION 8: THE ABSOLUTE DON'TS
#══════════════════════════════════════════════════════════════════
#
#  [P0] NEVER deliver HTML instead of MP4. The output is an MP4 FILE.
#  [P0] NEVER deliver a silent video. Audio track is MANDATORY.
#  [P0] NEVER use hard cuts between scenes. ALWAYS smooth transitions.
#  [P0] NEVER have a static frame with zero motion for >0.5s.
#  [P0] NEVER use linear easing on UI elements. EVER.
#  [P0] NEVER show primary color without gradient + glow.
#  [P0] NEVER use flat solid backgrounds. Always textured.
#  [P0] NEVER rush the opening 3 seconds.
#  [P0] NEVER end without a powerful closing CTA.
#
#  [P1] NEVER use text-heavy slides (max: headline + one subline).
#  [P1] NEVER use fonts below 24px body / 48px headlines.
#  [P1] NEVER use bouncy/elastic easing (not a cartoon).
#  [P1] NEVER animate everything simultaneously (stagger always).
#  [P1] NEVER use emoji in the video.
#  [P1] NEVER use generic stock footage.
#  [P1] NEVER use clip-art or cheap icons.
#  [P1] NEVER use corporate jargon in text (speak human).
#  [P1] NEVER use the same transition for every scene change.
#  [P1] NEVER show a cursor moving in a straight line.
#
#  [P2] NEVER use more than ONE lens flare in the entire video.
#  [P2] NEVER use dutch angles (not a music video).
#  [P2] NEVER use chromatic aberration noticeably (felt, not seen).
#  [P2] NEVER use more than 2 god ray moments.


#══════════════════════════════════════════════════════════════════
#  SECTION 9: FINAL QUALITY CHECKLIST
#══════════════════════════════════════════════════════════════════
#
#  Before delivering, verify EVERY item. No exceptions.
#
#  [P0] MUST-HAVE (missing = failure):
#  □ Output is an MP4 file (not HTML, not WebM, not GIF).
#  □ MP4 contains both video AND audio tracks.
#  □ Audio track has background music (not silent).
#  □ Audio track has sound effects for major visual events.
#  □ Video is minimum 3 minutes (180s). Target: 4:18+.
#  □ Resolution is 1920×1080 (Full HD).
#  □ Every frame has at least ONE ambient animation.
#  □ All scene transitions are smooth (no hard cuts).
#  □ Primary accent color is consistent (never random colors).
#  □ All text readable at 1080p on phone.
#  □ All number counters animate from 0 (never static).
#  □ The pacing has VARIETY (not all fast, not all slow).
#  □ Opening 3 seconds are visually arresting.
#  □ Closing 10 seconds create emotional response.
#  □ Film grain overlay present throughout (2-3%).
#  □ Bloom/glow on ALL primary-colored elements.
#  □ Particle systems active in every scene.
#
#  [P1] CRITICAL (missing = noticeable gap):
#  □ At least 3 "impossibility moments".
#  □ At least 2 zoom transitions (spatial depth).
#  □ Product logo reveal has the ONE lens flare.
#  □ Comparison scene makes product look undeniable.
#  □ Scene 4 (reveal) is the emotional FIRST peak.
#  □ Scene 15 (finale) is the emotional HIGHEST peak.
#  □ Sound design matches visual energy (music arc = visual arc).
#  □ Cursor movements are bezier curves, never linear.
#  □ At least 2 different transition types used.
#
#  [P2] ELEVATION (having = legendary):
#  □ Volumetric light used once or twice.
#  □ Chromatic aberration on fast transitions.
#  □ Rack focus used once.
#  □ Aspect ratio trick (pillarbox) used once.
#  □ Reflections on key UI elements.


#══════════════════════════════════════════════════════════════════
#  SECTION 10: THE NORTH STAR
#══════════════════════════════════════════════════════════════════
#
#  When someone watches this video, they should feel ONE thing:
#
#           "This is the future."
#
#  Not "that's a nice app."
#  Not "cool animations."
#  Not "good design."
#
#  "This is the FUTURE."
#
#  If they don't feel that, the video has failed.
#  Every single decision — every easing curve, every particle,
#  every transition, every word — serves this one feeling.
#
#  The problem must FRUSTRATE them.
#  The reveal must THRILL them.
#  The features must AMAZE them.
#  The comparison must CONVINCE them.
#  The close must INSPIRE them.
#
#  Make them believe it.
