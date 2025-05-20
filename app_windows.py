import subprocess
import time
import os
import signal
import sys
import socket
import platform
import tempfile  # Added to get temp folder path

def main():
    global process

    # Set the Windows terminal title
    if platform.system() == "Windows":
        os.system("title LinkGen V4")

# Constants
SSH_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3389  # Modified to accept port argument
LOG_FILE = os.path.join(tempfile.gettempdir(), "serveo_output.log")  # Modified to save in temp folder
SERVEO_DOMAIN = "serveo.net"
TIMEOUT = 60  # Maximum wait time in seconds

process = None  # global process handle

def cleanup(signum=None, frame=None):
    global process
    if process:
        print("\n[+] Cleaning up SSH tunnel process...")
        try:
            if platform.system() == "Windows":
                # On Windows, kill process and all child processes using taskkill
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                # On Unix, kill process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception as e:
            print(f"[!] Exception during cleanup: {e}")
    sys.exit(0)

# Set up signal handlers for clean exit
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    global process

    with open(LOG_FILE, "w") as log_file:
        if platform.system() == "Windows":
            # Detach process on Windows: CREATE_NEW_PROCESS_GROUP to allow signal control
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                ["ssh", "-o", "StrictHostKeyChecking=no", f"-R", f"0:localhost:{SSH_PORT}", SERVEO_DOMAIN],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )
        else:
            # On Unix, use preexec_fn to set new process group so we can kill all children later
            process = subprocess.Popen(
                ["ssh", "-o", "StrictHostKeyChecking=no", f"-R", f"0:localhost:{SSH_PORT}", SERVEO_DOMAIN],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )

    print("\n   > Waiting for tunnel to establish", end="")
    start_time = time.time()
    success = False

    # Poll the log file until tunnel is established or timeout
    while time.time() - start_time < TIMEOUT:
        try:
            with open(LOG_FILE, "r") as f:
                log_content = f.read()
                if "Forwarding TCP" in log_content:
                    success = True
                    break
        except FileNotFoundError:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print()

    if not success:
        print(f"[✗] Error: Failed to establish tunnel within {TIMEOUT} seconds")
        print(f"Check {LOG_FILE} for details")
        cleanup()

    # Resolve serveo.net IP address using socket
    try:
        serveo_ip = socket.gethostbyname(SERVEO_DOMAIN)
    except socket.gaierror:
        print(f"[✗] Error: Unable to resolve {SERVEO_DOMAIN}")
        cleanup()

    # Extract endpoint info
    serveo_endpoint_line = next(
        (line for line in log_content.splitlines() if "Forwarding TCP" in line), None
    )
    local_endpoint_line = next(
        (line for line in log_content.splitlines() if "localhost" in line), None
    )

    if serveo_endpoint_line:
        serveo_endpoint = serveo_endpoint_line.split()[-1]
    else:
        serveo_endpoint = "Unknown"
    if local_endpoint_line:
        local_endpoint = local_endpoint_line.split(":")[-1].strip()
    else:
        local_endpoint = "Unknown"
    print(f"   > Linkgen V4 By EFXTv")
    print(f"{'   > IP    :':<12} {serveo_ip}")
    print(f"{'   > RPORT :':<12} {serveo_endpoint.split(':')[1] if ':' in serveo_endpoint else serveo_endpoint}")
    print(f"{'   > LPORT :':<12} {local_endpoint}")

    print("\n   > Press Ctrl+C to exit and cleanup.")
    # Keep the script running to maintain the tunnel and handle cleanup signals
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
