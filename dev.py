import subprocess
import sys
import os
import time

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # Platform-specific executables
    is_win = os.name == 'nt'
    npm_cmd = "npm.cmd" if is_win else "npm"
    python_cmd = os.path.join(backend_dir, ".venv", "Scripts", "python.exe") if is_win else os.path.join(backend_dir, ".venv", "bin", "python")
    
    if not os.path.exists(python_cmd):
        python_cmd = "python" # Fallback to system python if venv not found
        
    print("🚀 Starting Universeaty Dev Servers...")
    print(f"Backend  -> {python_cmd} -m src.timetable_checker.api")
    print(f"Frontend -> {npm_cmd} run dev")
    print("--------------------------------------------------")

    backend_proc = None
    frontend_proc = None
    try:
        # Start backend API (uses the virtual environment python)
        backend_proc = subprocess.Popen(
            [python_cmd, "-m", "src.timetable_checker.api"],
            cwd=backend_dir,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Start frontend Vite server
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_dir,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        # Keep parent script alive
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down dev servers gracefully...")
        if backend_proc: backend_proc.terminate()
        if frontend_proc: frontend_proc.terminate()
        time.sleep(1)
        sys.exit(0)

if __name__ == "__main__":
    main()
