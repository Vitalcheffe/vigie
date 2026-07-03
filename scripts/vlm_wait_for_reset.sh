#!/bin/bash
# Wait for Z-AI API rate limit to reset, then trigger stress test
LOG=/home/z/my-project/scripts/vlm_stress_test.log
for i in $(seq 1 15); do
  echo "[attempt $i/15] Testing VLM at $(date)..."
  RESULT=$(timeout 30 z-ai vision -p "test" -i /home/z/my-project/scripts/vigie_screenshot.png 2>&1)
  if echo "$RESULT" | grep -q "429"; then
    echo "  -> still 429, waiting 2 min"
    sleep 120
  else
    echo "  -> RATE LIMIT RESET! Launching stress test"
    cd /home/z/my-project
    python3 scripts/vlm_stress_test.py > "$LOG" 2>&1
    echo "  -> Stress test completed"
    exit 0
  fi
done
echo "  -> Exhausted 30 min of retries"
