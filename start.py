"""Vigie — Railway keep-alive wrapper."""
import os, sys, time, signal, subprocess

def main():
    print("=== Vigie keep-alive wrapper ===", flush=True)
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        print(f"Attempt {retry_count + 1}/{max_retries}", flush=True)
        
        env = os.environ.copy()
        env["MCP_IN_PROCESS"] = "true"
        env["LOG_LEVEL"] = "INFO"
        env["LOG_FORMAT"] = "text"
        
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        
        print(f"Bot started (PID {proc.pid})", flush=True)
        
        # Wait for the process to exit
        retcode = proc.wait()
        print(f"Bot exited with code {retcode}", flush=True)
        
        if retcode == 0:
            print("Clean exit, not retrying.", flush=True)
            break
        
        retry_count += 1
        if retry_count < max_retries:
            print(f"Waiting 5s before retry...", flush=True)
            time.sleep(5)
    
    if retry_count >= max_retries:
        print("Max retries reached. Exiting.", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
