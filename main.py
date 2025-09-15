import tkinter as tk
import subprocess
import os

root = tk.Tk()
background_color = "#0d2d61"
root.configure(bg=background_color)
root.title("Welcome")
root.geometry("300x250")
script_dir = os.path.dirname(os.path.abspath(__file__))


reddit_button = tk.Button(
    root,
    text="Reddit",
    command=lambda: subprocess.Popen(["python", os.path.join(script_dir, "reddit.py")])
)
reddit_button.pack(pady=10)

tiktok_button = tk.Button(
    root,
    text="TikTok",
    command=lambda: subprocess.Popen(["python", os.path.join(script_dir, "tiktok.py")])
)
tiktok_button.pack(pady=10)

insta_button = tk.Button(
    root,
    text="Instagram",
    command=lambda: subprocess.Popen(["python", os.path.join(script_dir, "instagram.py")])
)
insta_button.pack(pady=10)

twitter_button = tk.Button(
    root,
    text="X/Twitter",
    command=lambda: subprocess.Popen(["python", os.path.join(script_dir, "twitter.py")])
)
twitter_button.pack(pady=10)

root.mainloop()
