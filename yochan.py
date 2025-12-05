#!/usr/bin/env python3
import subprocess
import re 
import os
import sys
import signal 
import difflib # For fuzzy matching

# --- IMPORT CONFIGURATION ---
from config import (
    SHUTDOWN_CMD,
    REBOOT_CMD,
    SUSPEND_CMD,
    LOGOUT_CMD,
    FUZZY_THRESHOLD,
    ASSISTANT_NAME,
    ASSISTANT_DISPLAY_NAME,
)

from apps import APP_COMMANDS 
# ----------------------------

# ------------- CONFIG -------------
USE_SUDO = True
TERMINAL_APP = "xfce4-terminal"
# ----------------------------------

# --- FUZZY MATCHING HELPER ---
def _match_app_fuzzy(cleaned_command):
    if not cleaned_command:
        return None

    candidates = list(APP_COMMANDS.keys())
    # Find top 1 close match, using the configurable FUZZY_THRESHOLD
    matches = difflib.get_close_matches(cleaned_command, candidates, n=1, cutoff=FUZZY_THRESHOLD)
    if matches:
        return matches[0]
    return None


# --- GRACEFUL CLEANUP HANDLER (Remains the same) ---
def cleanup_old_listeners():
    """Finds and terminates any process running the yochan listener script."""
    
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
        subprocess.run(
            ["notify-send", "-t", "3000", "-i", icon, title, message],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(f"[{ASSISTANT_NAME}] Notification Failed: {title} - {message}", file=sys.stderr)
    except Exception as e:
        print(f"[{ASSISTANT_NAME}] Notification Error: {e}", file=sys.stderr)


def show_result(message):
    show_notification(ASSISTANT_DISPLAY_NAME, message)
    print(f"\n[{ASSISTANT_NAME}]: {message}", file=sys.stderr)
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
        print(f"[{ASSISTANT_NAME}] Execution Error: Command '{' '.join(full_cmd)}' failed. Details: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"[{ASSISTANT_NAME}] Error: Executable '{cmd[0]}' not found. Check your map or installation.", file=sys.stderr)
        return False
    except KeyboardInterrupt:
        return False

# --- SYSTEM POWER HANDLERS ---
def handle_shutdown():
    cleanup_old_listeners()
    if LOGOUT_CMD:
        run_command(LOGOUT_CMD, need_sudo=False)
    if SHUTDOWN_CMD:
        run_command(SHUTDOWN_CMD, need_sudo=True)
    return "Shutting down system."

def handle_restart():
    cleanup_old_listeners()
    if REBOOT_CMD:
        run_command(REBOOT_CMD, need_sudo=True)
    return "Restarting system."

def handle_sleep():
    cleanup_old_listeners()
    if SUSPEND_CMD:
        run_command(SUSPEND_CMD, need_sudo=True)
    return "Suspending system."

def handle_logout():
    if LOGOUT_CMD:
        run_command(LOGOUT_CMD, need_sudo=False)
        return "Logging out of session."
    else:
        return "Logout command is not configured for this desktop."

# --- APPLICATION HANDLERS ---
def handle_app_launch(app_name):
    app_executable = APP_COMMANDS.get(app_name)
    
    if app_executable:
        shell_command = f"nohup {app_executable} > /dev/null 2>&1 &"
        
        try:
            subprocess.Popen(shell_command, shell=True, start_new_session=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            success = True
        except Exception:
            success = False
        
        return f"Opening {app_name.title()}." if success else f"Failed to open {app_name.title()}."
    return None

def handle_generic_launch(cleaned_command):
    if not cleaned_command:
        return None
    tokens = cleaned_command.split()
    exe = tokens[0]

    if exe in ("the", "a", "an", "it", "this"):
        return None

    success = run_command([exe], need_sudo=False)
    if success:
        return f"Trying to open {exe}."
    else:
        return None

def handle_app_closure(command_text):
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
            return "[{ASSISTANT_NAME}]: Brightness control requires 'xbacklight' (install using: sudo apt install xbacklight)."
        run_command(["xbacklight", "-set", str(percent)], need_sudo=False)
        return f"Setting brightness to {percent} percent."
    return f"Brightness command failed. Specify a percentage between 0 and 100."

# --- CLIPBOARD HANDLERS (Unchanged) ---
def handle_clipboard_read():
    """Reads the current content of the clipboard (xclip)."""
    try:
        result = subprocess.run(['xclip', '-o', '-selection', 'clipboard'], capture_output=True, text=True, check=True)
        content = result.stdout.strip()
        
        if content:
            show_notification("Clipboard Content", content[:50] + "..." if len(content) > 50 else content, icon="edit-copy")
            return f"Clipboard content shown."
        else:
            return "Clipboard is empty."
    except FileNotFoundError:
        return "Clipboard function failed: 'xclip' not installed. (sudo apt install xclip)"
    except Exception:
        return "Failed to read clipboard content."

# --- MASTER EXECUTION FUNCTION ---
def execute_command(command_text):
    command_text = command_text.strip().lower()
    
    CLEANUP_PATTERN = r"^(open|launch|start|run|the|a|i)\s*"
    CLOSE_PHRASES = ["close", "quit", "exit", "terminate", "end"]

    # --- 1. QUIT LISTENER COMMAND ---
    if "die" in command_text or "stop listening" in command_text:
        return "QUIT_LISTENER"

    # --- 2. POWER COMMANDS ---
    if "shutdown" in command_text or "turn off" in command_text:
        return show_result(handle_shutdown())
    elif "restart" in command_text or "reboot" in command_text:
        return show_result(handle_restart())
    elif "sleep" in command_text or "suspend" in command_text:
        return show_result(handle_sleep())
    elif any(word in command_text for word in ["logout", "log out", "log off"]):
        return show_result(handle_logout())

    # --- 3. CONTROL COMMANDS ---
    if "volume" in command_text and any(word in command_text for word in ["set", "turn", "to"]):
        return show_result(handle_volume(command_text))
    if "brightness" in command_text and any(word in command_text for word in ["set", "turn", "to"]):
        return show_result(handle_brightness(command_text))

    # --- 4. CLIPBOARD COMMANDS ---
    if "clipboard" in command_text and ("show" in command_text or "read" in command_text or "what is" in command_text):
        return show_result(handle_clipboard_read())

    # --- 5. CLOSE ALL APPS COMMAND ---
    if "close all" in command_text or "kill all" in command_text:
        return show_result(handle_close_all())

    # --- 6. APPLICATION LAUNCH/CLOSE COMMANDS ---
    
    if any(phrase in command_text for phrase in CLOSE_PHRASES):
        return show_result(handle_app_closure(command_text))

    cleaned_command = re.sub(CLEANUP_PATTERN, "", command_text).strip()

    # 6a. Exact match in APP_COMMANDS
    if cleaned_command in APP_COMMANDS:
        return show_result(handle_app_launch(cleaned_command))

    # 6b. Substring/inclusion match in APP_COMMANDS
    for app_name_key in APP_COMMANDS.keys():
        if app_name_key in cleaned_command or cleaned_command in app_name_key:
            return show_result(handle_app_launch(app_name_key))

    # 6c. Fuzzy fallback on app names
    fuzzy_key = _match_app_fuzzy(cleaned_command)
    if fuzzy_key:
        return show_result(handle_app_launch(fuzzy_key))

    # --- 7. GENERIC EXECUTABLE FALLBACK ---
    generic_result = handle_generic_launch(cleaned_command)
    if generic_result:
        return show_result(generic_result)

    # --- DEFAULT RESPONSE ---
    return show_result(f"Sorry, I don't understand '{cleaned_command}' yet.")