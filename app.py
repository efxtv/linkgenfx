import subprocess
import time
import os
import signal
import sys
import socket
import tempfile

# Constants
SSH_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3389
LOG_FILE = os.path.join(tempfile.gettempdir(), "serveo_output.log")
SERVEO_DOMAIN = "serveo.net"
TIMEOUT = 60

process = None  # Global process handle

def cleanup(signum=None, frame=None):
    global process
    if process:
        print("\n[+] Cleaning up SSH tunnel process...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception as e:
            print(f"[!] Exception during cleanup: {e}")
    sys.exit(0)

def clear_line():
    """Clear the current terminal line"""
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

def print_aligned(message):
    """Force aligned printing by clearing line before each print"""
    clear_line()
    print(message)

def main():
    global process

    # Set terminal title
    sys.stdout.write("\x1b]2;LinkGen V4\x07")
    sys.stdout.flush()

    print_aligned(f"[+] Starting SSH reverse tunnel to {SERVEO_DOMAIN} on port {SSH_PORT}")
    print_aligned("[>] Please wait while establishing tunnel...")

    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"0:localhost:{SSH_PORT}", SERVEO_DOMAIN],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )

    # Wait for tunnel to establish
    success = False
    log_content = ""

    for _ in range(TIMEOUT):
        try:
            with open(LOG_FILE, "r") as f:
                log_content = f.read()
                if "Forwarding TCP" in log_content:
                    success = True
                    break
        except FileNotFoundError:
            pass
        time.sleep(1)

    if not success:
        print_aligned(f"\n[✗] Error: Failed to establish tunnel within {TIMEOUT} seconds")
        print_aligned(f"[!] Check log: {LOG_FILE}")
        cleanup()

    # Resolve IP
    try:
        serveo_ip = socket.gethostbyname(SERVEO_DOMAIN)
    except socket.gaierror:
        print_aligned(f"\n[✗] Error: Unable to resolve {SERVEO_DOMAIN}")
        cleanup()

    serveo_endpoint_line = next((line for line in log_content.splitlines() if "Forwarding TCP" in line), None)
    local_endpoint_line = next((line for line in log_content.splitlines() if "localhost" in line), None)

    serveo_endpoint = serveo_endpoint_line.split()[-1] if serveo_endpoint_line else "Unknown"
    local_endpoint = local_endpoint_line.split(":")[-1].strip() if local_endpoint_line else "Unknown"

    # Final output with forced alignment
    print_aligned("")  # Empty line
    print_aligned("[>] Linkgen V4 By EFXTv")
    print_aligned(f"[>] IP    : {serveo_ip}")
    print_aligned(f"[>] RPORT : {serveo_endpoint.split(':')[1] if ':' in serveo_endpoint else serveo_endpoint}")
    print_aligned(f"[>] LPORT : {local_endpoint}")
    print_aligned("")  # Empty line
    print_aligned("[>] Press Ctrl+C to exit and cleanup.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

