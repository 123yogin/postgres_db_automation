import os
import subprocess
import time
import math
import signal
import sys
import re
import shutil
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# ---------------- CONFIG ----------------
DISPLAY_NUM = ":99"
SCREEN_RESOLUTION = "11520x6480"
SCREEN_DEPTH = "24"

# Global variables
xvfb_process = None
desktop_process = None

# Output Directory - Default to local path for testing
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/mnt/c/Users/yogin/OneDrive/Desktop/scripting/postgres_db_automation/output")

# Settings
PAGE_SIZE_FIRST = 15
PAGE_SIZE_REST = 40
QUERY_WAIT = 5.0 

# Query to execute
QUERY = "SELECT * FROM users"

# Database Connections
DATABASES = [
    {
        "name": "linecricket25",
        "folder": "LineCricket",
        "host": "172.19.224.1",
        "port": 5432,
        "user": os.getenv("LINECRICKET_USER", "postgres"),
        "password": os.getenv("LINECRICKET_PASSWORD", "postgres")
    },
    # {
    #     "name": "droptrackpwa",
    #     "folder": "DropTrack",
    #     "host": "172.19.224.1",
    #     "port": 5432,
    #     "user": os.getenv("DROPTRACK_USER", "postgres"),
    #     "password": os.getenv("DROPTRACK_PASSWORD", "postgres")
    # }
]

# ---------------- HELPERS ----------------

def cleanup_processes():
    """Forcefully kill all automation-related processes immediately"""
    names = ["Xvfb", "xfce4-session", "xfwm4", "xfce4-panel", "xfce4-terminal", "xfsettingsd", "psql"]
    for name in names:
        subprocess.run(["pkill", "-9", "-f", name], stderr=subprocess.DEVNULL)
    print("[CLEANUP] All background processes terminated.", flush=True)

def signal_handler(sig, frame):
    cleanup_processes()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def start_virtual_display():
    """Start Xvfb virtual display and window manager"""
    print("[DISPLAY] Starting Xvfb and Window Manager...", flush=True)
    subprocess.run(["pkill", "-f", f"Xvfb {DISPLAY_NUM}"], stderr=subprocess.DEVNULL)
    subprocess.Popen(["Xvfb", DISPLAY_NUM, "-screen", "0", f"{SCREEN_RESOLUTION}x{SCREEN_DEPTH}", "-ac"], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    os.environ["DISPLAY"] = DISPLAY_NUM
    subprocess.Popen(["xfwm4"], env={"DISPLAY": DISPLAY_NUM}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    print(f"[DISPLAY] Virtual display {DISPLAY_NUM} is READY.", flush=True)

def take_screenshot(filepath):
    """Take screenshot of virtual display"""
    try:
        # Use scrot to capture the entire virtual display
        subprocess.run([
            "scrot", "-z", filepath
        ], check=True, env={"DISPLAY": DISPLAY_NUM})
        return True
    except subprocess.CalledProcessError:
        try:
            # Fallback to ImageMagick
            subprocess.run([
                "import", "-window", "root", filepath
            ], check=True, env={"DISPLAY": DISPLAY_NUM})
            return True
        except subprocess.CalledProcessError:
            print(f"Failed to take screenshot: {filepath}")
            return False

def open_terminal():
    """Open terminal in virtual display"""
    try:
        print("  Launching xfce4-terminal...", flush=True)
        terminal_process = subprocess.Popen([
            "xfce4-terminal", "--maximize", "--title=PostgreSQL-Automation", "--font=Monospace 40"
        ], env={"DISPLAY": DISPLAY_NUM}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("  Waiting 5s for terminal to initialize...", flush=True)
        time.sleep(5)
        
        print("  Focusing terminal window...", flush=True)
        # Try to find the window multiple times if it's slow
        for i in range(3):
            res = subprocess.run(["xdotool", "search", "--name", "PostgreSQL-Automation", "windowactivate"], 
                           env={"DISPLAY": DISPLAY_NUM}, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                print("  Terminal FOCUSED.", flush=True)
                return terminal_process
            print(f"  Retry focusing terminal ({i+1}/3)...", flush=True)
            time.sleep(2)
        
        print("  Warning: Could not focus terminal window, but proceeding...", flush=True)
        return terminal_process
    except Exception as e:
        print(f"  Error opening terminal: {e}")
        return None

def send_keys(text, delay=0.1):
    """Send keystrokes to the virtual display"""
    try:
        # Use xdotool to send keystrokes
        subprocess.run([
            "xdotool", "type", "--delay", str(int(delay * 1000)), text
        ], env={"DISPLAY": DISPLAY_NUM}, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error sending keys: {e}")

def send_key(key):
    """Send special keys (Return, ctrl+c, etc.)"""
    try:
        subprocess.run([
            "xdotool", "key", key
        ], env={"DISPLAY": DISPLAY_NUM}, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error sending key {key}: {e}")

def sync_to_gdrive():
    """Sync output directory to Google Drive with aggressive cleaning and SOX structure"""
    config_data = os.getenv("RCLONE_CONFIG_DATA")
    
    if not config_data:
        print("[RCLONE] WARNING: RCLONE_CONFIG_DATA is empty. Skipping upload.", flush=True)
        return

    print("\n[RCLONE] Starting sync to your Personal Google Drive...", flush=True)
    
    # 1. Build the SOX Folder Structure
    now_time = datetime.now()
    year, month = now_time.year, now_time.month
    quarter = (month - 1) // 3 + 1
    timestamp = now_time.strftime("%Y-%m-%d_%H-%M")
    remote_path = f"Devops/Security/SOX/SOX-{year}-Q{quarter}/Commerce-Postgres/{timestamp}"

    # 2. NORMALIZE: Clean up config string
    config_data = config_data.replace('\\"', '"').replace("\\'", "'")
    try:
        lines = []
        for key in ['type', 'scope', 'token', 'team_drive']:
            m = re.search(rf'{key}\s*=\s*(.*?)(?=\s+(?:type|scope|token|team_drive)\s*=|$)', config_data)
            if m: lines.append(f"{key} = {m.group(1).strip()}")
        fixed_config = "[gdrive]\n" + "\n".join(lines) + "\n"
    except:
        fixed_config = f"[gdrive]\n{config_data}\n"

    # 4. Write to temp config
    config_path = "/tmp/rclone_tmp.conf"
    try:
        with open(config_path, "w") as f:
            f.write(fixed_config)
        
        # 5. Run rclone
        subprocess.run([
            "rclone", "--config", config_path, "sync", 
            OUTPUT_DIR, 
            f"gdrive:{remote_path}",
            "--drive-scope", "drive", "--verbose"
        ], capture_output=True, text=True, check=True)
        print(f"[RCLONE] Sync complete! Path: {remote_path}", flush=True)

    except subprocess.CalledProcessError as e:
        print(f"[RCLONE] Sync failed! Error: {e.stderr}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"[RCLONE] An unexpected error occurred: {e}", flush=True)
        sys.exit(1)
    finally:
        if os.path.exists(config_path): os.remove(config_path)

def get_total_rows(db_config):
    """Get total row count for pagination"""
    try:
        conn = psycopg2.connect(
            dbname=db_config["name"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            sslmode='prefer',
            connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM ({QUERY}) AS sub;")
        total = cur.fetchone()[0]
        cur.close()
        conn.close()
        return total
    except Exception as e:
        print(f"Error counting rows: {e}")
        return 0

def main():
    # Initial cleanup
    if os.path.exists(OUTPUT_DIR):
        print(f"[INIT] Cleaning local output directory: {OUTPUT_DIR}")
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"[INIT] Failed to delete {file_path}: {e}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        start_virtual_display()
        
        # Phase 1: CSV Export
        print("Phase 1: Exporting CSV files...", flush=True)
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        for db_config in DATABASES:
            db_folder = os.path.join(OUTPUT_DIR, db_config['folder'])
            os.makedirs(db_folder, exist_ok=True)
            csv_filename = f"{db_config['folder']}_RDS_{run_timestamp}.csv"
            csv_path = os.path.join(db_folder, csv_filename)
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            try:
                copy_cmd = f"COPY ({QUERY}) TO STDOUT WITH CSV HEADER"
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    subprocess.run([
                        "psql", "-h", db_config["host"], "-p", str(db_config["port"]),
                        "-U", db_config["user"], "-d", db_config["name"], "-c", copy_cmd
                    ], env=env, stdout=f, check=True)
                print(f"CSV exported: {csv_filename}")
            except Exception as e:
                print(f"Error exporting CSV: {e}")

        # Phase 2: Screenshot Automation
        print("Phase 2: Taking screenshots...", flush=True)
        terminal_process = open_terminal()
        if not terminal_process: return

        for db_config in DATABASES:
            print(f"-- Processing DB: {db_config['name']} --", flush=True)
            print("  Counting rows...", end="", flush=True)
            total_rows = get_total_rows(db_config)
            print(f" Done ({total_rows} rows)")
            
            total_pages = 1 if total_rows <= PAGE_SIZE_FIRST else 1 + math.ceil((total_rows - PAGE_SIZE_FIRST) / PAGE_SIZE_REST)
            
            print("  Clearing terminal...", flush=True)
            send_key("ctrl+l")
            time.sleep(0.5)
            
            print("  Connecting via psql...", flush=True)
            # Injecting PGPASSWORD into the shell command to avoid interactive password prompt issues
            connect_cmd = f'export PGPASSWORD="{db_config["password"]}" && export COLUMNS=5000 && psql -h {db_config["host"]} -p {db_config["port"]} -U {db_config["user"]} -d {db_config["name"]}'
            send_keys(connect_cmd)
            send_key("Return")
            time.sleep(3)
            
            # Setup psql for screenshots
            print("  Configuring psql view settings...", flush=True)
            for cmd in ["\\pset format aligned", "\\pset border 2", "\\x off", "\\pset pager off", "\\pset footer off"]:
                send_keys(cmd)
                send_key("Return")
                time.sleep(0.2)
            
            offset = 0
            for page in range(1, total_pages + 1):
                print(f"  > Capturing Page {page}/{total_pages}...", flush=True)
                if page > 1:
                    send_keys("\\! clear")
                    send_key("Return")
                    time.sleep(0.5)
                
                # 1. Print current date at the start
                send_keys("\\! date")
                send_key("Return")
                time.sleep(0.5)

                # 2. Run the actual query
                limit = PAGE_SIZE_FIRST if page == 1 else PAGE_SIZE_REST
                paginated_query = f"{QUERY} LIMIT {limit} OFFSET {offset};"
                send_keys(paginated_query)
                send_key("Return")
                time.sleep(QUERY_WAIT)

                # 3. Print current date at the end
                send_keys("\\! date")
                send_key("Return")
                time.sleep(1.0) # Wait for terminal to render date before screenshot
                
                scr_now = datetime.now().strftime('%Y%m%d_%H%M')
                screenshot_filename = f"{db_config['folder']}_RDS_{scr_now}_page_{page}.png"
                db_folder = os.path.join(OUTPUT_DIR, db_config['folder'])
                os.makedirs(db_folder, exist_ok=True)
                filepath = os.path.join(db_folder, screenshot_filename)
                
                if take_screenshot(filepath):
                    print(f"    [OK] Saved: {screenshot_filename}", flush=True)
                
                offset += limit
                time.sleep(0.5)
            
            print("  Exiting DB connection...", flush=True)
            send_keys("\\q")
            send_key("Return")
            time.sleep(1)
        
        # Final Upload
        sync_to_gdrive()
        print("\n[SUCCESS] Automation finished successfully.", flush=True)
        
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
    finally:
        cleanup_processes()
        print("[EXIT] Task completed.", flush=True)
        os._exit(0)

if __name__ == "__main__":
    main()