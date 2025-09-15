import tkinter as tk
import threading
from tkinter import messagebox
import pickle
import os
import webbrowser
import subprocess
import time
import datetime
import json
from playwright.sync_api import sync_playwright
from tkinter import ttk, scrolledtext, font
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

COOKIE_FILE = "tiktok_cookies.pkl"
process = None  
link_map = {}

def save_cookies(driver, path=COOKIE_FILE):
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("[*] Cookies saved.")

def load_cookies(driver, path=COOKIE_FILE):
    if not os.path.exists(path):
        print("[!] Cookie file not found.")
        return False

    driver.get("https://www.tiktok.com/")
    with open(path, "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)
    driver.refresh()
    print("[*] Cookies loaded.")
    return True

# Opens links when clicked on
def open_link(event):
    index = output_box.index("@%s,%s" % (event.x, event.y))
    for tag in output_box.tag_names(index):
        if tag in link_map:
            webbrowser.open(link_map[tag])
            return

def insert_clickable_link(url, display_text=None):
    tag_name = f"link_{len(link_map)}"
    link_map[tag_name] = url
    if display_text is None:
        display_text = url
    output_box.insert(tk.END, display_text, (tag_name))
    output_box.tag_configure(tag_name, foreground="#00b3ff", underline=True)
    output_box.tag_bind(tag_name, "<Button-1>", open_link)

# ---- Insert with highlight (supports multiple keywords) ----
def insert_with_highlight(text, keywords):
    """Insert text into output_box, highlighting all occurrences of each keyword."""
    if not keywords:
        output_box.insert(tk.END, text)
        return

    i = 0
    while i < len(text):
        match_pos = None
        match_kw = None
        lower_text = text[i:].lower()
        for kw in keywords:
            pos = lower_text.find(kw)
            if pos != -1:
                abs_pos = i + pos
                if match_pos is None or abs_pos < match_pos:
                    match_pos = abs_pos
                    match_kw = kw
        if match_pos is None:
            output_box.insert(tk.END, text[i:])
            break
        else:
            output_box.insert(tk.END, text[i:match_pos])
            output_box.insert(tk.END, text[match_pos:match_pos+len(match_kw)], "highlight")
            i = match_pos + len(match_kw)

def time_created(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.UTC).strftime("%d-%m-%Y %H:%M:%S")

def scrape_tags():
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    hashtags_input = input_entry.get().strip()
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]
    
    if not hashtags_input:
        output_box.insert(tk.END, "⚠️ Câmpul țintă este gol. ⚠️.", "error_text")
        return

    hashtags = [tag.strip() for tag in hashtags_input.replace(',', ' ').split() if tag]
    if not hashtags:
        output_box.insert(tk.END, "⚠️ Hashtag(uri) invalid. ⚠️", "error_text")
        return

    output_box.insert("end", f"✅ Căutare după hashtag(-uri): {', '.join(hashtags)}\n", "big_bold")
    
    options = webdriver.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    if not load_cookies(driver):
        driver.get("https://www.tiktok.com/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați OK.\n", "white_text")
        messagebox.showinfo("Autentificare", "✅ După ce te-ai logat, apasă OK aici")
        save_cookies(driver)
        driver.quit()
        return

    
    data = []

    for hashtag in hashtags:
        hashtag = hashtag.strip()
        if hashtag:
            print(f"[*] Visiting TikTok hashtag: {hashtag}")
        driver.get(f"https://www.tiktok.com/tag/{hashtag}")
        time.sleep(8)

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        output_box.insert("end", f"TikTok-uri cu #{hashtag}:\n", ["green_text", "big_bold"])

        video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        links, captions = [], []

        for video in video_elements:
            href = video.get_attribute("href")
            if href and href not in links:
                links.append(href)
                try:
                    img = video.find_element(By.CSS_SELECTOR, "img")
                    alt = img.get_attribute("alt") or ""
                except:
                    alt = ""
                captions.append(alt)

        has_word_videos, no_word_videos = [], []
        for idx, link in enumerate(links):
            caption = captions[idx] if idx < len(captions) else ""
            if keywords and any(kw in caption.lower() for kw in keywords):
                has_word_videos.append((caption, link))
            else:
                no_word_videos.append((caption, link))

        if not keywords:
            all_videos = has_word_videos + no_word_videos
            count = 1
            for caption, link in all_videos:
                output_box.insert(tk.END, f"{count}) {caption}\n")
                insert_clickable_link(link, f"{link}\n")
                output_box.insert(tk.END, "\n")
                data.append({
                    "counter": count,
                    "caption": caption,
                    "link": link,
                    "tags": hashtags
                })
                count += 1
        else:
            if has_word_videos:
                output_box.insert(tk.END, f"\n=== VIDEOCLIPURI CU CUVINTELE CHEIE \"{', '.join(keywords)}\" ===\n", "big_bold")
                count = 1
                for caption, link in has_word_videos:
                    insert_with_highlight(f"{count}) {caption}\n", keywords)
                    insert_clickable_link(link, f"{link}\n")
                    output_box.insert(tk.END, "\n")
                    data.append({
                        "counter": count,
                        "caption": caption,
                        "tags": hashtags,
                        "link": link,
                        "keywords": keywords
                    })
                    count += 1

            prev_count = len(data)
            if no_word_videos:
                output_box.insert(tk.END, f"\n=== VIDEOCLIPURI FĂRĂ CUVINTELE CHEIE \"{', '.join(keywords)}\" ===\n", "big_bold")
                count = 1
                for caption, link in no_word_videos:
                    output_box.insert(tk.END, f"{count}) {caption}\n")
                    insert_clickable_link(link, f"{link}\n")
                    output_box.insert(tk.END, "\n")
                    data.append({
                        "counter": count + prev_count,
                        "caption": caption,
                        "tags": hashtags,
                        "link": link
                    })
                    count += 1

    export_to_json(data, mode="tags", argument="_".join(hashtags))
    driver.quit()
    t2 = time.time()
    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")
    status_var.set("Status: Căutare finalizată.")
    root.update_idletasks()  # refresh the UI




def scrape_user():
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    user = input_entry.get().strip()
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    if not user:
        output_box.insert(tk.END, "⚠️ Câmpul țintă este gol. ⚠️\n", "error_text")
        return

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Load cookies if available
    if os.path.exists(COOKIE_FILE):
        load_cookies(driver)
    else:
        driver.get("https://www.tiktok.com/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați OK.\n", "white_text")
        messagebox.showinfo("Autentificare", "✅ După ce te-ai logat, apasă OK aici")
        save_cookies(driver)
        driver.quit()
        return

    is_live = False
    try:
        url = f"https://www.tiktok.com/@{user}?tab=videos"
        driver.get(url)
        driver.implicitly_wait(7)

        try:
            driver.find_element(By.CSS_SELECTOR, '[data-e2e="user-title"]')
            output_box.insert(tk.END, "✅ Utilizatorul ", "green_text")
            insert_clickable_link(url, user)
            output_box.insert(tk.END, " există!\n\n", "green_text")
        except NoSuchElementException:
            try:
                driver.find_element(By.XPATH, "//*[contains(text(), \"Couldn't find this account\")]")
                output_box.insert(tk.END, f"❌ Utilizatorul \"{user}\" NU există.\n", "error_text")
                driver.quit()
                return
            except NoSuchElementException:
                output_box.insert(tk.END, f"❌ Nu am găsit profilul \"{user}\".\n", "error_text")
                driver.quit()
                return
        try:
            driver.find_element(By.XPATH, "//span[text()='LIVE']")
            is_live = True
            output_box.insert(tk.END, "🔴 ")
            output_box.insert(tk.END, "Utilizatorul este LIVE acum!\n", "green_text")
            output_box.insert(tk.END, "Link: ")
            insert_clickable_link(f"https://www.tiktok.com/@{user}/live", f"https://www.tiktok.com/@{user}/live\n")
            output_box.insert(tk.END, "🎥 Se înregistrează. . .\n\n")
        except NoSuchElementException:
            output_box.insert(tk.END, "Utilizatorul nu este live.\n")

        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        

        video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')

        links, captions = [], []
        for idx, video in enumerate(video_elements):
            if is_live and idx == 0:
                continue
            href = video.get_attribute("href")
            if not href or "/live" in href:
                continue
            if href and href not in links:
                links.append(href)
                try:
                    img = video.find_element(By.CSS_SELECTOR, "img")
                    alt = img.get_attribute("alt") or ""
                except:
                    alt = ""
                captions.append(alt)

        has_word_videos, no_word_videos = [], []
        for i, link in enumerate(links):
            caption = captions[i] if i < len(captions) else ""
            if keywords and any(kw in caption.lower() for kw in keywords):
                has_word_videos.append((caption, link))
            else:
                no_word_videos.append((caption, link))
        
                
        data = []
        if not keywords:
            all_videos = has_word_videos + no_word_videos
            count = 1
            for caption, link in all_videos:
                output_box.insert(tk.END, f"{count}) ")
                if caption:
                    output_box.insert(tk.END, caption + "\n", "white_text")
                insert_clickable_link(link, f"{link}\n")
                output_box.insert(tk.END, "\n")
                data.append({
                    "counter": count,
                    "caption": caption,
                    "link": link,
                })
                count += 1
        else:
            # Print HAS_WORD videos first
            if has_word_videos:
                output_box.insert(tk.END, f"\n=== VIDEOCLIPURI CU CUVINTELE CHEIE \"{', '.join(keywords)}\" ===\n", "big_bold")
                count = 1
                for caption, link in has_word_videos:
                    output_box.insert(tk.END, f"{count}) ")
                    insert_with_highlight(caption + "\n", keywords)
                    insert_clickable_link(link, f"{link}\n")
                    output_box.insert(tk.END, "\n")
                    data.append({
                        "counter": count,
                        "caption": caption,
                        "link": link,
                        "keywords": keywords,
                    })
                    count += 1

            # Then NO_WORD videos
            prev_count = len(data) - 1
            if no_word_videos:
                output_box.insert(tk.END, f"\n=== VIDEOCLIPURI FĂRĂ CUVINTELE CHEIE \"{', '.join(keywords)}\" ===\n", "big_bold")
                count = 1
                
                for caption, link in no_word_videos:
                    output_box.insert(tk.END, f"{count}) ")
                    if caption:
                        output_box.insert(tk.END, caption + "\n", "white_text")
                    insert_clickable_link(link, f"{link}\n")
                    output_box.insert(tk.END, "\n")
                    data.append({
                        "counter": count + prev_count, # "+ prev_count" to keep continuity in JSON file
                        "caption": caption,
                        "link": link,
                    })
                    count += 1
        export_to_json(data, mode="user", argument=user)
        
        if is_live:
            def stop_recording(OUTPUT_FILE=f"{user}_live_{datetime.date.today()}.mp4"):
                global process
                if process:
                    print("[*] Stopping recording...")
                    process.stdin.write(b"q\n")   # send q
                    process.stdin.flush()
                    process.wait()
                    process = None
                    print("[+] File saved as", os.path.abspath(OUTPUT_FILE))

            def record_stream(user):
                global process
                OUTPUT_FILE = f"{user}_live_{datetime.date.today()}.mp4"
                PAGE_URL = f"https://www.tiktok.com/@{user}/live"
                with open(COOKIE_FILE, "rb") as f: 
                    cookies = pickle.load(f) 
                    
                time.sleep(5)
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context( 
                        user_data_dir=r"C:\\tiktok_profile",
                        channel="chrome", 
                        headless=False 
                    )
                    with open(COOKIE_FILE, "rb") as f: 
                        cookies = pickle.load(f) 
                        for c in cookies: 
                            c.pop("expiry", None) 
                        context.add_cookies(cookies) 
                        page = context.new_page() 
                        print("[*] Opening live page...") 
                        page.goto(PAGE_URL)
                        page.set_viewport_size({"width": 1920, "height": 1080})
                    
                    command = [
                        "ffmpeg",
                        "-y",
                        "-f", "gdigrab",
                        "-framerate", "30",
                        "-i", "desktop",
                        "-f", "dshow",
                        "-i", "audio=Microphone Array (AMD Audio Device)",  
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",             # encode audio
                        "-b:a", "192k",
                        OUTPUT_FILE
                    ]

                    print(f"[+] Starting screen recording for {user} livestream...")
                    process = subprocess.Popen(command, stdin=subprocess.PIPE)
                    time.sleep(15) # record 15 seconds
                    stop_recording()
                    page.close()
                    context.close()
                    output_box.insert(tk.END, f"✅ Live-ul a fost înregistrat și salvat ca \"{OUTPUT_FILE}\"\n", "green_text")
                    status_var.set("Status: Căutare finalizată și live înregistrat.")

            # Threaded start
            threading.Thread(target=record_stream, args=(user,), daemon=True).start()
            status_var.set("Status: Înregistrare live în curs...")
            

    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare: {e}\n", "error_text")
    finally:
        driver.quit()

    t2 = time.time()
    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")
    status_var.set("Status: Căutare finalizată.")
    root.update_idletasks()  # refresh the UI


def run_scraper():
    mode = mode_var.get()
    status_var.set("Status: Căutare în curs...")
    root.update_idletasks()  # refresh the UI
    if mode == "USER":
        scrape_user()
    else:
        scrape_tags()

# ---- Interface ----
background_color = "#0d2d61"
root = tk.Tk()
root.state('zoomed')
root.title("TikTok Scraper")
root.configure(bg=background_color)

def update_input_label(event=None):
    mode = mode_var.get()
    input_entry.delete(0, tk.END)
    output_box.delete('1.0', tk.END)
    if mode == "USER":
        input_label.config(text="Introduceți USERNAME țintă:")
    else:
        input_label.config(text="Introduceți TAG-uri țintă:")
        run_button.pack(pady=10)
        output_box.pack(padx=10, pady=10)

mode_var = tk.StringVar(value="USER")
mode_label = tk.Label(root, text="Căutare după:")
mode_label.pack(pady=5)
mode_dropdown = ttk.Combobox(root, textvariable=mode_var, values=["USER", "TAGS"], state="readonly")
mode_dropdown.pack(pady=5)
mode_dropdown.bind("<<ComboboxSelected>>", update_input_label)

input_label = tk.Label(root, text="Introduceți USERNAME țintă:")
input_label.pack(pady=5)
input_entry = tk.Entry(root, width=40)
input_entry.pack(pady=5)
input_entry.bind("<Return>", lambda e: run_scraper())

keyword_label = tk.Label(root, text="Cuvinte cheie (separate prin spațiu sau virgulă):")
keyword_label.pack(pady=5)
keyword_entry = tk.Entry(root, width=40)
keyword_entry.pack(pady=5)
keyword_entry.bind("<Return>", lambda e: run_scraper())

run_button = tk.Button(root, text="Caută", command=run_scraper)
run_button.pack(pady=10)

status_var = tk.StringVar(value="Status: Așteptare")
status_label = tk.Label(root, textvariable=status_var, bg=background_color, fg="white", anchor="w")
status_label.pack(anchor="w", padx=10, pady=0)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=200, height=50, font=("Consolas", 14), bg = "#081d40", fg="white")
output_box.pack(padx=10, pady=10)

# ---- Tags ----
output_box.tag_configure("highlight", background="#abab61")
output_box.tag_configure("green_text", foreground="#1fff2a")
output_box.tag_configure("error_text", foreground="red", font=("Consolas", 11, "bold"))
output_box.tag_configure("big_bold", font=("Consolas", 14, "bold"))
output_box.tag_configure("white_text", foreground="white")

# ---- Design ----
mode_label.configure(bg=background_color, fg="white")
input_label.configure(bg=background_color, fg="white")
keyword_label.configure(bg=background_color, fg="white")

run_button = tk.Button(root, text="Caută", command=run_scraper)
run_button.pack(pady=10)
output_box.pack(padx=10, pady=10)


# ---- JSON Export ----
def export_to_json(data, mode, argument):
    print(f"[*] export_to_json() called with {len(data)} items in mode {mode}")
    if mode == "user":
        filename = f"TIKTOK_USER_{argument}_{datetime.date.today()}.json"
    else:
        filename = f"TIKTOK_TAGS_{argument}_{datetime.date.today()}.json"
    try: 
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"data": data}, f, ensure_ascii=False, indent=4)
        output_box.insert(tk.END, f"✅ Fișier JSON \"{filename}\" creat cu succes.\n", "green_text")
        print(f"[*] JSON file {filename} created.")
    except Exception as e:
        output_box.insert(tk.END, f"Eroare fișier JSON: {e}", "error_text")
        print(e)

root.mainloop()
