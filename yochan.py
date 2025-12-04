#!/usr/bin/env python3
import subprocess
import re 
import os
import sys
import signal # Required for sending kill signals

# --- IMPORT MANUAL MAP ---
from apps import APP_COMMANDS 
# -------------------------

# ------------- CONFIG -------------
USE_SUDO = True
TERMINAL_APP = "xfce4-terminal"
# ----------------------------------

# --- GRACEACEFUL CLEANUP HANDLER (Remains the same) ---
def cleanup_old_listeners():
    """Finds and terminates any process running the yochan listener script."""
    
    # Use pgrep to find all processes matching the script name
    try:
        pids_output = subprocess.check_output(
            ["pgrep", "-f", "python.*yochan_listener.py"], 
            text=True
        ).strip().split('\n')
        
        pids = [int(p) for p in pids_output if p.isdigit() and int(p) != os.getpid()]
        
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
                
    except subprocess.CalledProcessError:
        pass

# --- DISPLAY HANDLER (Notifications) ---
def show_notification(title, message, icon="terminal"):
    try:
        subprocess.run(["notify-send", "-t", "3000", "-i", icon, title, message], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"[Yo-Chan] Notification Failed: {title} - {message}", file=sys.stderr)
    except Exception as e:
        print(f"[Yo-Chan] Notification Error: {e}", file=sys.stderr)

def show_result(message):
    show_notification("Yo-Chan! Assistant", message)
    print(f"\n[Yo-Chan]: {message}", file=sys.stderr)
    return message


# --- SYSTEM EXECUTION CORE ---
def run_command(cmd, need_sudo=False):
    """Executes a system command, blocking until completion (used for power/control/cleanup)."""
    try:
        if need_sudo and USE_SUDO:
            full_cmd = ["sudo"] + cmd
        else:
            full_cmd = cmd

        subprocess.run(full_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Yo-Chan] Execution Error: Command '{' '.join(full_cmd)}' failed. Details: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"[Yo-Chan] Error: Executable '{cmd[0]}' not found. Check your map or installation.", file=sys.stderr)
        return False
    except KeyboardInterrupt:
        return False

# --- SYSTEM POWER HANDLERS (Unchanged) ---
def handle_shutdown():
    cleanup_old_listeners()
    handle_logout()
    run_command(["systemctl", "poweroff"], need_sudo=True)
    return "Shutting down system."

def handle_restart():
    cleanup_old_listeners()
    run_command(["systemctl", "reboot"], need_sudo=True)
    return "Restarting system."

def handle_sleep():
    cleanup_old_listeners()
    run_command(["systemctl", "suspend"], need_sudo=True)
    return "Suspending system."

def handle_logout():
    run_command(["xfce4-session-logout", "--logout", "--fast"], need_sudo=False)
    return "Logging out of session."

# --- APPLICATION HANDLERS ---
def handle_app_launch(app_name):
    app_executable = APP_COMMANDS.get(app_name)
    
    if app_executable:
        # 🐛 CRITICAL FIX: Use 'nohup' and '&' to guarantee the application detaches and runs in the background.
        # This prevents the Python script from blocking while the app is open.
        
        # 1. Build the full shell command string
        shell_command = f"nohup {app_executable} > /dev/null 2>&1 &"
        
        # 2. Execute via the shell, which is required for 'nohup' and '&'
        success = subprocess.run(shell_command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # The success check is less reliable with 'shell=True' but Popen handles the immediate detach
        # The main goal is non-blocking execution.
        return f"Opening {app_name.title()}."
    return None

def handle_app_closure(command_text):
    # ... (Closure logic remains the same)
    CLOSE_PHRASES = r'^(close|quit|terminate|end)\s*'
    app_target = re.sub(CLOSE_PHRASES, '', command_text).strip()

    executable = None
    app_name = None
    
    if app_target in APP_COMMANDS:
        app_name = app_target
        executable = APP_COMMANDS[app_name]
    else:
        for key, exec_cmd in APP_COMMANDS.items():
            if app_target in key:
                app_name = key
                executable = exec_cmd
                break
                
    if executable:
        base_executable = executable.split()[-1] if 'flatpak' in executable else executable.split()[0]
        success = run_command(["pkill", "-f", base_executable], need_sudo=False)
        
        if success:
            return f"Closing {app_name.title()}."
        else:
            return f"Could not find or close {app_name.title()}. It may not be running."
            
    return "Error: Application name was not recognized for closure."


def handle_close_all():
    # ... (Close all logic remains the same)
    pkill_list = []
    for executable in APP_COMMANDS.values():
        if 'flatpak' in executable:
            pkill_list.append(executable.split()[-1])
        else:
            pkill_list.append(executable.split()[0])
            
    unique_executables = list(set(pkill_list))
    
    kill_cmd = ["pkill", "-f"] + unique_executables
    subprocess.run(kill_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return "Closed all recognized user applications."

# --- VOLUME/BRIGHTNESS HANDLERS (Unchanged) ---
def _get_percentage(command_text):
    percentage_str = re.search(r'\d+', command_text)
    if percentage_str:
        percent = int(percentage_str.group(0))
        return min(100, max(0, percent)) 
    return None

def handle_volume(command_text):
    percent = _get_percentage(command_text)
    if percent is not None:
        run_command(["amixer", "-D", "pulse", "sset", "Master", f"{percent}%"], need_sudo=False)
        return f"Setting volume to {percent} percent."
    return f"Volume command failed. Specify a percentage (e.g., 50)."

def handle_brightness(command_text):
    percent = _get_percentage(command_text)
    if percent is not None:
        if not subprocess.getstatusoutput('which xbacklight')[0] == 0:
            return "[Yo-Chan]: Brightness control requires 'xbacklight' (install using: sudo apt install xbacklight)."
        run_command(["xbacklight", "-set", str(percent)], need_sudo=False)
        return f"Setting brightness to {percent} percent."
    return f"Brightness command failed. Specify a percentage between 0 and 100."

# --- MASTER EXECUTION FUNCTION ---
def execute_command(command_text):
    command_text = command_text.strip().lower()
    
    CLEANUP_PATTERN = r'^(open|launch|start|run|the|a|i)\s*' 
    CLOSE_PHRASES = ["close", "quit", "exit", "terminate", "end"]

    # --- 1. QUIT LISTENER COMMAND ---
    if "die" in command_text or "stop listening" in command_text:
        return "QUIT_LISTENER"
        
    # --- 2. POWER COMMANDS ---
    if "shut down" in command_text or "turn off" in command_text:
        return show_result(handle_shutdown())
    elif "restart" in command_text or "reboot" in command_text:
        return show_result(handle_restart())
    elif "sleep" in command_text or "suspend" in command_text:
        return show_result(handle_sleep())
    elif any(word in command_text for word in ["logout", "log out", "log off"]):
        return show_result(handle_logout())

    # --- 3. CONTROL COMMANDS ---
    elif "volume" in command_text and any(word in command_text for word in ["set", "turn", "to"]):
        return show_result(handle_volume(command_text))
    elif "brightness" in command_text and any(word in command_text for word in ["set", "turn", "to"]):
        return show_result(handle_brightness(command_text))

    # --- 4. CLOSE ALL APPS COMMAND ---
    elif "close all" in command_text or "kill all" in command_text:
        return show_result(handle_close_all())
        
    # --- 5. APPLICATION LAUNCH/CLOSE COMMANDS ---
    
    if any(phrase in command_text for phrase in CLOSE_PHRASES):
        return show_result(handle_app_closure(command_text))
        
    cleaned_command = re.sub(CLEANUP_PATTERN, '', command_text).strip()
    
    if cleaned_command in APP_COMMANDS:
        return show_result(handle_app_launch(cleaned_command))
        
    for app_name_key in APP_COMMANDS.keys():
        if app_name_key in cleaned_command or cleaned_command in app_name_key: 
            return show_result(handle_app_launch(app_name_key))

    # --- DEFAULT RESPONSE ---
    return show_result(f"Sorry, I don't understand '{cleaned_command}' yet.")