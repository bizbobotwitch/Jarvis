import os
import threading
import queue
import time
import datetime
import webbrowser
import urllib.parse
import subprocess
import platform
import math
import random
import warnings
import json
import re

# Silence deprecation warnings to keep our terminal super clean and futuristic!
warnings.filterwarnings("ignore", category=FutureWarning)

# GUI Libraries
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Audio/AI Libraries
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai

# Configuration File and Safe Sharing Folder Name
CONFIG_FILE = "jarvis_config.json"
SAFE_DIR = "Jarvis_Documents"

# Global reference to let background tools print directly to the Tkinter terminal
ACTIVE_APP = None

def safe_coinitialize():
    """
    Safely initializes COM for SAPI5 speech thread on Windows using standard ctypes.
    This prevents SAPI5 vocal output engine COM crashes on background threads.
    """
    if platform.system().lower() == "windows":
        try:
            import ctypes
            # CoInitializeEx with COINIT_APARTMENTTHREADED (0x2) and COINIT_DISABLE_OLE1DDE (0x4)
            ctypes.windll.ole32.CoInitializeEx(None, 2 | 4)
        except Exception:
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass

class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("J.A.R.V.I.S. - Public Core v2.0")
        self.root.geometry("1020x750")
        self.root.configure(bg="#0B0F19") # Cyberpunk space background
        
        # Register this active instance globally so background functions can write to our screen
        global ACTIVE_APP
        ACTIVE_APP = self
        
        # Operational variables
        self.is_active = False
        self.is_muted = False
        self.current_status = "IDLE" # IDLE, LISTENING, PROCESSING, SPEAKING, MUTED
        self.update_queue = queue.Queue()
        self.animation_angle = 0
        self.wave_phase = 0
        self.all_mics = []
        self.filtered_mics = []
        self.mic_searching_logged = False # Track alert logging to avoid spamming the console
        
        # Connection status tracking to completely prevent log spamming
        self.last_logged_mic = None
        self.last_mic_status = None # None, "connecting_logged", "connected", "failed_logged"
        
        # Vocal Echo Shield - precise timestamp trackers to discard self-hearing feedback
        self.last_speech_start_time = 0.0
        self.last_speech_end_time = 0.0
        
        # Thread Session Safety Controls (Prevents multiple background thread accumulation)
        self.listen_session_id = 0
        self.chatter_session_id = 0
        
        # API Key Redundancy Controls
        self.current_key_in_use = "primary" # "primary" or "fallback"
        
        # Cooldown & Wait Time Tracking
        self.processing_start_time = 0.0
        self.cooldown_remaining = 0.0
        self.cooldown_start_time = 0.0
        
        # Load user configuration
        self.load_config()
        
        # Ensure the safe folder exists and write a welcome note
        self.prepare_safe_directory()
        
        # Initialize Core Engines
        self.initialize_ai()
        self.initialize_devices()
        
        # Build UI layout
        self.setup_styles()
        self.create_widgets()
        
        # Filter microphones initially (blank search returns all)
        self.filter_microphones("")
        
        # Start the background queues and animations
        self.process_queue()
        self.animate_hud()
        
        # Print optimized boot diagnostic and security instructions
        self.print_security_diagnostics()
        
        # Check if the user needs to enter an API key on first run
        self.check_api_key_status()
        
        # Handle graceful window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def prepare_safe_directory(self):
        """Creates the safe local directory for document reading and outputs a template welcome file."""
        try:
            os.makedirs(SAFE_DIR, exist_ok=True)
            welcome_file = os.path.join(SAFE_DIR, "welcome_note.txt")
            with open(welcome_file, "w", encoding="utf-8") as wf:
                wf.write(
                    f"Hello {self.user_name}!\n"
                    f"This is your safe document folder. You can place school notes, homework assignments, "
                    f"lists, or creative stories here! Ask me to read or analyze them anytime."
                )
        except Exception as e:
            print(f"Error setting up safe directory: {e}")

    def load_config(self):
        """Loads API key, fallback API key, guidelines, and user identity from local JSON storage."""
        self.api_key = ""
        self.fallback_api_key = ""
        self.user_name = "Aaron"
        self.assistant_name = "Jarvis"
        self.custom_guidelines = (
            "You are a brilliant, conversational AI voice assistant.\n"
            "You have access to system tools, but to conserve your developer's API tokens, you MUST follow these rules:\n"
            "1. ONLY call a tool if the user explicitly and directly requests it (e.g. 'check running games', 'screenshot', 'open notepad').\n"
            "2. NEVER call tools proactively, spontaneously, or repeatedly in a single turn just to be helpful.\n"
            "3. Limit tool usage to exactly ONE tool execution per conversation turn.\n"
            "4. Keep your responses concise, highly natural, friendly, and smart since they are read aloud.\n"
            "5. Do not use markdown formatting, asterisks, or bullet points in your speech.\n"
            "6. Ensure all answers and suggested media are 100% appropriate, wholesome, and safe for teenagers. "
            "Do not suggest or touch upon adult themes, violence, or dangerous topics."
        )
        self.chatter_enabled = False # Default disabled to prevent background quota usage!
        self.chatter_interval = 180 # Safe default interval of 3 minutes
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config_data = json.load(f)
                    self.api_key = config_data.get("api_key", "")
                    self.fallback_api_key = config_data.get("fallback_api_key", "")
                    self.user_name = config_data.get("user_name", "Aaron")
                    self.assistant_name = config_data.get("assistant_name", "Jarvis")
                    self.custom_guidelines = config_data.get("custom_guidelines", self.custom_guidelines)
                    self.chatter_enabled = config_data.get("chatter_enabled", False)
                    self.chatter_interval = config_data.get("chatter_interval", 180)
            except Exception as e:
                print(f"Error loading configuration: {e}")

    def save_config(self):
        """Saves current API keys and guidelines to the local JSON configuration file."""
        config_data = {
            "api_key": self.api_key,
            "fallback_api_key": self.fallback_api_key,
            "user_name": self.user_name,
            "assistant_name": self.assistant_name,
            "custom_guidelines": self.custom_guidelines,
            "chatter_enabled": self.chatter_enabled,
            "chatter_interval": self.chatter_interval
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config_data, f, indent=4)
            self.log_to_terminal("system", "Settings successfully saved to disk.")
            return True
        except Exception as e:
            self.log_to_terminal("error", f"Failed to write configuration: {e}")
            return False

    def is_in_cooldown(self):
        """Checks if the system is currently under a rate-limit sleep restriction."""
        if self.cooldown_remaining > 0:
            elapsed = time.time() - self.cooldown_start_time
            if elapsed < self.cooldown_remaining:
                return True
            else:
                self.cooldown_remaining = 0.0
        return False

    def is_accidental_noise(self, text):
        """Determines if the transcribed speech is likely background noise or a non-verbal sound."""
        if not text:
            return True
        
        text_lower = text.lower().strip()
        
        # Strip simple punctuation to avoid failing matches
        text_clean = re.sub(r'[.,!?_]', '', text_lower).strip()
        if not text_clean:
            return True
            
        # If the transcript is just a single letter (other than 'i' or 'a'), it is usually background noise
        if len(text_clean) == 1 and text_clean not in ["i", "a"]:
            return True
            
        # Common non-verbal sounds or stop words transcribed by Google due to breathing or sighs
        noise_words = {
            "uh", "um", "ah", "oh", "cough", "sneezed", "groan", "gasp", 
            "the", "it", "so", "that", "is", "of", "to", "and", "but", "or",
            "sigh", "laughter", "chuckle", "snort"
        }
        
        if text_clean in noise_words:
            return True
            
        return False

    def get_formatted_guidelines(self):
        """Formats the system instructions dynamically using custom names from settings."""
        identity_prefix = (
            f"Your name is {self.assistant_name}. You are talking to your friend and developer, {self.user_name}.\n"
            f"Respond directly as {self.assistant_name}.\n"
        )
        return identity_prefix + self.custom_guidelines

    def initialize_ai(self):
        """Pre-configures connection to the Google Gemini API with fallback redundancy checks."""
        primary = self.api_key.strip()
        fallback = self.fallback_api_key.strip()

        # Decide key based on current target
        active_key = fallback if self.current_key_in_use == "fallback" else primary
        
        # Safe self-healing fallback if the requested key is completely empty
        if not active_key:
            if primary:
                active_key = primary
                self.current_key_in_use = "primary"
            elif fallback:
                active_key = fallback
                self.current_key_in_use = "fallback"

        if not active_key:
            self.log_to_terminal("system", "AI system is offline. Please enter a Gemini API Key in the settings tab.")
            return

        # Attempt to capture the existing active conversation history to maintain continuity
        old_history = None
        if hasattr(self, 'chat') and self.chat:
            try:
                old_history = self.chat.history
            except Exception:
                pass

        try:
            genai.configure(api_key=active_key)
            self.jarvis_tools = [
                open_website, 
                search_web, 
                get_current_time, 
                open_calculator, 
                open_application, 
                get_system_info,
                list_my_files,
                read_my_file,
                detect_running_games,
                capture_and_analyze_screen,
                play_youtube_video
            ]
            formatted_instructions = self.get_formatted_guidelines()
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash', 
                tools=self.jarvis_tools,
                system_instruction=formatted_instructions
            )
            
            # Carry over past chat messages so Jarvis keeps his memories after key swap!
            self.chat = self.model.start_chat(enable_automatic_function_calling=True)
            if old_history:
                try:
                    self.chat.history = old_history
                except Exception:
                    pass

            self.log_to_terminal("system", f"Neural Core initialized using {self.current_key_in_use.upper()} API key.")
        except Exception as e:
            self.log_to_terminal("error", f"AI Core Error: {e}")

    def prune_chat_history(self):
        """
        Safely prunes the chat history to keep the token count extremely low.
        Ensures we only prune complete message turns and never leave dangling function calls or responses,
        which would cause structural validation errors on the Google Generative AI API.
        """
        try:
            if not self.chat or not hasattr(self.chat, 'history'):
                return
            
            history = list(self.chat.history)
            max_turns = 4 # Keep the last 4 complete conversational turns max
            if len(history) <= 8:
                return
            
            safe_index = 0
            user_turns_counted = 0
            
            # Search backwards to find the beginning of a clean user turn (not in the middle of tool calls)
            for i in range(len(history) - 1, -1, -1):
                content = history[i]
                # A clean user turn has the 'user' role and does NOT carry function_response elements
                is_user_turn_start = (
                    content.role == "user" and 
                    not any(hasattr(part, 'function_response') or 'function_response' in str(part) for part in content.parts)
                )
                if is_user_turn_start:
                    user_turns_counted += 1
                    if user_turns_counted > max_turns:
                        safe_index = i
                        break
            
            if safe_index > 0:
                self.chat.history = history[safe_index:]
        except Exception as e:
            self.log_to_terminal("error", f"History pruner failed: {e}")

    def handle_api_error_or_quota(self, error_msg):
        """
        Interprets error messages to detect Gemini API key quota limits (Error 429).
        Performs hot key swapping of the underlying genai active configurations.
        Returns True if key was rotated successfully, False otherwise.
        """
        is_quota_error = "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower()
        if is_quota_error:
            primary = self.api_key.strip()
            fallback = self.fallback_api_key.strip()

            # Rotation is physically impossible if keys are identical, missing, or empty.
            if not primary or not fallback or primary == fallback:
                return False

            if self.current_key_in_use == "primary":
                self.log_to_terminal("system", "⚠️ Primary API key exhausted. Automatically rotating to Fallback API Key...")
                self.current_key_in_use = "fallback"
                self.initialize_ai()
                return True
            elif self.current_key_in_use == "fallback":
                self.log_to_terminal("system", "⚠️ Fallback API key exhausted. Attempting to cycle back to Primary Key...")
                self.current_key_in_use = "primary"
                self.initialize_ai()
                return True
        return False

    def run_key_diagnostic(self, key_type):
        """Runs an immediate background diagnostic test on the selected API key to check its quota health."""
        target_key = self.api_key.strip() if key_type == "primary" else self.fallback_api_key.strip()
        if not target_key:
            messagebox.showwarning("Key Missing", f"Please enter a {key_type} key before running diagnostics.")
            return
        
        self.log_to_terminal("system", f"🔍 Diagnostic: testing selected {key_type.upper()} key...")
        
        def diagnostic_thread():
            try:
                # Test connectivity directly using a clean, fresh configuration
                temp_model = genai.GenerativeModel('gemini-2.5-flash')
                genai.configure(api_key=target_key)
                
                # Make a tiny 1-token test prompt to verify current rate limits
                temp_model.generate_content("hello", generation_config={"max_output_tokens": 1})
                
                self.log_to_terminal("system", f"✅ {key_type.upper()} KEY DIAGNOSTIC: Key is active and has remaining quota!")
                self.update_queue.put(("msgbox", ("Key Diagnostic Active", f"Your {key_type} API key is healthy, active, and accepted by Google's servers!")))
            except Exception as e:
                err_str = str(e)
                is_quota = "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower()
                
                if is_quota:
                    analysis = (
                        f"❌ {key_type.upper()} DIAGNOSTIC FAILURE: Daily Quota Blocked (429).\n"
                        "💡 REASON: This Google account has hit its strict free tier limit of 1,500 daily requests.\n"
                        "💡 NOTE: Creating a fallback key on the same Google account shares this daily budget! They will both fail.\n"
                        "💡 FIX: Create a fresh key using a different Google account, or wait for the midnight Pacific Time reset."
                    )
                    self.log_to_terminal("error", analysis)
                    self.update_queue.put(("msgbox", ("Quota Exhausted", f"Your {key_type} key has hit the daily limit! See console log for instructions.")))
                else:
                    self.log_to_terminal("error", f"❌ {key_type.upper()} DIAGNOSTIC FAILURE: {err_str}")
                    self.update_queue.put(("msgbox", ("Diagnostic Error", f"Failed to test key: {err_str}")))
            finally:
                # Restore system config back to standard active setup
                self.initialize_ai()
                
        threading.Thread(target=diagnostic_thread, daemon=True).start()

    def initialize_devices(self):
        """Scans the system for input microphones, removes driver suffixes, and deduplicates identical entries."""
        try:
            raw_mics = sr.Microphone.list_microphone_names()
            self.all_mics = []
            seen_names = set()
            
            for i, name in enumerate(raw_mics):
                if not name:
                    continue
                
                clean_name = str(name)
                try:
                    clean_name = name.encode('latin1').decode('utf-8', errors='ignore')
                except Exception:
                    pass
                
                # Explicit mojibake replacements for Windows bluetooth/AirPods names
                mojibake_map = {
                    "â€™": "'",
                    "â\x80\x99": "'",
                    "â\x80\x9c": '"',
                    "â\x80\x9d": '"',
                    "ââ": "'",
                    "â": "'"
                }
                for bad, good in mojibake_map.items():
                    clean_name = clean_name.replace(bad, good)
                
                lower_name = clean_name.lower()
                if (
                    ".sys" in lower_name or 
                    "bthhfenum" in lower_name or 
                    "system32" in lower_name or
                    "drivers" in lower_name or
                    clean_name.startswith("@")
                ):
                    continue
                
                simplified_name = clean_name.strip()
                driver_suffixes = [
                    "(wasapi)", "(mme)", "(directsound)", "(wdm-ks)", 
                    "wasapi", "mme", "directsound", "wdm-ks",
                    "- find my", "find my", "- find"
                ]
                for suffix in driver_suffixes:
                    if simplified_name.lower().endswith(suffix):
                        simplified_name = simplified_name[:-len(suffix)].strip()
                
                simplified_name = simplified_name.strip("()- ").strip()
                
                if simplified_name and simplified_name not in seen_names:
                    seen_names.add(simplified_name)
                    self.all_mics.append((i, simplified_name))
            
            if not self.all_mics:
                for i, name in enumerate(raw_mics):
                    if not name:
                        continue
                    clean = str(name)
                    clean = clean.replace("â€™", "'").replace("â\x80\x99", "'")
                    lower_name = clean.lower()
                    if (
                        ".sys" in lower_name or 
                        "bthhfenum" in lower_name or 
                        "system32" in lower_name or
                        clean.startswith("@")
                    ):
                        continue
                    self.all_mics.append((i, clean))
                
        except Exception as e:
            self.all_mics = []
            self.log_to_terminal("error", f"Microphone detection error: {e}")

        # Detect System TTS Voices
        try:
            temp_engine = pyttsx3.init()
            system_voices = temp_engine.getProperty('voices')
            self.voice_options = [f"{v.name}" for v in system_voices]
            if not self.voice_options:
                self.voice_options = ["Default OS Voice Profile"]
        except Exception as e:
            self.voice_options = ["Default Speech Synthesizer"]
            self.log_to_terminal("error", f"Voice synthesis error: {e}")

    def setup_styles(self):
        """Sets up a high-tech sci-fi theme styling."""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background="#0B0F19")
        style.configure("Card.TFrame", background="#121829", borderwidth=1, relief="solid")
        
        style.configure("TNotebook", background="#0B0F19", borderwidth=0)
        style.configure("TNotebook.Tab", background="#121829", foreground="#8F9CAE", font=("Consolas", 10), padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#1B2234")], foreground=[("selected", "#00F0FF")])
        
        style.configure("TLabel", background="#0B0F19", foreground="#8F9CAE", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#121829", foreground="#00F0FF", font=("Consolas", 12, "bold"))
        style.configure("Title.TLabel", background="#0B0F19", foreground="#00F0FF", font=("Consolas", 16, "bold"))
        style.configure("SettingHeader.TLabel", background="#121829", foreground="#39FF14", font=("Consolas", 12, "bold"))
        style.configure("SettingLink.TLabel", background="#121829", foreground="#00F0FF", font=("Segoe UI", 9, "underline"), cursor="hand2")
        
        style.configure("TCombobox", fieldbackground="#1B2234", background="#1B2234", foreground="#ffffff")
        style.map("TCombobox", fieldbackground=[('readonly', '#1B2234')], foreground=[('readonly', '#ffffff')])

    def create_widgets(self):
        """Assembles the entire futuristic layout with settings tabs."""
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=20, pady=10)
        
        lbl_title = ttk.Label(top_frame, text="// J.A.R.V.I.S. ENGINE MAINBOARD", style="Title.TLabel")
        lbl_title.pack(side="left")
        
        self.lbl_overall_status = ttk.Label(top_frame, text="SYSTEM: OFFLINE", font=("Consolas", 10, "bold"), foreground="#FF4D4D")
        self.lbl_overall_status.pack(side="right", padx=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(5, 15))
        
        self.tab_console = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_console, text="[ CONSOLE CENTER ]")
        self.notebook.add(self.tab_settings, text="[ NEURAL SETTINGS ]")
        
        self.build_console_tab()
        self.build_settings_tab()

    def build_console_tab(self):
        """Builds out the interactive operational console view."""
        left_panel = ttk.Frame(self.tab_console, style="Card.TFrame", padding=15, width=380)
        left_panel.pack(side="left", fill="both", expand=False)
        left_panel.pack_propagate(False)
        
        lbl_hud_title = ttk.Label(left_panel, text="HUD CORE STATUS", style="Header.TLabel")
        lbl_hud_title.pack(anchor="w")
        
        self.hud_canvas = tk.Canvas(left_panel, width=320, height=180, bg="#121829", bd=0, highlightthickness=0)
        self.hud_canvas.pack(pady=10)
        
        lbl_config_title = ttk.Label(left_panel, text="INPUT AUDIO PORT", style="Header.TLabel")
        lbl_config_title.pack(anchor="w", pady=(10, 5))
        
        ttk.Label(left_panel, text="Filter Microphone List:", style="TLabel").pack(anchor="w")
        self.entry_mic_search = tk.Entry(
            left_panel, bg="#1B2234", fg="#ffffff", insertbackground="#00F0FF",
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightcolor="#00F0FF", highlightbackground="#121829"
        )
        self.entry_mic_search.pack(fill="x", pady=(2, 6), ipady=4)
        self.entry_mic_search.bind("<KeyRelease>", self.on_mic_search_keyup)
        
        self.combo_mic = ttk.Combobox(left_panel, state="readonly")
        self.combo_mic.pack(fill="x", pady=2)
        
        self.btn_power = tk.Button(
            left_panel, text="BOOT UP AI CORE", font=("Consolas", 12, "bold"),
            bg="#005F73", fg="#ffffff", activebackground="#00F0FF", activeforeground="#005F73",
            bd=0, cursor="hand2", command=self.toggle_system
        )
        self.btn_power.pack(fill="x", side="bottom", pady=(5, 10), ipady=12)

        self.btn_mute = tk.Button(
            left_panel, text="MUTE MICROPHONE", font=("Consolas", 10, "bold"),
            bg="#1F293D", fg="#FF4D4D", activebackground="#FF4D4D", activeforeground="#1F293D",
            bd=0, cursor="hand2", command=self.toggle_mute
        )
        self.btn_mute.pack(fill="x", side="bottom", pady=(0, 5), ipady=8)

        right_panel = ttk.Frame(self.tab_console, style="Card.TFrame", padding=15)
        right_panel.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        lbl_feed_title = ttk.Label(right_panel, text="ACTIVE TERMINAL DIAGNOSTICS & CHAT LOG", style="Header.TLabel")
        lbl_feed_title.pack(anchor="w")
        
        self.txt_feed = scrolledtext.ScrolledText(
            right_panel, bg="#0A0E17", fg="#E2E8F0", insertbackground="#00F0FF", 
            font=("Consolas", 10), bd=1, relief="solid", highlightthickness=0
        )
        self.txt_feed.pack(fill="both", expand=True, pady=10)
        
        self.txt_feed.tag_config("user", foreground="#00F0FF")      
        self.txt_feed.tag_config("jarvis", foreground="#39FF14")    
        self.txt_feed.tag_config("system", foreground="#FF9F1C")    
        self.txt_feed.tag_config("error", foreground="#EF476F")     
        
        input_frame = ttk.Frame(right_panel)
        input_frame.pack(fill="x", side="bottom")
        
        self.entry_message = tk.Entry(
            input_frame, bg="#1B2234", fg="#ffffff", insertbackground="#00F0FF", 
            font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightcolor="#00F0FF", highlightbackground="#121829"
        )
        self.entry_message.pack(side="left", fill="both", expand=True, ipady=8)
        self.entry_message.bind("<Return>", lambda e: self.send_manual_message())
        
        self.btn_send = tk.Button(
            input_frame, text="TRANSMIT", font=("Consolas", 9, "bold"),
            bg="#1F293D", fg="#00F0FF", activebackground="#00F0FF", activeforeground="#0A0E17",
            bd=0, cursor="hand2", command=self.send_manual_message
        )
        self.btn_send.pack(side="right", padx=(10, 0), ipady=6, ipadx=15)

    def build_settings_tab(self):
        """Constructs the settings screen with customizable identities, API keys, and configurations."""
        settings_panel = ttk.Frame(self.tab_settings, style="Card.TFrame", padding=15)
        settings_panel.pack(fill="both", expand=True)
        
        # 1. API Keys Section (Primary & Fallback)
        lbl_api_sec = ttk.Label(settings_panel, text="1. ENTER YOUR GEMINI API KEYS HERE", style="SettingHeader.TLabel")
        lbl_api_sec.pack(anchor="w", pady=(0, 2))
        
        lbl_api_instructions = ttk.Label(
            settings_panel, 
            text="Get a free key by clicking the link below or visiting Google AI Studio directly:", 
            style="TLabel"
        )
        lbl_api_instructions.pack(anchor="w", pady=(0, 2))
        
        lbl_api_link = ttk.Label(
            settings_panel, 
            text="👉 Open Google AI Studio (aistudio.google.com)", 
            style="SettingLink.TLabel"
        )
        lbl_api_link.pack(anchor="w", pady=(0, 10))
        lbl_api_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/"))
        
        # Primary Key Row
        lbl_primary_key = ttk.Label(settings_panel, text="Primary API Key:", style="TLabel")
        lbl_primary_key.pack(anchor="w", pady=(2, 0))
        
        api_frame = ttk.Frame(settings_panel)
        api_frame.pack(fill="x", pady=2)
        
        self.entry_api_key = tk.Entry(
            api_frame, bg="#1B2234", fg="#ffffff", insertbackground="#39FF14", 
            font=("Consolas", 10), bd=0, highlightthickness=1, highlightcolor="#39FF14", highlightbackground="#121829",
            show="*" 
        )
        self.entry_api_key.pack(side="left", fill="both", expand=True, ipady=6)
        self.entry_api_key.insert(0, self.api_key)
        
        self.btn_show_key = tk.Button(
            api_frame, text="REVEAL KEY", font=("Consolas", 8, "bold"),
            bg="#1F293D", fg="#8F9CAE", activebackground="#00F0FF", activeforeground="#0A0E17",
            bd=0, cursor="hand2", command=self.toggle_primary_api_visibility
        )
        self.btn_show_key.pack(side="right", padx=(10, 0), ipady=4, ipadx=10)

        # Fallback Key Row
        lbl_fallback_key = ttk.Label(settings_panel, text="Fallback API Key (Optional):", style="TLabel")
        lbl_fallback_key.pack(anchor="w", pady=(6, 0))
        
        fallback_api_frame = ttk.Frame(settings_panel)
        fallback_api_frame.pack(fill="x", pady=2)
        
        self.entry_fallback_api_key = tk.Entry(
            fallback_api_frame, bg="#1B2234", fg="#ffffff", insertbackground="#39FF14", 
            font=("Consolas", 10), bd=0, highlightthickness=1, highlightcolor="#39FF14", highlightbackground="#121829",
            show="*" 
        )
        self.entry_fallback_api_key.pack(side="left", fill="both", expand=True, ipady=6)
        self.entry_fallback_api_key.insert(0, self.fallback_api_key)
        
        self.btn_show_fallback_key = tk.Button(
            fallback_api_frame, text="REVEAL KEY", font=("Consolas", 8, "bold"),
            bg="#1F293D", fg="#8F9CAE", activebackground="#00F0FF", activeforeground="#0A0E17",
            bd=0, cursor="hand2", command=self.toggle_fallback_api_visibility
        )
        self.btn_show_fallback_key.pack(side="right", padx=(10, 0), ipady=4, ipadx=10)

        # Key Diagnostics Trigger Buttons
        test_frame = ttk.Frame(settings_panel)
        test_frame.pack(fill="x", pady=6)
        
        self.btn_test_primary = tk.Button(
            test_frame, text="TEST PRIMARY KEY", font=("Consolas", 9, "bold"),
            bg="#1F293D", fg="#39FF14", activebackground="#39FF14", activeforeground="#0B0F19",
            bd=0, cursor="hand2", command=lambda: self.run_key_diagnostic("primary")
        )
        self.btn_test_primary.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=6)
        
        self.btn_test_fallback = tk.Button(
            test_frame, text="TEST FALLBACK KEY", font=("Consolas", 9, "bold"),
            bg="#1F293D", fg="#00F0FF", activebackground="#00F0FF", activeforeground="#0B0F19",
            bd=0, cursor="hand2", command=lambda: self.run_key_diagnostic("fallback")
        )
        self.btn_test_fallback.pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=6)

        # 2. Name Settings (User & Assistant)
        lbl_names_sec = ttk.Label(settings_panel, text="2. CUSTOMIZE USER & ASSISTANT IDENTITY", style="SettingHeader.TLabel")
        lbl_names_sec.pack(anchor="w", pady=(10, 2))

        names_frame = ttk.Frame(settings_panel)
        names_frame.pack(fill="x", pady=2)

        # User Name Option
        user_name_sub_frame = ttk.Frame(names_frame)
        user_name_sub_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(user_name_sub_frame, text="Your Name (Developer / User):", style="TLabel").pack(anchor="w")
        self.entry_user_name = tk.Entry(
            user_name_sub_frame, bg="#1B2234", fg="#ffffff", insertbackground="#39FF14", 
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightcolor="#39FF14", highlightbackground="#121829"
        )
        self.entry_user_name.pack(fill="x", pady=2, ipady=4)
        self.entry_user_name.insert(0, self.user_name)

        # Assistant Name Option
        assistant_name_sub_frame = ttk.Frame(names_frame)
        assistant_name_sub_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))
        ttk.Label(assistant_name_sub_frame, text="Assistant Name:", style="TLabel").pack(anchor="w")
        self.entry_assistant_name = tk.Entry(
            assistant_name_sub_frame, bg="#1B2234", fg="#ffffff", insertbackground="#39FF14", 
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightcolor="#39FF14", highlightbackground="#121829"
        )
        self.entry_assistant_name.pack(fill="x", pady=2, ipady=4)
        self.entry_assistant_name.insert(0, self.assistant_name)

        # 3. Custom Personality Rules
        lbl_rules_sec = ttk.Label(settings_panel, text="3. CUSTOM AI SYSTEM PERSONALITY & GUIDELINES", style="SettingHeader.TLabel")
        lbl_rules_sec.pack(anchor="w", pady=(10, 5))
        
        self.txt_guidelines = scrolledtext.ScrolledText(
            settings_panel, bg="#1B2234", fg="#ffffff", insertbackground="#39FF14",
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightcolor="#39FF14", highlightbackground="#121829",
            height=3
        )
        self.txt_guidelines.pack(fill="both", expand=True, pady=2)
        self.txt_guidelines.insert(tk.END, self.custom_guidelines)
        
        # 4. Speech Voice Settings
        lbl_speech_sec = ttk.Label(settings_panel, text="4. SYNTHESIS SPEECH SETTINGS", style="SettingHeader.TLabel")
        lbl_speech_sec.pack(anchor="w", pady=(10, 2))
        
        speech_frame = ttk.Frame(settings_panel)
        speech_frame.pack(fill="x", pady=2)
        
        voice_sub_frame = ttk.Frame(speech_frame)
        voice_sub_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(voice_sub_frame, text="Active Voice Profile:", style="TLabel").pack(anchor="w")
        self.combo_voice = ttk.Combobox(voice_sub_frame, values=self.voice_options, state="readonly")
        self.combo_voice.pack(fill="x", pady=2)
        if self.voice_options:
            self.combo_voice.current(0)
            
        rate_sub_frame = ttk.Frame(speech_frame)
        rate_sub_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))
        ttk.Label(rate_sub_frame, text="Speech Output Rate (Speed):", style="TLabel").pack(anchor="w")
        self.slide_rate = tk.Scale(
            rate_sub_frame, from_=100, to=300, orient="horizontal", 
            bg="#121829", fg="#8F9CAE", highlightthickness=0, troughcolor="#1B2234", activebackground="#00F0FF"
        )
        self.slide_rate.set(175)
        self.slide_rate.pack(fill="x", pady=2)

        # 5. Spontaneous Background Chatter Settings
        lbl_chatter_sec = ttk.Label(settings_panel, text="5. SPONTANEOUS AI CHATTER & SYSTEM REMARKS", style="SettingHeader.TLabel")
        lbl_chatter_sec.pack(anchor="w", pady=(10, 2))
        
        chatter_frame = ttk.Frame(settings_panel)
        chatter_frame.pack(fill="x", pady=2)
        
        self.var_chatter_enabled = tk.BooleanVar(value=self.chatter_enabled)
        self.chk_chatter = tk.Checkbutton(
            chatter_frame, text="Enable Spontaneous Thoughts (Speaks occasionally)",
            variable=self.var_chatter_enabled, bg="#121829", fg="#E2E8F0", selectcolor="#0B0F19",
            activebackground="#121829", activeforeground="#ffffff", font=("Segoe UI", 10)
        )
        self.chk_chatter.pack(side="left", fill="x", expand=True, anchor="w")
        
        chatter_slider_frame = ttk.Frame(chatter_frame)
        chatter_slider_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))
        ttk.Label(chatter_slider_frame, text="Chatter Delay Interval (Seconds):", style="TLabel").pack(anchor="w")
        self.slide_chatter_interval = tk.Scale(
            chatter_slider_frame, from_=30, to=300, orient="horizontal",
            bg="#121829", fg="#8F9CAE", highlightthickness=0, troughcolor="#1B2234", activebackground="#00F0FF"
        )
        self.slide_chatter_interval.set(self.chatter_interval)
        self.slide_chatter_interval.pack(fill="x", pady=2)

        # 6. Save Config Button
        self.btn_save_config = tk.Button(
            settings_panel, text="APPLY & SAVE SETTINGS", font=("Consolas", 11, "bold"),
            bg="#39FF14", fg="#0B0F19", activebackground="#00F0FF", activeforeground="#0B0F19",
            bd=0, cursor="hand2", command=self.apply_and_save_settings
        )
        self.btn_save_config.pack(fill="x", side="bottom", pady=(10, 0), ipady=8)

    def print_security_diagnostics(self):
        """Outputs essential system checks and guidelines for managing key usage."""
        self.log_to_terminal("system", "🛡️ SYSTEM AUDIT & OPTIMIZATION REPORT:")
        self.log_to_terminal("system", "👉 IMPORTANT: If you close the window but the terminal still prints, you have 'ghost' Python processes running.")
        self.log_to_terminal("system", "👉 FIX: Open Task Manager (Windows) or Activity Monitor (Mac) and end all processes named 'python' or 'python.exe'.")
        self.log_to_terminal("system", "👉 VOCAL ECHO SHIELD: Active. Discarding all microphone audios recorded during vocal synthesis.")
        self.log_to_terminal("system", "👉 FREE PLAN WARNING: Gemini Free Tier allows 15 requests per minute. Rapid speaking will trigger temporary cooldowns.")

    def on_mic_search_keyup(self, event):
        """Filters the microphone device list dynamically as you type."""
        search_query = self.entry_mic_search.get().strip()
        self.filter_microphones(search_query)

    def filter_microphones(self, query):
        """Updates the microphone dropdown box with matching search queries."""
        options = ["[AUTO] All Microphones (Simultaneous)"]
        if not query:
            options += [f"[{i}] {name}" for i, name in self.all_mics]
        else:
            options += [
                f"[{i}] {name}" for i, name in self.all_mics 
                if query.lower() in name.lower()
            ]
        self.combo_mic.configure(values=options)
        self.combo_mic.current(0)

    def toggle_primary_api_visibility(self):
        """Hides or reveals the primary API key characters."""
        if self.entry_api_key.cget("show") == "*":
            self.entry_api_key.configure(show="")
            self.btn_show_key.configure(text="HIDE KEY")
        else:
            self.entry_api_key.configure(show="*")
            self.btn_show_key.configure(text="REVEAL KEY")

    def toggle_fallback_api_visibility(self):
        """Hides or reveals the fallback API key characters."""
        if self.entry_fallback_api_key.cget("show") == "*":
            self.entry_fallback_api_key.configure(show="")
            self.btn_show_fallback_key.configure(text="HIDE KEY")
        else:
            self.entry_fallback_api_key.configure(show="*")
            self.btn_show_fallback_key.configure(text="REVEAL KEY")

    def toggle_mute(self):
        """Toggles state of the hardware microphone listener."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.configure(text="UNMUTE MICROPHONE", bg="#FF4D4D", fg="#0B0F19")
            self.log_to_terminal("system", "[Mic Muted] Audio feed is suspended.")
            self.update_hud_state("MUTED")
        else:
            self.btn_mute.configure(text="MUTE MICROPHONE", bg="#1F293D", fg="#FF4D4D")
            self.log_to_terminal("system", "[Mic Unmuted] Audio feed is listening.")
            self.update_hud_state("IDLE")

    def apply_and_save_settings(self):
        """Saves settings to file and re-initializes the AI core in memory."""
        self.api_key = self.entry_api_key.get().strip()
        self.fallback_api_key = self.entry_fallback_api_key.get().strip()
        self.user_name = self.entry_user_name.get().strip() or "Aaron"
        self.assistant_name = self.entry_assistant_name.get().strip() or "Jarvis"
        self.custom_guidelines = self.txt_guidelines.get("1.0", tk.END).strip()
        self.chatter_enabled = self.var_chatter_enabled.get()
        self.chatter_interval = int(self.slide_chatter_interval.get())
        
        if not self.api_key and not self.fallback_api_key:
            messagebox.showwarning("API Key Missing", "Your API keys are empty! Assistant cannot boot without at least one key.")
            return

        # Always default back to Primary Key on setting modifications
        self.current_key_in_use = "primary"

        success = self.save_config()
        if success:
            self.prepare_safe_directory() # Dynamically rebuild welcome card with updated custom name!
            self.initialize_ai()
            messagebox.showinfo("Neural Core Refreshed", "Brain configurations, guidelines, fallback redundances, and dynamic identity updated!")

    def check_api_key_status(self):
        """Encourages user to head to the settings tab if keys are missing."""
        if not self.api_key and not self.fallback_api_key:
            self.log_to_terminal("system", "⚠️ WELCOME: Go to 'Neural Settings', paste your free API key, set your custom names, and click 'Save'.")

    def log_to_terminal(self, tag, message):
        """Thread-safe utility to output messages directly to the console log."""
        self.update_queue.put(("log", (tag, message)))

    def update_hud_state(self, status):
        """Thread-safe utility to change system status updates."""
        self.current_status = status # Instantaneous, real-time memory state updates for threads
        self.update_queue.put(("status", status))

    def toggle_system(self):
        """Starts or stops the live microphone listening thread."""
        if not self.api_key and not self.fallback_api_key:
            messagebox.showerror("System Error", "Cannot wake assistant up without an API Key. Please insert your key in the settings tab.")
            return

        if not self.is_active:
            self.is_active = True
            self.btn_power.configure(text="SHUT DOWN AI CORE", bg="#D62828", activebackground="#FF4D4D")
            self.log_to_terminal("system", f"[Core Init] {self.assistant_name} listener loop is running.")
            
            if self.is_muted:
                self.update_hud_state("MUTED")
            else:
                self.update_hud_state("IDLE")
            
            # Reset and register fresh Session IDs to terminate any duplicate background threads
            self.listen_session_id = random.randint(1000, 9999)
            self.listen_thread = threading.Thread(
                target=self.voice_listening_loop, 
                args=(self.listen_session_id,), 
                daemon=True
            )
            self.listen_thread.start()
            
            if self.chatter_enabled:
                self.chatter_session_id = random.randint(1000, 9999)
                self.chatter_thread = threading.Thread(
                    target=self.proactive_chatter_loop, 
                    args=(self.chatter_session_id,), 
                    daemon=True
                )
                self.chatter_thread.start()
        else:
            self.is_active = False
            # Invalidate all existing threads immediately on shutdown
            self.listen_session_id = 0
            self.chatter_session_id = 0
            self.btn_power.configure(text="BOOT UP AI CORE", bg="#005F73", activebackground="#00F0FF")
            self.log_to_terminal("system", f"[Core ShutDown] {self.assistant_name} neural core is sleeping.")
            self.update_hud_state("IDLE")

    def send_manual_message(self):
        """Sends typed console commands to Gemini."""
        msg = self.entry_message.get().strip()
        if not msg:
            return
        
        if not self.api_key and not self.fallback_api_key:
            messagebox.showerror("Error", "Connect your API key in settings before transmitting.")
            return

        if self.is_in_cooldown():
            rem = self.cooldown_remaining - (time.time() - self.cooldown_start_time)
            self.log_to_terminal("system", f"Transmission blocked: API cooling down. Please wait {int(rem)} seconds.")
            return

        self.entry_message.delete(0, tk.END)
        self.log_to_terminal("user", msg)
        
        threading.Thread(target=self.process_ai_response, args=(msg,), daemon=True).start()

    def process_queue(self):
        """Refreshes the GUI from elements queued inside background execution tasks."""
        try:
            while True:
                task, data = self.update_queue.get_nowait()
                if task == "log":
                    tag, message = data
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    prefix = "👤 User: " if tag == "user" else f"🤖 {self.assistant_name}: " if tag == "jarvis" else "🖥️  SYSTEM: "
                    if tag == "error":
                        prefix = "⚠️  ERROR: "
                        
                    self.txt_feed.configure(state="normal")
                    self.txt_feed.insert(tk.END, f"[{timestamp}] {prefix}{message}\n", tag)
                    self.txt_feed.see(tk.END)
                    self.txt_feed.configure(state="disabled")
                    
                elif task == "status":
                    self.current_status = data
                    if data == "PROCESSING":
                        self.processing_start_time = time.time()
                    self.lbl_overall_status.configure(text=f"SYSTEM: {data}")
                    if data == "LISTENING":
                        self.lbl_overall_status.configure(foreground="#00F0FF")
                    elif data == "PROCESSING":
                        self.lbl_overall_status.configure(foreground="#FF9F1C")
                    elif data == "SPEAKING":
                        self.lbl_overall_status.configure(foreground="#39FF14")
                    elif data == "MUTED":
                        self.lbl_overall_status.configure(foreground="#FF4D4D")
                    else:
                        self.lbl_overall_status.configure(foreground="#8F9CAE")
                
                elif task == "cooldown":
                    self.cooldown_remaining = float(data)
                    self.cooldown_start_time = time.time()
                
                elif task == "msgbox":
                    title, msg = data
                    messagebox.showinfo(title, msg)
                        
                self.update_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def voice_listening_loop(self, session_id):
        """
        Background listening loop that intelligently connects to the best microphone.
        Cycles through available microphones sequentially to avoid PortAudio crashes if in AUTO.
        Now completely loop-shielded against speaking feedback echoes and active cooldown leaks.
        """
        recognizer = sr.Recognizer()
        
        # Optimize microphone sensitivity against breathing noise
        recognizer.energy_threshold = 400  # Prevent small noise triggers
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.5
        recognizer.pause_threshold = 0.8
        
        # Reset tracking properties for loop startup
        self.last_logged_mic = None
        self.last_mic_status = None # None, "connecting_logged", "connected", "failed_logged"
        
        while self.is_active and self.listen_session_id == session_id:
            if self.is_muted:
                self.update_hud_state("MUTED")
                time.sleep(0.5)
                continue
                
            # CRITICAL LOOP-SHIELD 1: Stop microphone listening if Jarvis is speaking/processing.
            # This completely cuts the self-hearing echo loop that triggers infinite Gemini calls!
            if self.current_status in ["SPEAKING", "PROCESSING"]:
                time.sleep(0.2)
                continue

            # CRITICAL LOOP-SHIELD 2: Stop background mic listening operations if in cooldown.
            # Frees local thread cycles and prevents rapid continuous loop hits during API limits.
            if self.is_in_cooldown():
                self.update_hud_state("IDLE")
                time.sleep(1.0)
                continue
                
            selected_mic_str = self.combo_mic.get()
            
            # Reset connection status flags dynamically if selection changes
            if selected_mic_str != self.last_logged_mic:
                self.last_logged_mic = selected_mic_str
                self.last_mic_status = None
                
            is_auto = selected_mic_str.startswith("[AUTO]")
            targets = []
            
            if is_auto:
                targets.append((None, "Default System Microphone"))
                for idx, name in self.all_mics:
                    targets.append((idx, name))
            else:
                device_index = None
                device_name = "Default Microphone"
                try:
                    if selected_mic_str and selected_mic_str.startswith("["):
                        parts = selected_mic_str.split("] ")
                        device_index = int(parts[0][1:])
                        device_name = parts[1]
                except Exception:
                    device_index = None
                targets.append((device_index, device_name))
                
            stream_success = False
            
            for dev_index, dev_name in targets:
                if not self.is_active or self.is_muted or self.listen_session_id != session_id:
                    break
                    
                # Abort before hardware acquisition if system status changed to speaking or cooldown activated
                if self.current_status in ["SPEAKING", "PROCESSING"] or self.is_in_cooldown():
                    break

                # Log the connection attempt exactly once per manual device selection
                if not is_auto and self.last_mic_status != "connected" and self.last_mic_status != "failed_logged":
                    if self.last_mic_status != "connecting_logged":
                        self.log_to_terminal("system", f"Connecting to selected microphone: '{dev_name}'...")
                        self.last_mic_status = "connecting_logged"
                    
                for rate in [None, 16000, 44100]:
                    if not self.is_active or self.is_muted or self.current_status in ["SPEAKING", "PROCESSING"] or self.is_in_cooldown() or self.listen_session_id != session_id:
                        break
                    try:
                        mic_source = sr.Microphone(
                            device_index=dev_index,
                            sample_rate=rate or 16000
                        )
                        with mic_source as source:
                            # Connection success! Log once and reset statuses
                            if not is_auto and self.last_mic_status != "connected":
                                self.log_to_terminal("system", f"Successfully connected to microphone: '{dev_name}'!")
                                self.last_mic_status = "connected"
                            
                            self.mic_searching_logged = False
                            
                            recognizer.adjust_for_ambient_noise(source, duration=0.4)
                            
                            if not self.is_active or self.is_muted or self.current_status in ["SPEAKING", "PROCESSING"] or self.is_in_cooldown() or self.listen_session_id != session_id:
                                break
                                
                            self.update_hud_state("LISTENING")
                            recording_start = time.time() # Precise timestamp of recording initiation
                            audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                            recording_end = time.time() # Precise timestamp of recording completion
                            
                            # Block immediately if cooldown active or Jarvis started vocalizing
                            if self.is_in_cooldown() or self.current_status in ["SPEAKING", "PROCESSING"] or self.listen_session_id != session_id:
                                break

                            # VOCAL ECHO SHIELD: Discard the audio clip if we spoke at any point during or after the recording started
                            if self.last_speech_end_time > recording_start:
                                # Self-hearing detected! This clip contains Jarvis speaking. Discard immediately.
                                if self.is_muted:
                                    self.update_hud_state("MUTED")
                                else:
                                    self.update_hud_state("IDLE")
                                continue

                            self.update_hud_state("PROCESSING")
                            speech_text = recognizer.recognize_google(audio).strip()
                            
                            # Discard static & breath transcription
                            if self.is_accidental_noise(speech_text):
                                if self.is_muted:
                                    self.update_hud_state("MUTED")
                                else:
                                    self.update_hud_state("IDLE")
                                continue

                            self.log_to_terminal("user", f"({dev_name}) {speech_text}")
                            self.process_ai_response(speech_text)
                            
                        stream_success = True
                        break 
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        stream_success = True
                        if self.is_muted:
                            self.update_hud_state("MUTED")
                        else:
                            self.update_hud_state("IDLE")
                        break
                    except sr.RequestError as req_err:
                        # Google Speech API Rate-Limit/Quota Exceeded detected!
                        err_str = str(req_err)
                        self.log_to_terminal("error", f"Google Speech API Rate-Limit: {err_str}")
                        stream_success = True # Stop checking other hardware devices!
                        
                        # Parse cooldown
                        delay = 15.0
                        match = re.search(r"(\d+(\.\d+)?)", err_str)
                        if match:
                            try:
                                delay = float(match.group(1))
                            except ValueError:
                                pass
                        
                        self.cooldown_remaining = delay
                        self.cooldown_start_time = time.time()
                        self.update_queue.put(("cooldown", delay))
                        
                        time.sleep(5) # Brief pause
                        break
                    except Exception:
                        continue
                
                if stream_success:
                    break
            
            if not stream_success:
                if is_auto:
                    if not getattr(self, "mic_searching_logged", False):
                        self.log_to_terminal("system", "Quietly looking for an active microphone...")
                        self.mic_searching_logged = True
                    time.sleep(2)
                else:
                    if self.last_mic_status != "failed_logged" and self.listen_session_id == session_id:
                        self.log_to_terminal("system", f"Selected microphone '{device_name}' is busy or offline. Retrying silently in the background...")
                        self.last_mic_status = "failed_logged"
                    # If specific mic fails, sleep longer (5 seconds) to avoid CPU-spinning loop
                    time.sleep(5)
            else:
                self.mic_searching_logged = False
                
            time.sleep(0.1)

    def proactive_chatter_loop(self, session_id):
        """Monitors idle time and periodically triggers spontaneous comments if enabled."""
        time.sleep(20)
        
        while self.is_active and self.chatter_session_id == session_id:
            if not self.chatter_enabled or self.is_in_cooldown():
                time.sleep(2)
                continue
            
            current_target = self.chatter_interval
            elapsed = 0
            while elapsed < current_target:
                if not self.is_active or not self.chatter_enabled or self.is_in_cooldown() or self.chatter_session_id != session_id:
                    break
                time.sleep(1)
                elapsed += 1
                
            if not self.is_active or self.is_muted or not self.chatter_enabled or self.is_in_cooldown() or self.chatter_session_id != session_id:
                continue
                
            if self.current_status == "IDLE":
                self.trigger_spontaneous_comment()

    def trigger_spontaneous_comment(self):
        """Assembles local environmental context and asks Gemini to spark a natural conversation."""
        if self.current_status != "IDLE" or self.is_muted or self.is_in_cooldown():
            return
            
        games_status = detect_running_games()
        files_status = list_my_files()
        
        prompt = (
            f"You are {self.assistant_name}. You are checking in on your developer/friend {self.user_name}.\n"
            f"Current running games: {games_status}\n"
            f"Current files in folder: {files_status}\n\n"
            "Think of a friendly, spontaneous checking-in comment. You can either:\n"
            "- Comment on their active game in a fun, positive way.\n"
            "- Reference a file in their documents.\n"
            "- Share a brief, inspiring thought or a cool science/technology/space fact.\n\n"
            "Keep it highly conversational, friendly, and exactly 1 or 2 spoken sentences. "
            "Do not use any asterisks, markdown, or formatting. Speak directly to them."
        )
        
        threading.Thread(target=self.process_proactive_response, args=(prompt,), daemon=True).start()

    def process_proactive_response(self, prompt):
        if self.current_status != "IDLE" or self.is_muted or self.is_in_cooldown():
            return
            
        self.update_hud_state("PROCESSING")
        
        # Clean history first to keep tokens low
        self.prune_chat_history()
        
        try:
            response = self.model.generate_content(prompt)
            clean_reply = response.text.replace("*", "")
            
            if self.is_active and not self.is_muted and self.current_status == "PROCESSING":
                self.log_to_terminal("jarvis", clean_reply)
                self.speak_vocal_response(clean_reply)
            else:
                self.update_hud_state("IDLE")
        except Exception as e:
            err_msg = str(e)
            
            # Quota Check & Key Rotate Attempt!
            if self.handle_api_error_or_quota(err_msg):
                try:
                    # Retry once with the newly bound API key!
                    response = self.model.generate_content(prompt)
                    clean_reply = response.text.replace("*", "")
                    if self.is_active and not self.is_muted and self.current_status == "PROCESSING":
                        self.log_to_terminal("jarvis", clean_reply)
                        self.speak_vocal_response(clean_reply)
                    else:
                        self.update_hud_state("IDLE")
                    return
                except Exception as retry_e:
                    err_msg = str(retry_e)

            if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                self.log_to_terminal("system", "Spontaneous thoughts temporarily paused: Google API speed limits hit (429).")
                delay = 60.0
                match = re.search(r"retry in (\d+(\.\d+)?)s", err_msg)
                if match:
                    delay = float(match.group(1))
                else:
                    match2 = re.search(r"seconds:\s*(\d+)", err_msg)
                    if match2:
                        delay = float(match2.group(1))
                self.cooldown_remaining = delay
                self.cooldown_start_time = time.time()
                self.update_queue.put(("cooldown", delay))
            
            if self.is_muted:
                self.update_hud_state("MUTED")
            else:
                self.update_hud_state("IDLE")

    def process_ai_response(self, text_input):
        """Interfaces the user's voice message through Gemini with system tools integration."""
        self.update_hud_state("PROCESSING")
        
        # Safe structural pruning before calling API to keep token transmissions tiny!
        self.prune_chat_history()

        try:
            response = self.chat.send_message(text_input)
            clean_reply = response.text.replace("*", "") 
            self.log_to_terminal("jarvis", clean_reply)
            
            self.speak_vocal_response(clean_reply)
        except Exception as e:
            err_msg = str(e)
            
            # Quota Check & Key Rotate Attempt!
            if self.handle_api_error_or_quota(err_msg):
                try:
                    # Retry once with the newly rotated API Key! (History is fully preserved!)
                    response = self.chat.send_message(text_input)
                    clean_reply = response.text.replace("*", "")
                    self.log_to_terminal("jarvis", clean_reply)
                    self.speak_vocal_response(clean_reply)
                    return
                except Exception as retry_e:
                    err_msg = str(retry_e)

            if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                delay = 60.0
                match = re.search(r"retry in (\d+(\.\d+)?)s", err_msg)
                if match:
                    delay = float(match.group(1))
                else:
                    match2 = re.search(r"seconds:\s*(\d+)", err_msg)
                    if match2:
                        delay = float(match2.group(1))
                
                self.cooldown_remaining = delay
                self.cooldown_start_time = time.time()
                self.update_queue.put(("cooldown", delay))
                
                friendly_warning = (
                    f"Google API Free-Tier Quota Exceeded. Please retry in {delay:.1f} seconds.\n"
                    "Let's get this resolved:\n"
                    "1. Wait for the cooldown countdown on the HUD to reset.\n"
                    "2. Head to settings and raise the 'Chatter Delay Interval' so spontaneous comments are less frequent.\n"
                    "3. If your daily quota limit is completely full, consider registering a fresh API Key in Google AI Studio!"
                )
                self.log_to_terminal("error", friendly_warning)
                self.speak_vocal_response(f"My apologies, {self.user_name}. We have reached the Google request limit. Please wait {int(delay)} seconds.")
            else:
                self.log_to_terminal("error", f"Connection Error: {err_msg}")
                
            if self.is_muted:
                self.update_hud_state("MUTED")
            else:
                self.update_hud_state("IDLE")

    def speak_vocal_response(self, text_to_speak):
        """Outputs synthesised audio via your local output speaker port."""
        self.update_hud_state("SPEAKING")
        self.last_speech_start_time = time.time() # Track exact moment vocal output began
        try:
            safe_coinitialize()
            engine = pyttsx3.init()
            
            rate = self.slide_rate.get()
            engine.setProperty('rate', rate)
            
            selected_voice_name = self.combo_voice.get()
            voices = engine.getProperty('voices')
            for v in voices:
                if v.name == selected_voice_name:
                    engine.setProperty('voice', v.id)
                    break
            
            engine.say(text_to_speak)
            engine.runAndWait()
            engine.stop() 
        except Exception as e:
            self.log_to_terminal("error", f"Vocal emitter failed: {e}")
        finally:
            self.last_speech_end_time = time.time() # Track exact moment vocal output completed
            if self.is_muted:
                self.update_hud_state("MUTED")
            else:
                self.update_hud_state("IDLE")

    def animate_hud(self):
        """Canvas updating loop rendering our futuristic AI active status."""
        self.hud_canvas.delete("all")
        
        # Core alignment center coords
        cx, cy = 160, 90
        
        # Draw Cooldown timer status if cooling down
        is_cooling_down = False
        if hasattr(self, "cooldown_remaining") and self.cooldown_remaining > 0:
            elapsed_cooldown = time.time() - self.cooldown_start_time
            rem_cooldown = max(0.0, self.cooldown_remaining - elapsed_cooldown)
            if rem_cooldown > 0:
                is_cooling_down = True
                self.hud_canvas.create_text(cx, cy-70, text=f"LIMIT COOLDOWN: {rem_cooldown:.1f}s", fill="#EF476F", font=("Consolas", 9, "bold"))
            else:
                self.cooldown_remaining = 0.0

        if self.current_status == "LISTENING":
            # Scanning sci-fi scope loop
            self.wave_phase += 0.15
            radius_pulse = 30 + (math.sin(self.wave_phase) * 15)
            
            self.hud_canvas.create_oval(cx-radius_pulse-20, cy-radius_pulse-20, cx+radius_pulse+20, cy+radius_pulse+20, outline="#00F0FF", width=1)
            self.hud_canvas.create_oval(cx-radius_pulse, cy-radius_pulse, cx+radius_pulse, cy+radius_pulse, outline="#00B4D8", width=2)
            
            radar_angle = self.wave_phase * 2
            rx = cx + math.cos(radar_angle) * (radius_pulse + 20)
            ry = cy + math.sin(radar_angle) * (radius_pulse + 20)
            self.hud_canvas.create_line(cx, cy, rx, ry, fill="#00F0FF", width=2)
            self.hud_canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#00F0FF")
            
            self.hud_canvas.create_text(cx, cy-55, text="INPUT ARRAY ACTIVE", fill="#00F0FF", font=("Consolas", 8, "bold"))
            
        elif self.current_status == "PROCESSING":
            # Glowing core motor engine
            self.animation_angle += 8
            rad = 45
            
            for offset in [0, 90, 180, 270]:
                start_angle = (self.animation_angle + offset) % 360
                self.hud_canvas.create_arc(
                    cx-rad, cy-rad, cx+rad, cy+rad, start=start_angle, extent=45, 
                    style="arc", outline="#FF9F1C", width=3
                )
            glow = "#FF9F1C" if (self.animation_angle % 40 < 20) else "#7A431D"
            self.hud_canvas.create_oval(cx-15, cy-15, cx+15, cy+15, fill=glow, outline="")
            
            elapsed_processing = time.time() - getattr(self, "processing_start_time", time.time())
            self.hud_canvas.create_text(
                cx, cy+45, 
                text=f"WAIT TIME: {elapsed_processing:.1f}s", 
                fill="#FF9F1C", 
                font=("Consolas", 10, "bold")
            )
            
        elif self.current_status == "SPEAKING":
            # Simulated electronic sound frequency spikes
            self.wave_phase += 0.3
            
            for i in range(-7, 8):
                distance_from_center = abs(i)
                height_multiplier = max(1.0 - (distance_from_center / 7.0), 0.1)
                height = (math.sin(self.wave_phase + i * 0.5) * 40 * height_multiplier) + (random.randint(-5, 5) * height_multiplier)
                
                wx = cx + (i * 14)
                self.hud_canvas.create_line(wx, cy - height, wx, cy + height, fill="#39FF14", width=4)
                
            self.hud_canvas.create_oval(cx-120, cy-65, cx+120, cy+65, outline="#1A3E21", width=1)
            
        elif self.current_status == "MUTED":
            # Red Muted Microphone Visual
            self.hud_canvas.create_oval(cx-30, cy-30, cx+30, cy+30, outline="#FF4D4D", width=2)
            self.hud_canvas.create_line(cx-21, cy-21, cx+21, cy+21, fill="#FF4D4D", width=3)
            self.hud_canvas.create_text(cx, cy+45, text="MIC MUTED", fill="#FF4D4D", font=("Consolas", 9, "bold"))
            
        else: # IDLE STATE
            # Slow soft blue rhythmic breathing glow
            self.wave_phase += 0.04
            breath_radius = 25 + (math.sin(self.wave_phase) * 3)
            
            self.hud_canvas.create_oval(cx-75, cy-75, cx+75, cy+75, outline="#1B243B", width=1, dash=(5, 3))
            self.hud_canvas.create_oval(cx-breath_radius-8, cy-breath_radius-8, cx+breath_radius+8, cy+breath_radius+8, outline="#12405C", width=1)
            self.hud_canvas.create_oval(cx-breath_radius, cy-breath_radius, cx+breath_radius, cy+breath_radius, fill="#022B42", outline="#00F0FF", width=1)
            self.hud_canvas.create_line(cx-5, cy, cx+5, cy, fill="#00F0FF", width=1)
            self.hud_canvas.create_line(cx, cy-5, cx, cy+5, fill="#00F0FF", width=1)
            
            if self.is_active and not is_cooling_down:
                num_mics = len(self.all_mics) if self.combo_mic.get().startswith("[AUTO]") else 1
                self.hud_canvas.create_text(
                    cx, cy+55, 
                    text=f"MONITORING {num_mics} CHANNELS", 
                    fill="#00F0FF", 
                    font=("Consolas", 8)
                )

        # Draw frame again in 25ms (~40 FPS)
        self.root.after(25, self.animate_hud)

    def on_closing(self):
        """Forces threads to clean up when exit button is clicked."""
        self.is_active = False
        self.root.destroy()

# --- Jarvis System Tools (Function Calling) ---

def capture_and_analyze_screen(focus_question: str = "Comment on what is happening on the screen."):
    """
    Captures a real-time screenshot of the desktop screen (or mirrored phone display) 
    and uses AI Vision to describe and comment on the screen context (including YouTube videos).
    """
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Analyzing screen focus: '{focus_question}'")
    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        screenshot.thumbnail((1024, 1024))
        
        safe_prompt = (
            f"Analyze the attached image based on this question: '{focus_question}'.\n"
            "Provide a wholesome, clean, and safe commentary (appropriate for teens under 18).\n"
            "If they are watching a YouTube video, tell me about it. "
            "If they are looking at notes, code, or a mirrored phone screen, comment on it. "
            "Keep your commentary to exactly 1 or 2 spoken sentences. Avoid reading aloud passwords or personal codes."
        )
        
        vision_model = genai.GenerativeModel('gemini-2.5-flash')
        response = vision_model.generate_content([safe_prompt, screenshot])
        return response.text
    except ImportError:
        return "The screen capture system requires the Pillow library. Run 'pip install Pillow' in your terminal."
    except Exception as e:
        return f"Could not capture screen details: {str(e)}"

def play_youtube_video(search_term: str):
    """
    Searches and plays a safe, clean, educational, or fun YouTube video based on a search term 
    (e.g., cool science experiments, coding tutorials, wholesome animal facts, or clean gameplay).
    """
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Searching YouTube for '{search_term}'")
    clean_term = re.sub(r'[^a-zA-Z0-9\s-]', '', search_term)
    clean_term += " clean educational wholesome safe"
    encoded_query = urllib.parse.quote(clean_term)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    
    webbrowser.open(url)
    return f"I launched a safe, wholesome search for '{search_term}' on YouTube. Pick your favorite video to watch!"

def open_website(url: str):
    """Opens a web browser directly to the specified URL."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Launching website: {url}")
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)
    return f"I have successfully launched your browser to {url}."

def search_web(query: str):
    """Searches Google for the given query."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Querying search engine for '{query}'")
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"I have processed a search inquiry for '{query}' and loaded the results on your screen."

def get_current_time():
    """Returns the current date and time formatted nicely including exact seconds."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Fetching current system time.")
    now = datetime.datetime.now().strftime("%I:%M:%S %p on %A, %B %d, %Y")
    return f"System calculations indicate the current time is {now}."

def open_calculator():
    """Opens the calculator application on the operating system."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Requesting system Calculator.")
    os_name = platform.system().lower()
    try:
        if "windows" in os_name:
            subprocess.Popen("calc.exe")
        elif "darwin" in os_name: # MacOS
            subprocess.Popen(["open", "-a", "Calculator"])
        return "The calculation unit is initialized and open."
    except Exception:
        return "I was unable to launch the desktop calculator, but you can tell me what math you need done!"

def get_system_info():
    """Returns safe, general information about the user's operating system and computer setup."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Querying platform host specifications.")
    info = {
        "OS": platform.system(),
        "Version": platform.release(),
        "Machine Architecture": platform.machine(),
        "Processor": platform.processor(),
        "Python Version": platform.python_version()
    }
    return f"System Specifications: Operating System: {info['OS']}, Version: {info['Version']}, Processor: {info['Processor'] or 'Generic'}, Architecture: {info['Machine Architecture']}."

def open_application(app_name: str):
    """
    Attempts to safely launch a requested standard desktop application.
    Allowed friendly names: notepad, paint, wordpad, task manager, explorer, cmd.
    """
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Launching system program: '{app_name}'")
    app_name_lower = app_name.lower().strip()
    os_name = platform.system().lower()
    
    windows_apps = {
        "notepad": "notepad.exe",
        "paint": "mspaint.exe",
        "wordpad": "write.exe",
        "task manager": "taskmgr.exe",
        "explorer": "explorer.exe",
        "command prompt": "cmd.exe",
        "file explorer": "explorer.exe"
    }
    
    mac_apps = {
        "notepad": "TextEdit",
        "textedit": "TextEdit",
        "paint": "Preview",
        "explorer": "Finder",
        "finder": "Finder",
        "safari": "Safari"
    }
    
    if "windows" in os_name:
        if app_name_lower in windows_apps:
            try:
                subprocess.Popen(windows_apps[app_name_lower], shell=False)
                return f"Successfully opened {app_name_lower}."
            except Exception as e:
                return f"Failed to open {app_name_lower}: {str(e)}"
        else:
            if app_name_lower.isalnum():
                try:
                    subprocess.Popen(f"{app_name_lower}.exe", shell=False)
                    return f"Sent command to open {app_name_lower}."
                except Exception:
                    return f"I couldn't locate '{app_name_lower}' on your machine. Let's try opening standard tools like notepad, paint, or task manager."
            else:
                return "For safety, I can only launch applications with simple, single-word alphanumeric names."
                
    elif "darwin" in os_name: # macOS
        if app_name_lower in mac_apps:
            try:
                subprocess.Popen(["open", "-a", mac_apps[app_name_lower]], shell=False)
                return f"Successfully opened {app_name_lower}."
            except Exception as e:
                return f"Failed to open: {str(e)}"
        else:
            if app_name_lower.isalnum():
                try:
                    subprocess.Popen(["open", "-a", app_name], shell=False)
                    return f"Requested macOS to open {app_name}."
                except Exception:
                    return f"Unable to open {app_name}."
            else:
                return "For security, application names must be alphanumeric."
    else:
        return "Application launching is currently optimized for Windows and macOS environments."

def list_my_files():
    """Lists all text files (.txt, .md, .json, .rtf, .csv) inside the local 'Jarvis_Documents' folder."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Scanning document index inside Jarvis_Documents.")
    try:
        if not os.path.exists(SAFE_DIR):
            return "The Jarvis_Documents folder does not exist."
        files = os.listdir(SAFE_DIR)
        allowed_extensions = {".txt", ".md", ".json", ".rtf", ".csv"}
        safe_files = [f for f in files if os.path.splitext(f)[1].lower() in allowed_extensions]
        if not safe_files:
            return "There are currently no text documents inside the 'Jarvis_Documents' folder."
        return f"Files currently available in your shared directory: {', '.join(safe_files)}"
    except Exception as e:
        return f"Failed to query files directory: {str(e)}"

def read_my_file(filename: str):
    """
    Reads the textual contents of a safe file in the 'Jarvis_Documents' folder.
    Allowed formats are strictly limited to text file extensions (.txt, .md, .json, .rtf, .csv).
    """
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Reading local document: '{filename}'")
    try:
        safe_name = os.path.basename(filename)
        target_path = os.path.join(SAFE_DIR, safe_name)
        
        allowed_extensions = {".txt", ".md", ".json", ".rtf", ".csv"}
        if os.path.splitext(safe_name)[1].lower() not in allowed_extensions:
            return "File access rejected. For safety, I am only authorized to view standard text and data formats."
        
        if not os.path.exists(target_path):
            return f"The file '{safe_name}' could not be located in your 'Jarvis_Documents' shared folder."
            
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(1500)
            
        return f"Content readout of '{safe_name}':\n{content}"
    except Exception as e:
        return f"Error trying to read local document: {str(e)}"

def detect_running_games():
    """Checks the system's active process log to see if popular clean, friendly video games are running."""
    if ACTIVE_APP:
        ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Checking active processes for clean games.")
    os_name = platform.system().lower()
    running_games = []
    
    game_list = {
        "minecraft": "Minecraft",
        "roblox": "Roblox",
        "fortnite": "Fortnite",
        "valorant": "Valorant",
        "league": "League of Legends",
        "brawlhalla": "Brawlhalla",
        "steam": "Steam",
        "genshin": "Genshin Impact",
        "epicgames": "Epic Games Launcher",
        "cs2": "Counter-Strike 2",
        "csgo": "Counter-Strike: Global Offensive",
        "hl2": "Half-Life 2",
        "halflife": "Half-Life",
        "portal": "Portal",
        "portal2": "Portal 2",
        "left4dead": "Left 4 Dead",
        "left 4 dead": "Left 4 Dead",
        "lethal company": "Lethal Company",
        "lethalcompany": "Lethal Company",
        "dota": "Dota 2",
        "team fortress": "Team Fortress 2",
        "tf2": "Team Fortress 2"
    }
    
    try:
        if "windows" in os_name:
            output = subprocess.check_output("tasklist /FO CSV", shell=False, creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore')
            output_lower = output.lower()
            for key, name in game_list.items():
                if key in output_lower:
                    running_games.append(name)
                    
        elif "darwin" in os_name:
            output = subprocess.check_output(["ps", "-ax"], shell=False).decode('utf-8', errors='ignore')
            output_lower = output.lower()
            for key, name in game_list.items():
                if key in output_lower:
                    running_games.append(name)
    except Exception:
        pass
        
    if running_games:
        return f"Detected running games: {', '.join(running_games)}. Comment on this in a fun, friendly, and enthusiastic way!"
    return "No running gaming platforms detected right now. Ask the user what game they are currently playing or what their favorite game is!"

if __name__ == "__main__":
    root_window = tk.Tk()
    app = JarvisApp(root_window)
    root_window.mainloop()
