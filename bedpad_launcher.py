import io
import secrets
import socket
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    import qrcode
    from PIL import ImageTk
except ImportError:
    qrcode = None
    ImageTk = None


ROOT = Path(__file__).resolve().parent
PORT = 8876


def local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def ensure_qr_deps():
    if qrcode and ImageTk:
        return True
    answer = messagebox.askyesno(
        "Install QR support",
        "BedPad needs the small qrcode package to show a QR code. Install it now?",
    )
    if not answer:
        return False
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "qrcode[pil]>=7.4"],
        cwd=ROOT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        messagebox.showerror("Install failed", "Could not install qrcode[pil].")
        return False
    messagebox.showinfo("Ready", "QR support installed. Please launch BedPad again.")
    return False


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BedPad")
        self.resizable(False, False)
        self.process = None
        self.url = None
        self.qr_image = None

        self.columnconfigure(0, weight=1)
        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="BedPad", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Scan this with your phone on the same Wi-Fi.").grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.qr_label = ttk.Label(frame)
        self.qr_label.grid(row=2, column=0, pady=6)

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(frame, textvariable=self.url_var, width=54)
        url_entry.grid(row=3, column=0, sticky="ew", pady=(8, 8))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, sticky="ew")
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text="Copy URL", command=self.copy_url).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Stop", command=self.stop_and_close).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.protocol("WM_DELETE_WINDOW", self.stop_and_close)
        self.start_server()

    def start_server(self):
        token = secrets.token_urlsafe(9)
        self.url = f"http://{local_ip()}:{PORT}/?token={token}"
        self.url_var.set(self.url)
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / "bedpad.py"), "--port", str(PORT), "--token", token],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.draw_qr()

    def draw_qr(self):
        qr = qrcode.QRCode(border=2, box_size=8)
        qr.add_data(self.url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        self.qr_image = ImageTk.PhotoImage(data=buffer.read())
        self.qr_label.configure(image=self.qr_image)

    def copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)

    def stop_and_close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.destroy()


def main():
    root = tk.Tk()
    root.withdraw()
    ok = ensure_qr_deps()
    root.destroy()
    if ok:
        Launcher().mainloop()


if __name__ == "__main__":
    main()
