import tkinter as tk
import subprocess

root = tk.Tk()
background_color = "#0d2d61"
root.configure(bg=background_color)
root.title("Welcome")
root.geometry("300x250")

reddit_button = tk.Button(
    root,
    text="Reddit",
    command=lambda: subprocess.Popen(["python", "C:\\Users\\pc\\Desktop\\Practica SRL\\reddit.py"])
)
reddit_button.pack(pady=10)

tiktok_button = tk.Button(
    root,
    text="TikTok",
    command=lambda: subprocess.Popen(["python", "C:\\Users\\pc\\Desktop\\Practica SRL\\tiktok.py"])
)
tiktok_button.pack(pady=10)

insta_button = tk.Button(
    root,
    text="Instagram",
    command=lambda: subprocess.Popen(["python", "C:\\Users\\pc\\Desktop\\Practica SRL\\instagram.py"])
)
insta_button.pack(pady=10)

twitter_button = tk.Button(
    root,
    text="X/Twitter",
    command=lambda: subprocess.Popen(["python", "C:\\Users\\pc\\Desktop\\Practica SRL\\twitter.py"])
)
twitter_button.pack(pady=10)

root.mainloop()
