import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
import sys
from decimal import Decimal
from pydub import AudioSegment

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(__file__)

ffmpeg_path = os.path.abspath(os.path.join(base_path, "ffmpeg.exe"))

if not os.path.exists(ffmpeg_path):
    messagebox.showerror("FFmpeg Missing", f"ffmpeg.exe not found in:\n{ffmpeg_path}")
else:
    AudioSegment.converter = ffmpeg_path

class KSHAudioSpeedEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("KSH + Audio Speed Editor")
        self.ksh_filename = None
        self.audio_filename = None
        self.original_lines = []
        self.lines = []
        self.original_t = 100.0
        self.step_count = 0
        self.audio_step_count = 0
        self.audio_format = None
        self.audio_only_mode = False
        self.preserve_pitch = tk.BooleanVar(value=True)

        self.label = tk.Label(root, text="Load a .ksh or audio file to begin", font=("Arial", 14))
        self.label.pack(pady=10)

        self.ksh_display = tk.Label(root, text="Original t: N/A | Current t: N/A", font=("Arial", 12))
        self.ksh_display.pack()

        self.load_ksh_button = tk.Button(root, text="Load .ksh File", command=self.load_ksh_file)
        self.load_ksh_button.pack(pady=5)

        self.load_audio_button = tk.Button(root, text="(Optional) Load Audio File (.ogg or .mp3)", command=self.load_audio_file)
        self.load_audio_button.pack(pady=5)

        self.pitch_checkbox = tk.Checkbutton(root, text="Preserve Pitch (No Shift)", variable=self.preserve_pitch)
        self.pitch_checkbox.pack(pady=5)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=5)

        self.increase_button = tk.Button(self.button_frame, text="Increase (+5%)", command=lambda: self.adjust_t(1), state=tk.DISABLED)
        self.increase_button.grid(row=0, column=0, padx=5)

        self.decrease_button = tk.Button(self.button_frame, text="Decrease (-5%)", command=lambda: self.adjust_t(-1), state=tk.DISABLED)
        self.decrease_button.grid(row=0, column=1, padx=5)

        self.reset_button = tk.Button(self.button_frame, text="Reset t", command=self.reset_t, state=tk.DISABLED)
        self.reset_button.grid(row=0, column=2, padx=5)

        self.save_button = tk.Button(root, text="Save Updated Files", command=self.save_all, state=tk.DISABLED)
        self.save_button.pack(pady=10)

    def load_ksh_file(self):
        self.ksh_filename = filedialog.askopenfilename(filetypes=[("KSH Files", "*.ksh")])
        if not self.ksh_filename:
            return
        with open(self.ksh_filename, 'r', encoding='utf-8') as file:
            self.original_lines = file.readlines()
        self.lines = self.original_lines.copy()

        self.extract_t()
        self.audio_only_mode = False
        self.update_display()
        self.enable_controls()
        self.label.config(text=f"Editing: {os.path.basename(self.ksh_filename)}")

    def load_audio_file(self):
        self.audio_filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.ogg *.mp3")])
        if not self.audio_filename:
            return

        ext = os.path.splitext(self.audio_filename)[1].lower()
        if ext == ".ogg":
            self.audio_format = "ogg"
        elif ext == ".mp3":
            self.audio_format = "mp3"
        else:
            messagebox.showerror("Unsupported Format", "Only .ogg and .mp3 files are supported.")
            return

        self.audio_only_mode = self.ksh_filename is None
        self.original_t = 100.0
        self.audio_step_count = 0
        self.step_count = 0
        self.update_display()
        self.enable_controls()
        self.label.config(text=f"Editing Audio: {os.path.basename(self.audio_filename)}")
        messagebox.showinfo("Loaded", f"Loaded audio file: {os.path.basename(self.audio_filename)}")

    def extract_t(self):
        for line in self.original_lines:
            match = re.match(r'^t=(\d+\.?\d*)$', line.strip())
            if match:
                self.original_t = float(match.group(1))
                self.step_count = 0
                return
        self.original_t = 100.0
        self.step_count = 0

    def adjust_t(self, step_delta):
        if self.audio_only_mode:
            self.audio_step_count += step_delta
        else:
            self.step_count += step_delta
            self.replace_all_t()
        self.update_display()

    def reset_t(self):
        self.step_count = 0
        self.audio_step_count = 0
        if not self.audio_only_mode:
            self.replace_all_t()
        self.update_display()

    def replace_all_t(self):
        if not self.ksh_filename:
            return

        multiplier = Decimal("1.00") + (Decimal("0.05") * self.step_count)

        range_pattern = re.compile(r'^t=(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$')
        t_pattern = re.compile(r'^t=(\d+(?:\.\d+)?)$')

        def format_scaled(original, multiplier):
            original_decimal = Decimal(original)
            scaled = original_decimal * multiplier
            decimals = len(original.split(".")[1]) if "." in original else 0
            return str(scaled.quantize(Decimal('1.' + '0' * decimals)))

        def replace_ranges(match):
            first = format_scaled(match.group(1), multiplier)
            second = format_scaled(match.group(2), multiplier)
            return f"t={first}-{second}"

        def replace_single(match):
            return f"t={format_scaled(match.group(1), multiplier)}"

        new_lines = []
        for line in self.original_lines:
            stripped = line.strip()
            if range_pattern.match(stripped):
                line = range_pattern.sub(replace_ranges, stripped) + '\n'
            elif t_pattern.match(stripped):
                line = t_pattern.sub(replace_single, stripped) + '\n'
            new_lines.append(line)

        self.lines = new_lines

    def update_display(self):
        multiplier = Decimal("1.00") + (Decimal("0.05") * (self.audio_step_count if self.audio_only_mode else self.step_count))
        new_t = self.original_t * float(multiplier)
        self.ksh_display.config(text=f"Original t: {self.original_t:.3f} | Current t: {new_t:.3f} | Multiplier: {multiplier:.4f}")

    def enable_controls(self):
        self.increase_button.config(state=tk.NORMAL)
        self.decrease_button.config(state=tk.NORMAL)
        self.reset_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)

    def save_all(self):
        if self.ksh_filename:
            ksh_save_path = filedialog.asksaveasfilename(defaultextension=".ksh", filetypes=[("KSH Files", "*.ksh")])
            if not ksh_save_path:
                return
            with open(ksh_save_path, 'w', encoding='utf-8') as file:
                file.writelines(self.lines)
        else:
            ksh_save_path = None

        if self.audio_filename and self.audio_format:
            try:
                sound = AudioSegment.from_file(self.audio_filename, format=self.audio_format)
                speed_ratio = float(Decimal("1.00") + Decimal("0.05") * self.audio_step_count)

                if self.preserve_pitch.get():
                    if 0.5 <= speed_ratio <= 2.0:
                        import subprocess
                        temp_input = "__temp_input.wav"
                        temp_output = "__temp_output.wav"
                        sound.export(temp_input, format="wav")
                        subprocess.run([ffmpeg_path, "-y", "-i", temp_input, "-filter:a",
                                        f"atempo={speed_ratio:.4f}", temp_output], check=True)
                        sound = AudioSegment.from_wav(temp_output)
                        os.remove(temp_input)
                        os.remove(temp_output)
                    else:
                        raise ValueError("Pitch-preserving tempo adjustment only works between 0.5x and 2.0x")
                else:
                    new_frame_rate = int(sound.frame_rate * speed_ratio)
                    sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_frame_rate})
                    sound = sound.set_frame_rate(44100)

                if ksh_save_path:
                    audio_save_path = os.path.splitext(ksh_save_path)[0] + f"_adjusted.{self.audio_format}"
                else:
                    audio_save_path = filedialog.asksaveasfilename(defaultextension=f".{self.audio_format}",
                                                                   filetypes=[(f"{self.audio_format.upper()} Files", f"*.{self.audio_format}")])
                    if not audio_save_path:
                        return

                sound.export(audio_save_path, format=self.audio_format)
                messagebox.showinfo("Success", f"Audio saved: {audio_save_path}")
            except Exception as e:
                messagebox.showerror("Audio Error", f"Failed to adjust audio:\n\n{e}")
        elif not self.ksh_filename:
            messagebox.showinfo("Nothing to Save", "No audio or KSH file loaded.")

if __name__ == "__main__":
    root = tk.Tk()
    app = KSHAudioSpeedEditor(root)
    root.mainloop()
