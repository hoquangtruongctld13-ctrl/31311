#!/usr/bin/env python3
"""
TTS-Grabber GUI
Giao diện đồ họa cho TTS-Grabber với khả năng:
- Nhập văn bản trực tiếp
- Import và xử lý file SRT để tạo voice
- Chọn giọng nói từ danh sách
"""

import functools
import requests
import textwrap
import os
import time
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

# Default API configuration - can be overridden via environment variables
API_URL = os.environ.get("TTS_API_URL", "https://play.ht/api/transcribe")
API_USER_ID = os.environ.get("TTS_USER_ID", "landing_demo_user")
API_PLATFORM = os.environ.get("TTS_PLATFORM", "landing_demo")
REQUEST_TIMEOUT = int(os.environ.get("TTS_REQUEST_TIMEOUT", "60"))


class TTSGrabberGUI:
    """Main GUI class for TTS-Grabber application."""

    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("TTS-Grabber GUI")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        # Data
        self.voices = []
        self.filtered_voices = []
        self.selected_voice = None
        self.lastused_voice = None
        self.is_processing = False

        # Load voices data
        self.load_voices()

        # Create GUI components
        self.create_menu()
        self.create_main_frame()

        # Load last used voice if exists
        self.load_lastused()

    def load_voices(self):
        """Load voice data from data.json file."""
        data_path = os.path.join(os.path.dirname(__file__), 'data.json')
        try:
            with open(data_path, encoding='utf-8') as f:
                self.voices = json.load(f)
            # Sort voices by language + gender + name
            self.voices.sort(key=lambda x: x["language"] + x["gender"] + x["name"])
            self.filtered_voices = self.voices.copy()
        except FileNotFoundError:
            messagebox.showerror("Lỗi", "Không tìm thấy file data.json!")
            self.voices = []
            self.filtered_voices = []

    def load_lastused(self):
        """Load last used voice from lastused.json."""
        lastused_path = os.path.join(os.path.dirname(__file__), 'lastused.json')
        if os.path.isfile(lastused_path):
            try:
                with open(lastused_path, encoding='utf-8') as f:
                    self.lastused_voice = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.lastused_voice = None

    def save_lastused(self, voice):
        """Save last used voice to lastused.json."""
        lastused_path = os.path.join(os.path.dirname(__file__), 'lastused.json')
        try:
            with open(lastused_path, 'w', encoding='utf-8') as f:
                json.dump(voice, f)
            self.lastused_voice = voice
        except IOError:
            pass

    def create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Mở file văn bản...", command=self.open_text_file)
        file_menu.add_command(label="Import SRT...", command=self.import_srt)
        file_menu.add_separator()
        file_menu.add_command(label="Chọn thư mục lưu...", command=self.select_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Hướng dẫn", command=self.show_help)
        help_menu.add_command(label="Giới thiệu", command=self.show_about)
        menubar.add_cascade(label="Trợ giúp", menu=help_menu)

        self.root.config(menu=menubar)

    def create_main_frame(self):
        """Create the main application frame."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Voice selection
        left_panel = ttk.LabelFrame(main_frame, text="Chọn giọng nói", padding="5")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # Search/filter frame
        filter_frame = ttk.Frame(left_panel)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Tìm kiếm:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_voices)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Language filter
        lang_frame = ttk.Frame(left_panel)
        lang_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(lang_frame, text="Ngôn ngữ:").pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="Tất cả")
        languages = ["Tất cả"] + sorted(set(v["language"] for v in self.voices))
        self.lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var,
                                       values=languages, state="readonly", width=18)
        self.lang_combo.pack(side=tk.LEFT, padx=5)
        self.lang_combo.bind("<<ComboboxSelected>>", self.filter_voices)

        # Voice list with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.voice_listbox = tk.Listbox(list_frame, width=35, height=20,
                                         yscrollcommand=scrollbar.set)
        self.voice_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.voice_listbox.yview)

        self.voice_listbox.bind("<<ListboxSelect>>", self.on_voice_select)

        # Populate voice list
        self.update_voice_list()

        # Selected voice info
        info_frame = ttk.LabelFrame(left_panel, text="Thông tin giọng nói", padding="5")
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self.voice_info_label = ttk.Label(info_frame, text="Chưa chọn giọng nói",
                                          wraplength=200)
        self.voice_info_label.pack()

        # Use last voice button
        if self.lastused_voice:
            last_btn = ttk.Button(info_frame, text="Dùng giọng gần nhất",
                                  command=self.use_last_voice)
            last_btn.pack(pady=(5, 0))

        # Right panel - Text input and settings
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Notebook for tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Text input
        text_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(text_tab, text="Nhập văn bản")

        ttk.Label(text_tab, text="Nhập văn bản cần chuyển thành giọng nói:").pack(anchor=tk.W)
        self.text_input = scrolledtext.ScrolledText(text_tab, height=15, wrap=tk.WORD)
        self.text_input.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab 2: SRT import
        srt_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(srt_tab, text="Import SRT")

        srt_btn_frame = ttk.Frame(srt_tab)
        srt_btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(srt_btn_frame, text="Chọn file SRT...",
                   command=self.import_srt).pack(side=tk.LEFT)
        self.srt_path_label = ttk.Label(srt_btn_frame, text="Chưa chọn file")
        self.srt_path_label.pack(side=tk.LEFT, padx=10)

        ttk.Label(srt_tab, text="Nội dung SRT (đã được phân tích):").pack(anchor=tk.W)
        self.srt_preview = scrolledtext.ScrolledText(srt_tab, height=15, wrap=tk.WORD,
                                                      state=tk.DISABLED)
        self.srt_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        # Settings frame
        settings_frame = ttk.LabelFrame(right_panel, text="Cài đặt", padding="5")
        settings_frame.pack(fill=tk.X, pady=5)

        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill=tk.X)

        # Speed setting
        ttk.Label(settings_grid, text="Tốc độ (%):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.speed_var = tk.IntVar(value=100)
        speed_spin = ttk.Spinbox(settings_grid, from_=50, to=200,
                                 textvariable=self.speed_var, width=10)
        speed_spin.grid(row=0, column=1, padx=5, pady=2)

        # Volume setting
        ttk.Label(settings_grid, text="Âm lượng (dB):").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.volume_var = tk.IntVar(value=0)
        volume_spin = ttk.Spinbox(settings_grid, from_=-20, to=20,
                                  textvariable=self.volume_var, width=10)
        volume_spin.grid(row=0, column=3, padx=5, pady=2)

        # Output directory
        output_frame = ttk.Frame(settings_frame)
        output_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(output_frame, text="Thư mục lưu:").pack(side=tk.LEFT)
        self.output_dir = tk.StringVar(value=os.path.dirname(__file__))
        self.output_dir_label = ttk.Label(output_frame, textvariable=self.output_dir,
                                          width=40, anchor=tk.W)
        self.output_dir_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(output_frame, text="Chọn...",
                   command=self.select_output_dir).pack(side=tk.LEFT)

        # Action buttons
        action_frame = ttk.Frame(right_panel)
        action_frame.pack(fill=tk.X, pady=5)

        self.generate_btn = ttk.Button(action_frame, text="🔊 Tạo Voice",
                                        command=self.generate_voice)
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        self.generate_srt_btn = ttk.Button(action_frame, text="🎬 Tạo Voice từ SRT",
                                            command=self.generate_voice_from_srt)
        self.generate_srt_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="Xóa văn bản",
                   command=self.clear_text).pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(right_panel, variable=self.progress_var,
                                            maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Sẵn sàng")
        status_label = ttk.Label(right_panel, textvariable=self.status_var,
                                 relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X)

    def update_voice_list(self):
        """Update the voice listbox with filtered voices."""
        self.voice_listbox.delete(0, tk.END)
        for i, voice in enumerate(self.filtered_voices):
            display_text = f"{i+1}. [{voice['language']}] {voice['name']} ({voice['gender']})"
            self.voice_listbox.insert(tk.END, display_text)

    def filter_voices(self, *args):
        """Filter voices based on search text and language selection."""
        search_text = self.search_var.get().lower()
        selected_lang = self.lang_var.get()

        self.filtered_voices = []
        for voice in self.voices:
            # Check language filter
            if selected_lang != "Tất cả" and voice["language"] != selected_lang:
                continue

            # Check search text
            if search_text:
                searchable = (voice["language"] + voice["name"] +
                              voice["gender"]).lower()
                if search_text not in searchable:
                    continue

            self.filtered_voices.append(voice)

        self.update_voice_list()

    def on_voice_select(self, event):
        """Handle voice selection from listbox."""
        selection = self.voice_listbox.curselection()
        if selection:
            idx = selection[0]
            self.selected_voice = self.filtered_voices[idx]
            info_text = (f"Tên: {self.selected_voice['name']}\n"
                        f"Ngôn ngữ: {self.selected_voice['language']}\n"
                        f"Giới tính: {self.selected_voice['gender']}\n"
                        f"Loại: {self.selected_voice.get('voiceType', 'Standard')}")
            self.voice_info_label.config(text=info_text)

    def use_last_voice(self):
        """Use the last used voice."""
        if self.lastused_voice:
            self.selected_voice = self.lastused_voice
            info_text = (f"Tên: {self.selected_voice['name']}\n"
                        f"Ngôn ngữ: {self.selected_voice['language']}\n"
                        f"Giới tính: {self.selected_voice['gender']}\n"
                        f"Loại: {self.selected_voice.get('voiceType', 'Standard')}")
            self.voice_info_label.config(text=info_text)
            messagebox.showinfo("Thông báo", "Đã chọn giọng nói gần nhất!")

    def open_text_file(self):
        """Open a text file and load its content."""
        filepath = filedialog.askopenfilename(
            title="Chọn file văn bản",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_input.delete(1.0, tk.END)
                self.text_input.insert(tk.END, content)
                self.notebook.select(0)  # Switch to text tab
                self.status_var.set(f"Đã mở file: {os.path.basename(filepath)}")
            except IOError as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

    def import_srt(self):
        """Import and parse an SRT file."""
        filepath = filedialog.askopenfilename(
            title="Chọn file SRT",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        if filepath:
            try:
                srt_content = self.parse_srt(filepath)
                self.srt_path_label.config(text=os.path.basename(filepath))

                # Enable preview and update content
                self.srt_preview.config(state=tk.NORMAL)
                self.srt_preview.delete(1.0, tk.END)

                # Store parsed segments for later use
                self.srt_segments = srt_content

                # Display preview
                for segment in srt_content:
                    self.srt_preview.insert(tk.END,
                        f"[{segment['index']}] {segment['start']} --> {segment['end']}\n"
                        f"{segment['text']}\n\n")

                self.srt_preview.config(state=tk.DISABLED)
                self.notebook.select(1)  # Switch to SRT tab
                self.status_var.set(f"Đã import SRT: {len(srt_content)} đoạn")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file SRT: {e}")

    def parse_srt(self, filepath):
        """Parse an SRT file and return list of segments."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # SRT pattern: index, timestamp, text
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\n|\Z)'

        segments = []
        for match in re.finditer(pattern, content):
            segments.append({
                'index': int(match.group(1)),
                'start': match.group(2),
                'end': match.group(3),
                'text': match.group(4).strip()
            })

        return segments

    def select_output_dir(self):
        """Select output directory for generated audio files."""
        directory = filedialog.askdirectory(title="Chọn thư mục lưu file")
        if directory:
            self.output_dir.set(directory)

    def clear_text(self):
        """Clear the text input."""
        self.text_input.delete(1.0, tk.END)

    def generate_voice(self):
        """Generate voice from text input."""
        if self.is_processing:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi...")
            return

        text = self.text_input.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập văn bản!")
            return

        if not self.selected_voice:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn giọng nói!")
            return

        # Start generation in a separate thread
        thread = threading.Thread(target=self._generate_voice_thread, args=(text,))
        thread.daemon = True
        thread.start()

    def _generate_voice_thread(self, text):
        """Thread function for generating voice."""
        self.is_processing = True
        self._update_ui_state(False)

        try:
            # Split text into chunks
            chunks = textwrap.wrap(text, 1500)
            total_chunks = len(chunks)

            self.save_lastused(self.selected_voice)

            for i, chunk in enumerate(chunks):
                self._update_status(f"Đang xử lý đoạn {i+1}/{total_chunks}...")
                self._update_progress((i / total_chunks) * 100)

                input_text = f"<speak><p>{chunk}</p></speak>"
                params = {
                    "globalSpeed": f"{self.speed_var.get()}%",
                    "globalVolume": f"{'+' if self.volume_var.get() >= 0 else ''}{self.volume_var.get()}dB",
                    "chunk": input_text,
                    "narrationStyle": "regular",
                    "platform": API_PLATFORM,
                    "ssml": input_text,
                    "userId": API_USER_ID,
                    "voice": self.selected_voice["value"]
                }

                req = requests.post(API_URL, data=params, timeout=REQUEST_TIMEOUT)

                filename = f"_{self.selected_voice['name']}-{int(time.time_ns() / 1000)}-{i+1}.mp3"
                filepath = os.path.join(self.output_dir.get(), filename)

                try:
                    response = json.loads(req.text)
                    audio_content = requests.get(response["file"], timeout=REQUEST_TIMEOUT).content
                except (json.JSONDecodeError, KeyError):
                    # Assume we got an audio file directly
                    audio_content = req.content

                with open(filepath, "wb") as f:
                    f.write(audio_content)

                self._update_status(f"Đã lưu: {filename}")

            self._update_progress(100)
            self._update_status("Hoàn thành!")
            self.root.after(0, lambda: messagebox.showinfo("Thành công",
                f"Đã tạo {total_chunks} file audio!"))

        except requests.exceptions.Timeout as e:
            self._update_status("Lỗi: Hết thời gian chờ kết nối")
            self.root.after(0, lambda: messagebox.showerror("Lỗi",
                f"Hết thời gian chờ kết nối (timeout {REQUEST_TIMEOUT}s).\n"
                "Vui lòng kiểm tra kết nối mạng và thử lại."))
        except requests.exceptions.RequestException as e:
            self._update_status(f"Lỗi kết nối: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi kết nối: {e}"))
        except IOError as e:
            self._update_status(f"Lỗi ghi file: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi ghi file: {e}"))
        finally:
            self.is_processing = False
            self._update_ui_state(True)

    def generate_voice_from_srt(self):
        """Generate voice from SRT segments."""
        if self.is_processing:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi...")
            return

        if not hasattr(self, 'srt_segments') or not self.srt_segments:
            messagebox.showwarning("Cảnh báo", "Vui lòng import file SRT trước!")
            return

        if not self.selected_voice:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn giọng nói!")
            return

        # Start generation in a separate thread
        thread = threading.Thread(target=self._generate_srt_voice_thread)
        thread.daemon = True
        thread.start()

    def _generate_srt_voice_thread(self):
        """Thread function for generating voice from SRT."""
        self.is_processing = True
        self._update_ui_state(False)

        try:
            total_segments = len(self.srt_segments)
            self.save_lastused(self.selected_voice)

            for i, segment in enumerate(self.srt_segments):
                self._update_status(f"Đang xử lý đoạn {i+1}/{total_segments}...")
                self._update_progress((i / total_segments) * 100)

                text = segment['text']
                if not text.strip():
                    continue

                input_text = f"<speak><p>{text}</p></speak>"
                params = {
                    "globalSpeed": f"{self.speed_var.get()}%",
                    "globalVolume": f"{'+' if self.volume_var.get() >= 0 else ''}{self.volume_var.get()}dB",
                    "chunk": input_text,
                    "narrationStyle": "regular",
                    "platform": API_PLATFORM,
                    "ssml": input_text,
                    "userId": API_USER_ID,
                    "voice": self.selected_voice["value"]
                }

                req = requests.post(API_URL, data=params, timeout=REQUEST_TIMEOUT)

                # Use segment index in filename for ordering
                filename = f"srt_{segment['index']:04d}_{self.selected_voice['name']}.mp3"
                filepath = os.path.join(self.output_dir.get(), filename)

                try:
                    response = json.loads(req.text)
                    audio_content = requests.get(response["file"], timeout=REQUEST_TIMEOUT).content
                except (json.JSONDecodeError, KeyError):
                    # Assume we got an audio file directly
                    audio_content = req.content

                with open(filepath, "wb") as f:
                    f.write(audio_content)

                self._update_status(f"Đã lưu: {filename}")

            self._update_progress(100)
            self._update_status("Hoàn thành!")
            self.root.after(0, lambda: messagebox.showinfo("Thành công",
                f"Đã tạo {total_segments} file audio từ SRT!"))

        except requests.exceptions.Timeout as e:
            self._update_status("Lỗi: Hết thời gian chờ kết nối")
            self.root.after(0, lambda: messagebox.showerror("Lỗi",
                f"Hết thời gian chờ kết nối (timeout {REQUEST_TIMEOUT}s).\n"
                "Vui lòng kiểm tra kết nối mạng và thử lại."))
        except requests.exceptions.RequestException as e:
            self._update_status(f"Lỗi kết nối: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi kết nối: {e}"))
        except IOError as e:
            self._update_status(f"Lỗi ghi file: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi ghi file: {e}"))
        finally:
            self.is_processing = False
            self._update_ui_state(True)

    def _update_status(self, message):
        """Update status bar text (thread-safe)."""
        self.root.after(0, lambda: self.status_var.set(message))

    def _update_progress(self, value):
        """Update progress bar value (thread-safe)."""
        self.root.after(0, lambda: self.progress_var.set(value))

    def _update_ui_state(self, enabled):
        """Enable/disable UI elements during processing."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.root.after(0, lambda: self.generate_btn.config(state=state))
        self.root.after(0, lambda: self.generate_srt_btn.config(state=state))

    def show_help(self):
        """Show help dialog."""
        help_text = """TTS-Grabber GUI - Hướng dẫn sử dụng

1. Chọn giọng nói:
   - Tìm kiếm theo tên hoặc ngôn ngữ
   - Click vào giọng nói trong danh sách để chọn

2. Nhập văn bản:
   - Tab "Nhập văn bản": Gõ trực tiếp hoặc mở file .txt
   - Tab "Import SRT": Chọn file .srt để tạo voice cho phụ đề

3. Cài đặt:
   - Tốc độ: 50-200% (mặc định 100%)
   - Âm lượng: -20 đến +20 dB (mặc định 0)

4. Tạo voice:
   - "Tạo Voice": Chuyển văn bản thành audio
   - "Tạo Voice từ SRT": Tạo file audio riêng cho mỗi đoạn SRT

File audio sẽ được lưu trong thư mục đã chọn."""

        messagebox.showinfo("Hướng dẫn", help_text)

    def show_about(self):
        """Show about dialog."""
        about_text = """TTS-Grabber GUI
Version 1.0

Ứng dụng chuyển văn bản thành giọng nói
với giao diện đồ họa.

Dựa trên TTS-Grabber
(https://github.com/BleachDev/TTS-Grabber)"""

        messagebox.showinfo("Giới thiệu", about_text)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = TTSGrabberGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
