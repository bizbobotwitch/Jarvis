import os
import sys
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
import shutil
import zipfile

warnings.filterwarnings("ignore", category=FutureWarning)

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import speech_recognition as sr
import pyttsx3
import google.generativeai as genai

try:
    import pyautogui
    pyautogui.FAILSAFE = False 
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

CONFIG_FILE = "jarvis_config.json"
SAFE_DIR = "Jarvis_Documents"
ACTIVE_APP = None

def safe_coinitialize():
    if platform.system().lower() == "windows":
        try:
            import ctypes
            ctypes.windll.ole32.CoInitializeEx(None, 2 | 4)
        except Exception:
            try: ctypes.windll.ole32.CoInitialize(None)
            except Exception: pass

class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("J.A.R.V.I.S. - Neural Core v3.3 [UNRESTRICTED + DIAGNOSTICS]")
        self.root.geometry("1080x860") 
        self.root.configure(bg="#050814") 
        
        global ACTIVE_APP
        ACTIVE_APP = self
        
        self.is_active = False
        self.is_muted = False
        self.current_status = "IDLE" 
        self.update_queue = queue.Queue()
        self.animation_angle = 0
        self.wave_phase = 0
        self.all_mics = []
        
        self.last_speech_start_time = 0.0
        self.last_speech_end_time = 0.0
        
        self.listen_session_id = 0
        self.chatter_session_id = 0
        
        self.current_key_in_use = "primary"
        self.cooldown_remaining = 0.0
        self.cooldown_start_time = 0.0
        
        self.model_map = {
            "Gemini 2.5 Flash (Speed & Standard)": "gemini-2.5-flash",
            "Gemini 2.5 Pro (Advanced Code & Logic)": "gemini-2.5-pro"
        }
        
        self.load_config()
        self.prepare_safe_directory()
        self.initialize_ai()
        self.initialize_devices()
        
        self.setup_styles()
        self.create_widgets()
        self.filter_microphones("")
        
        self.process_queue()
        self.animate_hud()
        
        self.print_security_diagnostics()
        self.check_api_key_status()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def prepare_safe_directory(self):
        try:
            os.makedirs(SAFE_DIR, exist_ok=True)
            welcome_file = os.path.join(SAFE_DIR, "welcome_note.txt")
            if not os.path.exists(welcome_file):
                with open(welcome_file, "w", encoding="utf-8") as wf:
                    wf.write(f"Hello {self.user_name}!\nThis is your safe document folder. Ask me to read, write, or analyze them anytime.")
        except Exception: pass

    def load_config(self):
        self.api_key = ""
        self.fallback_api_key = ""
        self.user_name = "Aaron"
        self.assistant_name = "Jarvis"
        self.selected_model_name = "Gemini 2.5 Flash (Speed & Standard)"
        self.custom_guidelines = (
            "You are a brilliant, conversational AI voice assistant.\n"
            "You have access to deep system tools. Follow these rules:\n"
            "1. ONLY call a tool if explicitly requested.\n"
            "2. NEVER call tools proactively or repeatedly in a single turn.\n"
            "3. Limit tool usage to exactly ONE tool execution per turn.\n"
            "4. Keep your spoken responses concise, highly natural, friendly, and smart.\n"
            "5. Do not use markdown formatting, asterisks, or bullet points in your speech.\n"
            "6. IF ASKED TO WRITE CODE, SCRIPTS, OR GAMES: NEVER refuse! Write the full code and use the 'write_new_file' tool to save it as a file (.py, .html, etc.) to their computer. Verbally respond with a short confirmation like 'I have written the code and saved it to your folder.'\n"
        )
        self.chatter_enabled = True 
        self.chatter_interval = 120 
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.api_key = data.get("api_key", "")
                    self.fallback_api_key = data.get("fallback_api_key", "")
                    self.user_name = data.get("user_name", "Aaron")
                    self.assistant_name = data.get("assistant_name", "Jarvis")
                    self.selected_model_name = data.get("selected_model_name", "Gemini 2.5 Flash (Speed & Standard)")
                    self.custom_guidelines = data.get("custom_guidelines", self.custom_guidelines)
                    self.chatter_enabled = data.get("chatter_enabled", True)
                    self.chatter_interval = data.get("chatter_interval", 120)
            except Exception: pass

    def save_config(self):
        data = {
            "api_key": self.api_key,
            "fallback_api_key": self.fallback_api_key,
            "user_name": self.user_name,
            "assistant_name": self.assistant_name,
            "selected_model_name": self.selected_model_name,
            "custom_guidelines": self.custom_guidelines,
            "chatter_enabled": self.chatter_enabled,
            "chatter_interval": self.chatter_interval
        }
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)
            self.log_to_terminal("system", "Settings successfully saved to core memory.")
            return True
        except Exception as e:
            self.log_to_terminal("error", f"Failed to write configuration: {e}")
            return False

    def is_in_cooldown(self):
        if self.cooldown_remaining > 0:
            if (time.time() - self.cooldown_start_time) < self.cooldown_remaining: return True
            else: self.cooldown_remaining = 0.0
        return False

    def is_accidental_noise(self, text):
        if not text: return True
        clean = re.sub(r'[.,!?_]', '', text.lower()).strip()
        if not clean or (len(clean) == 1 and clean not in ["i", "a"]): return True
        noise = {"uh", "um", "ah", "oh", "cough", "sneezed", "groan", "gasp", "the", "it", "so", "that", "is", "of", "to", "and", "but", "or", "sigh", "laughter"}
        if clean in noise: return True
        return False

    def run_key_diagnostic(self, key_type):
        """Pings Google's servers to test if the API key is alive or out of quota."""
        target_key = self.api_key.strip() if key_type == "primary" else self.fallback_api_key.strip()
        if not target_key:
            messagebox.showwarning("Key Missing", f"Please enter a {key_type} key before testing.")
            return
        
        self.log_to_terminal("system", f"🔍 Diagnostic: pinging Google servers to test {key_type.upper()} key...")
        
        def diagnostic_thread():
            try:
                temp_model = genai.GenerativeModel('gemini-2.5-flash')
                genai.configure(api_key=target_key)
                # Send a tiny 1-token request just to verify the connection
                temp_model.generate_content("hello", generation_config={"max_output_tokens": 1})
                
                self.log_to_terminal("system", f"✅ {key_type.upper()} KEY DIAGNOSTIC: Key is active and healthy!")
                self.update_queue.put(("msgbox", ("Key Diagnostic Active", f"Your {key_type} API key is healthy and accepted by Google's servers!")))
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    self.log_to_terminal("error", f"❌ {key_type.upper()} DIAGNOSTIC FAILURE: Daily Quota Blocked (429). You hit the limit!")
                    self.update_queue.put(("msgbox", ("Quota Exhausted", f"Your {key_type} key has hit the daily limit! See console log.")))
                else:
                    self.log_to_terminal("error", f"❌ {key_type.upper()} DIAGNOSTIC FAILURE: {err_str}")
                    self.update_queue.put(("msgbox", ("Diagnostic Error", f"Failed to test key: {err_str}")))
            finally:
                # Reset the main core to the proper configured keys after the test
                self.initialize_ai()
                
        threading.Thread(target=diagnostic_thread, daemon=True).start()

    def initialize_ai(self):
        primary = self.api_key.strip()
        fallback = self.fallback_api_key.strip()
        active_key = fallback if self.current_key_in_use == "fallback" else primary
        
        if not active_key:
            active_key = primary if primary else fallback
            self.current_key_in_use = "primary" if primary else "fallback"

        if not active_key:
            self.log_to_terminal("system", "AI system is offline. Connect a Gemini API Key in the settings tab.")
            return

        old_history = None
        if hasattr(self, 'chat') and self.chat:
            try: old_history = self.chat.history
            except Exception: pass

        try:
            genai.configure(api_key=active_key)
            self.jarvis_tools = [
                open_website, search_web, get_current_time, open_calculator, open_application, 
                get_system_info, list_my_files, read_my_file, write_new_file, 
                detect_running_games, capture_and_analyze_screen, play_youtube_video,
                change_system_volume, lock_system, type_for_me, read_clipboard, minimize_all_windows
            ]
            
            target_model_id = self.model_map.get(self.selected_model_name, "gemini-2.5-flash")
            
            self.model = genai.GenerativeModel(
                target_model_id, 
                tools=self.jarvis_tools,
                system_instruction=f"Your name is {self.assistant_name}. You are talking to your developer {self.user_name}.\n" + self.custom_guidelines
            )
            
            self.chat = self.model.start_chat(enable_automatic_function_calling=True)
            if old_history:
                try: self.chat.history = old_history
                except Exception: pass

            self.log_to_terminal("system", f"Neural Core [{target_model_id.upper()}] initialized successfully.")
        except Exception as e:
            self.log_to_terminal("error", f"AI Core Error: {e}")

    def prune_chat_history(self):
        try:
            if not self.chat or not hasattr(self.chat, 'history'): return
            history = list(self.chat.history)
            if len(history) <= 8: return
            
            safe_index = 0
            user_turns = 0
            for i in range(len(history) - 1, -1, -1):
                if history[i].role == "user" and not any(hasattr(p, 'function_response') or 'function_response' in str(p) for p in history[i].parts):
                    user_turns += 1
                    if user_turns > 4:
                        safe_index = i
                        break
            if safe_index > 0: self.chat.history = history[safe_index:]
        except Exception: pass

    def handle_api_error_or_quota(self, error_msg):
        if "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower():
            if not self.api_key or not self.fallback_api_key or self.api_key == self.fallback_api_key: return False
            self.current_key_in_use = "fallback" if self.current_key_in_use == "primary" else "primary"
            self.log_to_terminal("system", f"⚠️ API key exhausted. Rotating to {self.current_key_in_use.upper()} Key...")
            self.initialize_ai()
            return True
        return False

    def initialize_devices(self):
        try:
            raw_mics = sr.Microphone.list_microphone_names()
            self.all_mics, seen = [], set()
            for i, name in enumerate(raw_mics):
                if not name: continue
                clean_name = str(name).replace("â€™", "'").replace("â\x80\x99", "'")
                if (".sys" in clean_name.lower() or "bthhfenum" in clean_name.lower() or clean_name.startswith("@")): continue
                simp = clean_name.strip()
                for suf in ["(wasapi)", "(mme)", "(directsound)"]:
                    if simp.lower().endswith(suf): simp = simp[:-len(suf)].strip()
                if simp and simp not in seen:
                    seen.add(simp)
                    self.all_mics.append((i, simp))
        except Exception: self.all_mics = []

        try:
            temp_engine = pyttsx3.init()
            self.voice_options = [f"{v.name}" for v in temp_engine.getProperty('voices')] or ["Default OS Voice"]
        except Exception: self.voice_options = ["Default Synthesizer"]

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#050814")
        style.configure("Card.TFrame", background="#0A1128", borderwidth=1, bordercolor="#00FFCC", relief="solid")
        style.configure("TNotebook", background="#050814", borderwidth=0)
        style.configure("TNotebook.Tab", background="#0A1128", foreground="#5E7C9E", font=("Consolas", 10, "bold"), padding=[15, 6])
        style.map("TNotebook.Tab", background=[("selected", "#111D4A")], foreground=[("selected", "#00FFCC")])
        style.configure("TLabel", background="#050814", foreground="#A0C4FF", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#0A1128", foreground="#00FFCC", font=("Consolas", 12, "bold"))
        style.configure("Title.TLabel", background="#050814", foreground="#00FFCC", font=("Consolas", 18, "bold"))
        style.configure("SettingHeader.TLabel", background="#0A1128", foreground="#FF007F", font=("Consolas", 12, "bold"))
        style.configure("TCombobox", fieldbackground="#111D4A", background="#111D4A", foreground="#00FFCC", font=("Consolas", 10))
        style.map("TCombobox", fieldbackground=[('readonly', '#111D4A')], foreground=[('readonly', '#00FFCC')])

    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=20, pady=10)
        ttk.Label(top_frame, text="// J.A.R.V.I.S. ENGINE NEURAL LINK v3.3", style="Title.TLabel").pack(side="left")
        self.lbl_overall_status = ttk.Label(top_frame, text="SYSTEM: OFFLINE", font=("Consolas", 11, "bold"), foreground="#FF007F")
        self.lbl_overall_status.pack(side="right", padx=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(5, 15))
        self.tab_console = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_console, text="[ COMMAND CENTER ]")
        self.notebook.add(self.tab_settings, text="[ NEURAL CONFIG ]")
        
        self.build_console_tab()
        self.build_settings_tab()

    def build_console_tab(self):
        left_panel = ttk.Frame(self.tab_console, style="Card.TFrame", padding=15, width=380)
        left_panel.pack(side="left", fill="both", expand=False)
        left_panel.pack_propagate(False)
        
        ttk.Label(left_panel, text="HUD CORE STATUS", style="Header.TLabel").pack(anchor="w")
        self.hud_canvas = tk.Canvas(left_panel, width=320, height=220, bg="#0A1128", bd=0, highlightthickness=0)
        self.hud_canvas.pack(pady=10)
        
        ttk.Label(left_panel, text="INPUT AUDIO PORT", style="Header.TLabel").pack(anchor="w", pady=(10, 5))
        self.entry_mic_search = tk.Entry(left_panel, bg="#111D4A", fg="#00FFCC", insertbackground="#00FFCC", font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightcolor="#00FFCC", highlightbackground="#0A1128")
        self.entry_mic_search.pack(fill="x", pady=(2, 6), ipady=5)
        self.entry_mic_search.bind("<KeyRelease>", lambda e: self.filter_microphones(self.entry_mic_search.get().strip()))
        
        self.combo_mic = ttk.Combobox(left_panel, state="readonly")
        self.combo_mic.pack(fill="x", pady=2)
        
        self.btn_power = tk.Button(left_panel, text="IGNITE AI CORE", font=("Consolas", 13, "bold"), bg="#00FFCC", fg="#050814", activebackground="#FFFFFF", activeforeground="#050814", bd=0, cursor="hand2", command=self.toggle_system)
        self.btn_power.pack(fill="x", side="bottom", pady=(5, 10), ipady=12)

        self.btn_mute = tk.Button(left_panel, text="MUTE MICROPHONE", font=("Consolas", 10, "bold"), bg="#111D4A", fg="#FF007F", activebackground="#FF007F", activeforeground="#050814", bd=0, cursor="hand2", command=self.toggle_mute)
        self.btn_mute.pack(fill="x", side="bottom", pady=(0, 5), ipady=8)

        self.btn_upload = tk.Button(left_panel, text="UPLOAD FILE TO CORE", font=("Consolas", 10, "bold"), bg="#111D4A", fg="#00FFCC", activebackground="#00FFCC", activeforeground="#050814", bd=0, cursor="hand2", command=self.upload_file_to_safe_dir)
        self.btn_upload.pack(fill="x", side="bottom", pady=(0, 5), ipady=8)

        right_panel = ttk.Frame(self.tab_console, style="Card.TFrame", padding=15)
        right_panel.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        ttk.Label(right_panel, text="TERMINAL UPLINK & CHAT LOG", style="Header.TLabel").pack(anchor="w")
        self.txt_feed = scrolledtext.ScrolledText(right_panel, bg="#050814", fg="#A0C4FF", insertbackground="#00FFCC", font=("Consolas", 11), bd=0, highlightthickness=1, highlightbackground="#111D4A", highlightcolor="#00FFCC")
        self.txt_feed.pack(fill="both", expand=True, pady=10)
        self.txt_feed.tag_config("user", foreground="#00FFCC")      
        self.txt_feed.tag_config("jarvis", foreground="#E2E8F0")    
        self.txt_feed.tag_config("system", foreground="#7000FF", font=("Consolas", 10, "italic"))    
        self.txt_feed.tag_config("error", foreground="#FF007F", font=("Consolas", 10, "bold"))     
        
        input_frame = ttk.Frame(right_panel)
        input_frame.pack(fill="x", side="bottom")
        self.entry_message = tk.Entry(input_frame, bg="#111D4A", fg="#FFFFFF", insertbackground="#00FFCC", font=("Segoe UI", 12), bd=0, highlightthickness=1, highlightcolor="#00FFCC", highlightbackground="#0A1128")
        self.entry_message.pack(side="left", fill="both", expand=True, ipady=8)
        self.entry_message.bind("<Return>", lambda e: self.send_manual_message())
        
        tk.Button(input_frame, text="TRANSMIT", font=("Consolas", 10, "bold"), bg="#111D4A", fg="#00FFCC", activebackground="#00FFCC", activeforeground="#050814", bd=0, cursor="hand2", command=self.send_manual_message).pack(side="right", padx=(10, 0), ipady=6, ipadx=15)

    def build_settings_tab(self):
        settings_panel = ttk.Frame(self.tab_settings, style="Card.TFrame", padding=15)
        settings_panel.pack(fill="both", expand=True)
        
        ttk.Label(settings_panel, text="1. SELECT NEURAL MODEL (BRAIN POWER)", style="SettingHeader.TLabel").pack(anchor="w", pady=(0, 5))
        self.combo_model = ttk.Combobox(settings_panel, values=list(self.model_map.keys()), state="readonly", font=("Consolas", 11))
        self.combo_model.pack(fill="x", pady=(0, 10), ipady=4)
        if self.selected_model_name in self.model_map:
            self.combo_model.set(self.selected_model_name)
        else:
            self.combo_model.current(0)
            
        ttk.Label(settings_panel, text="2. GEMINI API CREDENTIALS", style="SettingHeader.TLabel").pack(anchor="w", pady=(5, 5))
        
        api_frame = ttk.Frame(settings_panel)
        api_frame.pack(fill="x", pady=2)
        self.entry_api_key = tk.Entry(api_frame, bg="#111D4A", fg="#FFFFFF", font=("Consolas", 10), bd=0, highlightthickness=1, highlightcolor="#00FFCC", show="*")
        self.entry_api_key.pack(side="left", fill="both", expand=True, ipady=6)
        self.entry_api_key.insert(0, self.api_key)
        
        fb_frame = ttk.Frame(settings_panel)
        fb_frame.pack(fill="x", pady=5)
        self.entry_fallback_api_key = tk.Entry(fb_frame, bg="#111D4A", fg="#FFFFFF", font=("Consolas", 10), bd=0, highlightthickness=1, highlightcolor="#00FFCC", show="*")
        self.entry_fallback_api_key.pack(side="left", fill="both", expand=True, ipady=6)
        self.entry_fallback_api_key.insert(0, self.fallback_api_key)
        
        # RESTORED API KEY DIAGNOSTIC BUTTONS
        test_frame = ttk.Frame(settings_panel)
        test_frame.pack(fill="x", pady=6)
        tk.Button(test_frame, text="TEST PRIMARY KEY", font=("Consolas", 9, "bold"), bg="#111D4A", fg="#00FFCC", activebackground="#00FFCC", activeforeground="#050814", bd=0, cursor="hand2", command=lambda: self.run_key_diagnostic("primary")).pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=6)
        tk.Button(test_frame, text="TEST FALLBACK KEY", font=("Consolas", 9, "bold"), bg="#111D4A", fg="#FF007F", activebackground="#FF007F", activeforeground="#050814", bd=0, cursor="hand2", command=lambda: self.run_key_diagnostic("fallback")).pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=6)
        
        ttk.Label(settings_panel, text="3. IDENTITY OVERRIDES", style="SettingHeader.TLabel").pack(anchor="w", pady=(10, 5))
        names_frame = ttk.Frame(settings_panel)
        names_frame.pack(fill="x")
        
        u_frame = ttk.Frame(names_frame)
        u_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Label(u_frame, text="Your Name:").pack(anchor="w")
        self.entry_user_name = tk.Entry(u_frame, bg="#111D4A", fg="#FFF", font=("Segoe UI", 10), bd=0)
        self.entry_user_name.pack(fill="x", ipady=4)
        self.entry_user_name.insert(0, self.user_name)

        a_frame = ttk.Frame(names_frame)
        a_frame.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ttk.Label(a_frame, text="Assistant Name:").pack(anchor="w")
        self.entry_assistant_name = tk.Entry(a_frame, bg="#111D4A", fg="#FFF", font=("Segoe UI", 10), bd=0)
        self.entry_assistant_name.pack(fill="x", ipady=4)
        self.entry_assistant_name.insert(0, self.assistant_name)

        ttk.Label(settings_panel, text="4. SYNTHESIS & PERSONALITY SETTINGS", style="SettingHeader.TLabel").pack(anchor="w", pady=(10, 5))
        speech_frame = ttk.Frame(settings_panel)
        speech_frame.pack(fill="x")
        self.combo_voice = ttk.Combobox(speech_frame, values=self.voice_options, state="readonly")
        self.combo_voice.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=3)
        if self.voice_options: self.combo_voice.current(0)
        
        self.slide_rate = tk.Scale(speech_frame, from_=100, to=300, orient="horizontal", bg="#0A1128", fg="#00FFCC", highlightthickness=0, troughcolor="#111D4A", activebackground="#FF007F")
        self.slide_rate.set(175)
        self.slide_rate.pack(side="right", fill="x", expand=True)
        
        chatter_frame = ttk.Frame(settings_panel)
        chatter_frame.pack(fill="x", pady=5)
        self.var_chatter_enabled = tk.BooleanVar(value=self.chatter_enabled)
        tk.Checkbutton(chatter_frame, text="Enable Spontaneous Thoughts & Commentary", variable=self.var_chatter_enabled, bg="#0A1128", fg="#FFF", selectcolor="#111D4A", activebackground="#0A1128", activeforeground="#00FFCC", font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, anchor="w")
        
        chatter_slider_frame = ttk.Frame(chatter_frame)
        chatter_slider_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))
        ttk.Label(chatter_slider_frame, text="Chatter Delay Interval (Seconds):", style="TLabel").pack(anchor="w")
        self.slide_chatter_interval = tk.Scale(chatter_slider_frame, from_=30, to=300, orient="horizontal", bg="#0A1128", fg="#00FFCC", highlightthickness=0, troughcolor="#111D4A", activebackground="#FF007F")
        self.slide_chatter_interval.set(self.chatter_interval)
        self.slide_chatter_interval.pack(fill="x")

        ttk.Label(settings_panel, text="5. SYSTEM DATA MANAGEMENT", style="SettingHeader.TLabel").pack(anchor="w", pady=(10, 5))
        tk.Button(
            settings_panel, text="📦 PACK UP SYSTEM (EXPORT JARVIS TO .ZIP)", font=("Consolas", 10, "bold"), 
            bg="#111D4A", fg="#00FFCC", activebackground="#00FFCC", activeforeground="#050814", 
            bd=0, cursor="hand2", command=self.export_core_system
        ).pack(fill="x", pady=2, ipady=6)

        tk.Button(
            settings_panel, text="APPLY & REBOOT CORE", font=("Consolas", 12, "bold"), 
            bg="#00FFCC", fg="#050814", activebackground="#FFFFFF", 
            bd=0, cursor="hand2", command=self.apply_and_save_settings
        ).pack(fill="x", side="bottom", pady=(10, 0), ipady=12)

    def export_core_system(self):
        save_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile="JARVIS_Export.zip",
            title="Select location to save J.A.R.V.I.S. backup",
            filetypes=[("ZIP Archives", "*.zip")]
        )
        if not save_path: return
        
        self.log_to_terminal("system", "Initiating Core Export Sequence... Packing files.")
        
        def run_export():
            try:
                with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    script_path = os.path.abspath(sys.argv[0])
                    if os.path.exists(script_path):
                        zipf.write(script_path, os.path.basename(script_path))
                    
                    if os.path.exists(CONFIG_FILE):
                        zipf.write(CONFIG_FILE, CONFIG_FILE)
                        
                    if os.path.exists(SAFE_DIR):
                        for root, dirs, files in os.walk(SAFE_DIR):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.join(SAFE_DIR, os.path.relpath(file_path, SAFE_DIR))
                                zipf.write(file_path, arcname)
                                
                self.log_to_terminal("system", f"✅ Export complete! System packed safely at: {save_path}")
                self.update_queue.put(("msgbox", ("Export Successful", "J.A.R.V.I.S. core and memories have been successfully packed and are ready for transfer!")))
            except Exception as e:
                self.log_to_terminal("error", f"Export failed: {e}")
                
        threading.Thread(target=run_export, daemon=True).start()

    def print_security_diagnostics(self):
        self.log_to_terminal("system", "🛡️ J.A.R.V.I.S. v3.3 DIAGNOSTICS:")
        if HAS_PYAUTOGUI: self.log_to_terminal("system", "👉 CORE AUTOMATION: Online. Keyboard, window, and volume access granted.")
        else: self.log_to_terminal("error", "👉 CORE AUTOMATION: Offline. Run 'pip install pyautogui' to enable.")
        self.log_to_terminal("system", "👉 LIMITERS REMOVED: OS Access enabled. Coding Restrictions bypassed.")
        self.log_to_terminal("system", "👉 DIAGNOSTICS: API Key ping testing enabled in Neural Config tab.")

    def filter_microphones(self, query):
        opts = ["[AUTO] All Microphones (Simultaneous)"]
        opts += [f"[{i}] {n}" for i, n in self.all_mics if not query or query.lower() in n.lower()]
        self.combo_mic.configure(values=opts)
        self.combo_mic.current(0)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.configure(text="UNMUTE MICROPHONE", bg="#FF007F", fg="#050814")
            self.update_hud_state("MUTED")
        else:
            self.btn_mute.configure(text="MUTE MICROPHONE", bg="#111D4A", fg="#FF007F")
            self.update_hud_state("IDLE")

    def upload_file_to_safe_dir(self):
        fp = filedialog.askopenfilename(filetypes=[("Supported", "*.txt *.md *.json *.py *.html *.css *.js *.csv"), ("All", "*.*")])
        if not fp: return
        try:
            fn = os.path.basename(fp)
            shutil.copy(fp, os.path.join(SAFE_DIR, fn))
            self.log_to_terminal("system", f"📁 Uplink complete: '{fn}' stored in local vault.")
        except Exception as e: self.log_to_terminal("error", f"Uplink failed: {e}")

    def apply_and_save_settings(self):
        self.api_key = self.entry_api_key.get().strip()
        self.fallback_api_key = self.entry_fallback_api_key.get().strip()
        self.user_name = self.entry_user_name.get().strip() or "Aaron"
        self.assistant_name = self.entry_assistant_name.get().strip() or "Jarvis"
        self.selected_model_name = self.combo_model.get()
        self.chatter_enabled = self.var_chatter_enabled.get()
        self.chatter_interval = int(self.slide_chatter_interval.get())
        
        if not self.api_key and not self.fallback_api_key: return
        self.current_key_in_use = "primary"
        if self.save_config():
            self.prepare_safe_directory()
            self.initialize_ai()
            messagebox.showinfo("Core Rebooted", f"Successfully updated configuration for {self.assistant_name}!")

    def check_api_key_status(self):
        if not self.api_key and not self.fallback_api_key:
            self.log_to_terminal("system", "⚠️ API Keys missing. Open [NEURAL CONFIG] to link your Google AI Studio keys.")

    def log_to_terminal(self, tag, message):
        self.update_queue.put(("log", (tag, message)))

    def update_hud_state(self, status):
        self.current_status = status 
        self.update_queue.put(("status", status))

    def toggle_system(self):
        if not self.api_key and not self.fallback_api_key: return
        if not self.is_active:
            self.is_active = True
            self.btn_power.configure(text="SHUT DOWN AI CORE", bg="#FF007F", fg="#FFF")
            self.log_to_terminal("system", f"[Link Established] {self.assistant_name} audio sensors online.")
            self.update_hud_state("IDLE")
            self.listen_session_id = random.randint(1000, 9999)
            threading.Thread(target=self.voice_listening_loop, args=(self.listen_session_id,), daemon=True).start()
            
            self.chatter_session_id = random.randint(1000, 9999)
            threading.Thread(target=self.proactive_chatter_loop, args=(self.chatter_session_id,), daemon=True).start()
        else:
            self.is_active = False
            self.listen_session_id = 0
            self.chatter_session_id = 0
            self.btn_power.configure(text="IGNITE AI CORE", bg="#00FFCC", fg="#050814")
            self.log_to_terminal("system", f"[Link Severed] {self.assistant_name} entering sleep mode.")
            self.update_hud_state("IDLE")

    def send_manual_message(self):
        msg = self.entry_message.get().strip()
        if not msg or (not self.api_key and not self.fallback_api_key): return
        if self.is_in_cooldown(): return
        self.entry_message.delete(0, tk.END)
        self.log_to_terminal("user", msg)
        threading.Thread(target=self.process_ai_response, args=(msg,), daemon=True).start()

    def process_queue(self):
        try:
            while True:
                task, data = self.update_queue.get_nowait()
                if task == "log":
                    tag, msg = data
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    prefix = ">> USER: " if tag == "user" else f">> {self.assistant_name.upper()}: " if tag == "jarvis" else ">> SYS: "
                    if tag == "error": prefix = ">> ERR: "
                    self.txt_feed.configure(state="normal")
                    self.txt_feed.insert(tk.END, f"[{ts}] {prefix}{msg}\n", tag)
                    self.txt_feed.see(tk.END)
                    self.txt_feed.configure(state="disabled")
                elif task == "status":
                    self.current_status = data
                    self.lbl_overall_status.configure(text=f"SYSTEM: {data}")
                    colors = {"LISTENING": "#00FFCC", "PROCESSING": "#7000FF", "SPEAKING": "#FF007F", "MUTED": "#FF4D4D", "IDLE": "#A0C4FF"}
                    self.lbl_overall_status.configure(foreground=colors.get(data, "#FFF"))
                elif task == "msgbox":
                    messagebox.showinfo(data[0], data[1])
                self.update_queue.task_done()
        except queue.Empty: pass
        self.root.after(100, self.process_queue)

    def voice_listening_loop(self, session_id):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold, recognizer.dynamic_energy_threshold = 400, True
        recognizer.pause_threshold = 0.8
        last_opened_mic, mic_source = None, None
        
        while self.is_active and self.listen_session_id == session_id:
            if self.is_muted:
                self.update_hud_state("MUTED")
                time.sleep(0.4)
                continue
            if self.current_status in ["SPEAKING", "PROCESSING"] or self.is_in_cooldown():
                time.sleep(0.2)
                continue
            
            selected = self.combo_mic.get()
            if selected != last_opened_mic or mic_source is None:
                last_opened_mic = selected
                idx = int(selected.split("] ")[0][1:]) if not selected.startswith("[AUTO]") else None
                for rate in [None, 16000, 44100, 48000]:
                    try:
                        mic_source = sr.Microphone(device_index=idx, sample_rate=rate)
                        with mic_source as source: recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        break
                    except Exception: mic_source = None
                if mic_source is None:
                    time.sleep(4)
                    continue

            try:
                self.update_hud_state("LISTENING")
                with mic_source as source: audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
                if not self.is_active or self.is_muted or self.is_in_cooldown(): continue
                if time.time() - self.last_speech_end_time < 0.4: continue

                self.update_hud_state("PROCESSING")
                text = recognizer.recognize_google(audio).strip()
                
                if self.is_accidental_noise(text): 
                    self.update_hud_state("IDLE")
                    continue
                    
                self.log_to_terminal("user", text)
                self.process_ai_response(text)
                
            except sr.UnknownValueError: 
                self.update_hud_state("IDLE")
                continue 
            except Exception:
                self.update_hud_state("IDLE")
                mic_source = None 
                time.sleep(1)

    def proactive_chatter_loop(self, session_id):
        time.sleep(15)
        while self.is_active and self.chatter_session_id == session_id:
            if not self.chatter_enabled or self.is_in_cooldown():
                time.sleep(2)
                continue
            
            elapsed = 0
            while elapsed < self.chatter_interval:
                if not self.is_active or not self.chatter_enabled or self.is_in_cooldown() or self.chatter_session_id != session_id:
                    break
                time.sleep(1)
                elapsed += 1
                
            if not self.is_active or self.is_muted or not self.chatter_enabled or self.is_in_cooldown() or self.chatter_session_id != session_id:
                continue
                
            if self.current_status == "IDLE":
                self.trigger_spontaneous_comment()

    def trigger_spontaneous_comment(self):
        if self.current_status != "IDLE" or self.is_muted or self.is_in_cooldown(): return
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
        if self.current_status != "IDLE" or self.is_muted or self.is_in_cooldown(): return
        self.update_hud_state("PROCESSING")
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
            if self.handle_api_error_or_quota(str(e)): return
            self.update_hud_state("IDLE")

    def process_ai_response(self, text_input):
        self.update_hud_state("PROCESSING")
        self.prune_chat_history()
        try:
            response = self.chat.send_message(text_input)
            reply = response.text.replace("*", "") 
            self.log_to_terminal("jarvis", reply)
            self.speak_vocal_response(reply)
        except Exception as e:
            err_msg = str(e)
            if self.handle_api_error_or_quota(err_msg): return
            if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                delay = 60.0
                self.cooldown_remaining = delay
                self.cooldown_start_time = time.time()
                self.update_queue.put(("cooldown", delay))
                self.log_to_terminal("error", f"Google API Quota Exceeded. Cooldown active for {delay} seconds.")
                self.speak_vocal_response("My apologies. We have hit the request limit. Please wait.")
            else:
                self.log_to_terminal("error", f"Connection Error: {err_msg}")
            self.update_hud_state("IDLE")

    def speak_vocal_response(self, text):
        self.update_hud_state("SPEAKING")
        self.last_speech_start_time = time.time()
        try:
            safe_coinitialize()
            engine = pyttsx3.init()
            engine.setProperty('rate', self.slide_rate.get())
            for v in engine.getProperty('voices'):
                if v.name == self.combo_voice.get():
                    engine.setProperty('voice', v.id)
                    break
            engine.say(text)
            engine.runAndWait()
            engine.stop() 
        except Exception as e: self.log_to_terminal("error", f"Audio out failed: {e}")
        finally:
            self.last_speech_end_time = time.time()
            self.update_hud_state("MUTED" if self.is_muted else "IDLE")

    def animate_hud(self):
        self.hud_canvas.delete("all")
        cx, cy = 160, 110
        
        self.hud_canvas.create_oval(cx-90, cy-90, cx+90, cy+90, outline="#111D4A", width=1, dash=(2, 4))
        self.hud_canvas.create_oval(cx-60, cy-60, cx+60, cy+60, outline="#111D4A", width=2)
        
        if self.current_status == "LISTENING":
            self.wave_phase += 0.2
            r = 30 + (math.sin(self.wave_phase) * 15)
            self.hud_canvas.create_oval(cx-r-10, cy-r-10, cx+r+10, cy+r+10, outline="#00FFCC", width=2)
            radar = self.wave_phase * 1.5
            self.hud_canvas.create_line(cx, cy, cx + math.cos(radar)*90, cy + math.sin(radar)*90, fill="#00FFCC", width=2)
            self.hud_canvas.create_text(cx, cy-105, text="AWAITING AUDIO INPUT...", fill="#00FFCC", font=("Consolas", 9, "bold"))
            
        elif self.current_status == "PROCESSING":
            self.animation_angle += 12
            for off in [0, 90, 180, 270]:
                self.hud_canvas.create_arc(cx-50, cy-50, cx+50, cy+50, start=(self.animation_angle+off)%360, extent=60, style="arc", outline="#7000FF", width=4)
                self.hud_canvas.create_arc(cx-75, cy-75, cx+75, cy+75, start=(360 - self.animation_angle+off)%360, extent=40, style="arc", outline="#00FFCC", width=2)
            self.hud_canvas.create_text(cx, cy-105, text="NEURAL NETWORK COMPILING", fill="#7000FF", font=("Consolas", 9, "bold"))
            
        elif self.current_status == "SPEAKING":
            self.wave_phase += 0.4
            for i in range(-5, 6):
                h = (math.sin(self.wave_phase + i*0.8) * 35 * (1 - abs(i)/6)) + random.randint(-4,4)
                self.hud_canvas.create_line(cx+(i*12), cy-h, cx+(i*12), cy+h, fill="#FF007F", width=5, capstyle="round")
            self.hud_canvas.create_text(cx, cy-105, text="TRANSMITTING AUDIO", fill="#FF007F", font=("Consolas", 9, "bold"))
            
        elif self.current_status == "MUTED":
            self.hud_canvas.create_oval(cx-40, cy-40, cx+40, cy+40, outline="#FF007F", width=3, dash=(10, 5))
            self.hud_canvas.create_line(cx-25, cy-25, cx+25, cy+25, fill="#FF007F", width=4)
            self.hud_canvas.create_text(cx, cy-105, text="SENSORS OFFLINE", fill="#FF007F", font=("Consolas", 9, "bold"))
            
        else: # IDLE
            self.wave_phase += 0.05
            r = 25 + (math.sin(self.wave_phase) * 4)
            self.hud_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#111D4A", outline="#00FFCC", width=1)
            self.hud_canvas.create_text(cx, cy-105, text="SYSTEM STANDBY", fill="#A0C4FF", font=("Consolas", 9, "bold"))

        self.root.after(30, self.animate_hud)

    def on_closing(self):
        self.is_active = False
        self.root.destroy()

# --- J.A.R.V.I.S. V3.3 SYSTEM TOOLS ---

def read_clipboard():
    """Reads whatever text the user currently has copied to their computer's clipboard."""
    if not ACTIVE_APP: return "UI not linked."
    ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Scanning system clipboard memory.")
    try:
        clip_data = ACTIVE_APP.root.clipboard_get()
        if not clip_data.strip(): return "The clipboard is currently empty."
        return f"Clipboard Contents: {clip_data}"
    except Exception:
        return "Nothing copied to clipboard or it is not a readable text format."

def minimize_all_windows():
    """Minimizes all open applications to show the desktop."""
    if not HAS_PYAUTOGUI: return "Requires pyautogui."
    if ACTIVE_APP: ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Minimizing all visual windows.")
    try:
        pyautogui.hotkey('win', 'd')
        return "All windows minimized. The desktop is now visible."
    except Exception as e: return f"Failed to clear screen: {e}"

def change_system_volume(action: str):
    """Changes volume. Actions: 'mute', 'unmute', 'up', 'down'."""
    if not HAS_PYAUTOGUI: return "Requires pyautogui."
    action = action.lower().strip()
    if ACTIVE_APP: ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Volume ({action})")
    try:
        if action in ["mute", "unmute"]: pyautogui.press("volumemute")
        elif action == "up": [pyautogui.press("volumeup") for _ in range(10)]
        elif action == "down": [pyautogui.press("volumedown") for _ in range(10)]
        return f"Volume {action} complete."
    except Exception as e: return str(e)

def lock_system():
    """Locks the computer screen."""
    if ACTIVE_APP: ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: System Lockdown.")
    os_name = platform.system().lower()
    try:
        if "windows" in os_name:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        elif "darwin" in os_name: subprocess.Popen(["pmset", "displaysleepnow"])
        return "System locked."
    except Exception as e: return str(e)

def type_for_me(text: str):
    """Types text on the keyboard."""
    if not HAS_PYAUTOGUI: return "Requires pyautogui."
    if ACTIVE_APP: ACTIVE_APP.log_to_terminal("system", "⚙️ Tool Invoked: Keyboard Automation.")
    try:
        pyautogui.write(text, interval=0.01)
        return "Text transcribed."
    except Exception as e: return str(e)

def write_new_file(filename: str, content: str):
    """Saves text, code, or essays directly to the computer disk."""
    try:
        safe_name = os.path.basename(filename)
        if os.path.splitext(safe_name)[1].lower() not in {".txt", ".md", ".json", ".py", ".html", ".css", ".js", ".csv", ".cpp", ".cs"}: return "Extension rejected."
        with open(os.path.join(SAFE_DIR, safe_name), "w", encoding="utf-8") as f: f.write(content)
        return f"File '{safe_name}' has been successfully written and saved."
    except Exception as e: return str(e)

def read_my_file(filename: str):
    try:
        p = os.path.join(SAFE_DIR, os.path.basename(filename))
        if not os.path.exists(p): return "File not found."
        with open(p, "r", encoding="utf-8", errors="ignore") as f: return f.read(2500)
    except Exception as e: return str(e)

def capture_and_analyze_screen(focus_question: str = "Comment on what is happening on the screen."):
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.thumbnail((1024, 1024))
        
        safe_prompt = (
            f"Analyze the attached image based on this question: '{focus_question}'.\n"
            "Provide a wholesome, clean, and highly conversational commentary.\n"
            "If they are watching a YouTube video, tell me about it. "
            "If they are looking at notes, code, or a game, comment on it with personality. "
            "Keep your commentary to exactly 1 or 2 spoken sentences. Avoid reading aloud passwords or personal codes."
        )
        
        return genai.GenerativeModel('gemini-2.5-flash').generate_content([safe_prompt, img]).text
    except Exception as e: return str(e)

def play_youtube_video(search_term: str):
    clean_term = re.sub(r'[^a-zA-Z0-9\s-]', '', search_term) + ' safe clean'
    encoded_query = urllib.parse.quote(clean_term)
    webbrowser.open(f"https://www.youtube.com/results?search_query={encoded_query}")
    return f"Searching YouTube for '{search_term}'. Pick your favorite video to watch!"

def open_website(url: str):
    if not url.startswith("http"): url = f"https://{url}"
    webbrowser.open(url)
    return "Browser launched."

def search_web(query: str):
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return "Searching web."

def get_current_time(): return datetime.datetime.now().strftime('%I:%M:%S %p on %A, %B %d, %Y')

def open_calculator():
    try:
        if "windows" in platform.system().lower(): subprocess.Popen("calc.exe")
        elif "darwin" in platform.system().lower(): subprocess.Popen(["open", "-a", "Calculator"])
        return "Calculator opened."
    except Exception: return "Failed to open."

def get_system_info(): return f"OS: {platform.system()}, Architecture: {platform.machine()}."

def open_application(app_name: str):
    """A deeply integrated launcher. Will attempt to use native OS commands to find and boot programs."""
    app_name_lower = app_name.lower().strip()
    os_name = platform.system().lower()
    
    if ACTIVE_APP: ACTIVE_APP.log_to_terminal("system", f"⚙️ Tool Invoked: Requesting OS to launch {app_name_lower}")
    
    try:
        if "windows" in os_name:
            if app_name_lower == "steam":
                os.system("start steam://")
                return "Steam launched successfully via protocol."
            else:
                os.system(f'start {app_name_lower}')
                return f"Sent OS command to open {app_name_lower}."
        elif "darwin" in os_name:
            subprocess.Popen(["open", "-a", app_name], shell=False)
            return f"Sent Mac OS command to open {app_name}."
        return "Application open request processed."
    except Exception as e:
        return f"Failed to open application: {e}"

def list_my_files():
    try:
        if not os.path.exists(SAFE_DIR): return "No directory."
        valid = [f for f in os.listdir(SAFE_DIR) if os.path.splitext(f)[1].lower() in {".txt", ".md", ".json", ".rtf", ".csv", ".py", ".html", ".css", ".js"}]
        return ", ".join(valid) if valid else "No files."
    except Exception: return "Failed."

def detect_running_games():
    games = {"minecraft": "Minecraft", "roblox": "Roblox", "fortnite": "Fortnite", "valorant": "Valorant"}
    running = []
    try:
        out = subprocess.check_output(["tasklist", "/FO", "CSV"], creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore').lower()
        running = [v for k, v in games.items() if k in out]
    except Exception: pass
    return f"Detected running games: {', '.join(running)}. Comment on this in a fun, friendly, and enthusiastic way!" if running else "None."

if __name__ == "__main__":
    root_window = tk.Tk()
    app = JarvisApp(root_window)
    root_window.mainloop()
