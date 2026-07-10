"""
Generate the audio track for the Vigie product launch video.

Creates a 180-second WAV file with:
- Ambient drone background (sine waves at 55Hz + 82.4Hz)
- Bass hits at scene transitions
- Crystalline tinks for UI events
- Whoosh transitions
- Final uplifting chord

Matches the visual timeline of vigie_video.html.
"""
import numpy as np
from scipy.io import wavfile
from pathlib import Path

SAMPLE_RATE = 44100
DURATION = 182  # seconds (180 + 2s buffer)
OUTPUT_PATH = Path("/home/z/my-project/scripts/video_output/vigie_audio.wav")

def generate_audio():
    print(f"Generating {DURATION}s audio track...")
    total_samples = SAMPLE_RATE * DURATION
    t = np.arange(total_samples) / SAMPLE_RATE

    # ═══ MASTER AUDIO ═══
    master = np.zeros(total_samples, dtype=np.float64)

    # ═══ BACKGROUND DRONE ═══
    # Root drone (55Hz A1)
    drone1 = np.sin(2 * np.pi * 55 * t) * 0.15
    # Fifth drone (82.4Hz E2)
    drone2 = np.sin(2 * np.pi * 82.4 * t) * 0.10
    # Slow LFO breathing (0.15Hz)
    lfo = np.sin(2 * np.pi * 0.15 * t) * 0.05
    drone = (drone1 + drone2) * (0.15 + lfo)

    # Intensity envelope (matches visual energy)
    intensity = np.ones(total_samples) * 0.15
    # Scene-by-scene intensity
    intensity[t >= 30] = 0.30   # Scene 3: Problem
    intensity[t >= 48] = 0.50   # Scene 4: Reveal
    intensity[t >= 68] = 0.60   # Scene 5: Classification
    intensity[t >= 98] = 0.70   # Scene 6: Slack
    intensity[t >= 125] = 0.60  # Scene 7: VLM
    intensity[t >= 150] = 0.80  # Scene 8: Finale
    # Fade out at end
    fade_start = int(177 * SAMPLE_RATE)
    fade_end = int(180 * SAMPLE_RATE)
    fade_indices = np.arange(fade_start, min(fade_end, total_samples))
    fade_mask = np.linspace(0.80, 0.0, len(fade_indices))
    intensity[fade_indices] = fade_mask
    intensity[fade_end:] = 0

    drone = drone * intensity
    master += drone

    # ═══ BASS HITS ═══
    def bass_hit(start_time, amplitude=0.6, duration=1.5):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        freq = 80 * np.exp(-tt * 2) + 40  # 80Hz → 40Hz exp decay
        env = np.exp(-tt * 1.5)
        hit = np.sin(2 * np.pi * freq * tt) * env * amplitude
        master[start:end] += hit

    # Bass hits at scene transitions
    bass_times = [0, 12, 36, 46, 51, 103, 155, 162]
    for bt in bass_times:
        bass_hit(bt)

    # ═══ CRYSTALLINE TINKS ═══
    def tink(start_time, freq=2500, amplitude=0.15, duration=0.3):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        env = np.exp(-tt * 15)
        hit = np.sin(2 * np.pi * freq * tt) * env * amplitude
        master[start:end] += hit

    # Tinks for connections and UI events
    tink_times = [4, 49, 50, 51.2, 51.3, 51.4, 51.5, 127, 179.5]
    for tt_time in tink_times:
        tink(tt_time, freq=2000 + np.random.randint(0, 1000))

    # ═══ WHOOSH ═══
    def whoosh(start_time, amplitude=0.3, duration=0.5):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        # Filtered noise
        noise = np.random.randn(end - start)
        # Simple bandpass approximation: modulate amplitude
        freq_mod = 800 * np.exp(-tt * 3) + 200
        env = np.exp(-tt * 3) * amplitude
        # Apply crude filter: multiply by sine at freq_mod
        modulated = noise * np.sin(2 * np.pi * freq_mod * tt) * env
        master[start:end] += modulated

    whoosh_times = [6, 30, 48, 98, 127.5]
    for wt in whoosh_times:
        whoosh(wt)

    # ═══ POPS ═══
    def pop(start_time, amplitude=0.2, duration=0.15):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        freq = 600 * np.exp(-tt * 10) + 300
        env = np.exp(-tt * 8) * amplitude
        hit = np.sin(2 * np.pi * freq * tt) * env
        master[start:end] += hit

    # Pops for card appearances
    pop_times = [69, 71, 71.12, 71.24, 71.36, 100, 102.5, 105, 107.5, 126]
    for pt in pop_times:
        pop(pt)

    # ═══ DINGS ═══
    def ding(start_time, freq=1200, amplitude=0.2, duration=0.5):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        env = np.exp(-tt * 3) * amplitude
        hit = (np.sin(2 * np.pi * freq * tt) + np.sin(2 * np.pi * freq * 2 * tt) * 0.5) * env
        master[start:end] += hit

    ding_times = [74, 103.5]
    for dt in ding_times:
        ding(dt)

    # ═══ GLASS BREAK ═══
    def glass_break(start_time, amplitude=0.15, duration=0.5):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        # Multiple high-freq oscillators at random freqs
        for i in range(8):
            offset = int(i * 0.02 * SAMPLE_RATE)
            if start + offset >= end:
                break
            freq = 3000 + np.random.randint(0, 4000)
            ttt = np.arange(end - start - offset) / SAMPLE_RATE
            env = np.exp(-ttt * 10) * amplitude
            hit = np.sin(2 * np.pi * freq * ttt) * env
            master[start + offset:end] += hit

    glass_break(46)

    # ═══ TICKS ═══
    def tick(start_time, amplitude=0.05, duration=0.03):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        env = np.exp(-tt * 30) * amplitude
        hit = np.sin(2 * np.pi * 1500 * tt) * env
        master[start:end] += hit

    # Ticks during counter animations
    i = 12.0
    while i < 15.0:
        tick(i)
        i += 0.1

    # ═══ FINAL CHORD ═══
    def chord(start_time, amplitude=0.12, duration=3.0):
        start = int(start_time * SAMPLE_RATE)
        end = min(start + int(duration * SAMPLE_RATE), total_samples)
        tt = np.arange(end - start) / SAMPLE_RATE
        env = np.exp(-tt * 0.5) * amplitude
        # C major: C4, E4, G4, C5
        notes = [261.63, 329.63, 392.00, 523.25]
        chord_sound = np.zeros(end - start)
        for freq in notes:
            chord_sound += np.sin(2 * np.pi * freq * tt)
        chord_sound = chord_sound / len(notes) * env
        master[start:end] += chord_sound

    chord(150)  # Finale start
    chord(162)  # Name reveal

    # ═══ CLIP AND NORMALIZE ═══
    master = np.clip(master, -1.0, 1.0)

    # Convert to 16-bit PCM
    audio_16bit = (master * 32767).astype(np.int16)

    # Write WAV
    wavfile.write(str(OUTPUT_PATH), SAMPLE_RATE, audio_16bit)
    print(f"✓ Audio saved: {OUTPUT_PATH}")
    print(f"  Duration: {DURATION}s")
    print(f"  Size: {OUTPUT_PATH.stat().st_size / 1024:.0f} KB")

if __name__ == "__main__":
    generate_audio()
