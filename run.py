import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Launcher for The Edges of House")
    parser.add_argument("--wc", "--with-cheats", action="store_true", help="Enable cheats")
    parser.add_argument("--wom", "--without-music", action="store_true", help="Disable music")
    args = parser.parse_args()

    # Determine the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change the current working directory to the script's directory
    os.chdir(script_dir)
    
    # Path to the main.py file
    main_script = os.path.join(script_dir, "src", "main.py")
    
    # Check if main.py exists
    if not os.path.exists(main_script):
        # print(f"Error: {main_script} not found.")
        sys.exit(1)
        
    # Execute main.py using the current Python interpreter
    # We use subprocess to ensure it runs in the same environment
    import subprocess
    
    cmd = [sys.executable, main_script]
    if args.wc:
        cmd.append("--wc")
    if args.wom:
        cmd.append("--wom")
        
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        # print(f"Error running game: {e}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
