import subprocess
import time
import sys
import os
import signal
from pathlib import Path

def run_project():
    # Get the project root directory
    root_dir = Path(__file__).resolve().parent
    
    python_cmd = sys.executable
    # Define scripts to run relative to root
    scripts = [
        [python_cmd, "src/process/manager.py"],
        [python_cmd, "src/process/alarm.py"],
        [python_cmd, "src/process/helmet.py"],
        [python_cmd, "src/process/station.py"],
        [python_cmd, "src/web_server.py"]
    ]
    
    processes = []
    
    print("🚀 Starting Construction Site Monitoring System...")
    print("="*60)
    
    try:
        # Start all processes
        for cmd in scripts:
            script_name = cmd[1].split('/')[-1]
            print(f"📦 Starting {script_name}...")
            
            # Use subprocess.Popen to run in background
            # We don't use shell=True for better control and security
            process = subprocess.Popen(
                cmd,
                cwd=str(root_dir),
                # Optional: redirect stdout/stderr to simplify main output
                # For now, let's keep them in the main terminal to see what's happening
            )
            processes.append(process)
            time.sleep(1) # Small delay to avoid race conditions on startup
            
        print("="*60)
        print("✅ All components are running!")
        print("💡 Press Ctrl+C to stop all processes.")
        print("="*60)
        
        # Wait for processes to finish or for Ctrl+C
        while True:
            # Check if any process has died
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    script_name = scripts[i][1].split('/')[-1]
                    print(f"⚠️  Process {script_name} terminated with code {p.returncode}")
                    # You could choose to restart it here if needed
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all components...")
        
        # Terminate all processes
        for p in processes:
            try:
                # Send SIGTERM
                p.terminate()
            except Exception:
                pass
                
        # Wait for processes to exit gracefully
        time.sleep(2)
        
        # Force kill if still running
        for p in processes:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        
        print("✅ Shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    run_project()