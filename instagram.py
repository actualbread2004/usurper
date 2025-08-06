import tkinter as tk
from tkinter import ttk, scrolledtext, font
import pytz
from datetime import datetime
import webbrowser
import time
import datetime
import json
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
import pickle
import os

COOKIE_FILE = "instagram_cookies.pkl"
link_map = {}

def save_cookies(driver, path=COOKIE_FILE):
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("Cookies saved.")

def load_cookies(driver, path=COOKIE_FILE):
    if not os.path.exists(path):
        print("Cookie file not found.")
        return False

    driver.get("https://www.instagram.com/")
    with open(path, "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)
    driver.refresh()
    print("Cookies loaded.")
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
        driver.get("https://www.instagram.com/accounts/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați ENTER în terminal (NU în zona de output a aplicației).\n", "white_text")
        input("✅ După ce te-ai logat, apasă Enter aici...")
        save_cookies(driver)
        driver.quit()
        return


    try:
        url = f"https://www.instagram.com/{user}/"
        driver.get(url)
        driver.implicitly_wait(5)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), '@') or contains(text(), '')]"))
            )
            output_box.insert(tk.END, "✅ Utilizatorul ", "green_text")
            insert_clickable_link(url, user)
            output_box.insert(tk.END, " există!\n", "green_text")
        except Exception:
            try:
                if driver.find_element(By.XPATH, "//*[contains(text(), \"Sorry, this page\")]"):
                    output_box.insert(tk.END, f"❌ Utilizatorul \"{user}\" nu există.\n", "error_text")
                    driver.quit()
                    return
            except NoSuchElementException:
                output_box.insert(tk.END, f"❌ Eroare necunoscută la accesarea profilului \"{user}\".\n", "error_text")
                driver.quit()
                return
        try:
            if driver.find_element(By.XPATH, "//*[contains(text(), \"This account is private\")]"):
                    output_box.insert(tk.END, f"🔒 Profilul \"{user}\" este privat. Nu pot accesa conținutul.\n", ["error_text", "bold"])
                    driver.quit()
                    return
        except NoSuchElementException:
            pass
        
        # Scroll to load more reels
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(1):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/reel/"], a[href*="/p/"]')
        

        unique_links = []
        for video in video_elements:
            href = video.get_attribute("href")
            if href and href not in unique_links:
                unique_links.append(href)
        
        unique_links = list(set(elem.get_attribute("href") for elem in video_elements))

        has_word_videos = []
        no_word_videos = []
        count = 1
        data = []
        
        try:
            if driver.find_element(By.XPATH, "//*[contains(text(), \"Verified\")]"):
                output_box.insert(tk.END, "Profilul este verificat!\n\n", "green_text")
            else:
                output_box.insert(tk.END, "Profilul nu este verificat.\n\n", "error_text")
        except Exception:
            output_box.insert(tk.END, "Nu am putut verifica starea profilului.\n\n", "error_text")

        for link in unique_links:
            driver.get(link)
            wait = WebDriverWait(driver, 10)

            
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//time[@datetime]')))
            except TimeoutException:
                continue
            
            caption = "N/A"
            try:
                caption_element = driver.find_element(By.CSS_SELECTOR, "h1._ap3a")
                print("Caption:", caption_element.text)
                caption = caption_element.text.strip()
            except Exception as e:
                print("Caption not found:", e)

            try:
                likes_elem = wait.until(EC.presence_of_element_located((
                    By.XPATH, '//a[contains(@href, "/liked_by/")]//span[1]'
                )))
                likes = likes_elem.text.strip().replace(",", "")
            except:
                likes = "N/A"

            try:
                time_elem = wait.until(EC.presence_of_element_located((
                    By.XPATH, '//time[@datetime]'
                )))
                iso_date = time_elem.get_attribute("datetime")
                title_date = time_elem.get_attribute("title")
            except Exception:
                iso_date = "N/A"
                title_date = "N/A"

            local_time_str = "N/A"
            if iso_date != "N/A":
                try:
                    utc_time = datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=pytz.utc)
                    local_tz = pytz.timezone("Europe/Bucharest")
                    local_time = utc_time.astimezone(local_tz)
                    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    local_time_str = "Invalid format"

            if keywords and any(kw in caption.lower() for kw in keywords):
                has_word_videos.append({
                    "caption": caption,
                    "link": link,
                    "likes": likes,
                    "iso_date": local_time_str,
                    "title_date": title_date
                })
            else:
                no_word_videos.append({
                    "caption": caption,
                    "link": link,
                    "likes": likes,
                    "iso_date": local_time_str,
                    "title_date": title_date
                })

        count = 1
        if not keywords:
            all_videos = has_word_videos + no_word_videos
            for video in all_videos:
                output_box.insert(tk.END, f"{count}) ", "white_text")
                output_box.insert(tk.END, f"{video['caption']} | {video['likes']}\n")
                output_box.insert(tk.END, f"Data: {video['title_date']} ({video['iso_date']})\n", "white_text")
                output_box.insert(tk.END, "Link: ", "white_text")
                insert_clickable_link(video['link'], video['link'] + "\n")
                output_box.insert(tk.END, "\n")
                data.append({
                    "counter": count,
                    "iso_date": video['iso_date'],
                    "title_date": video['title_date'],
                    "caption": video['caption'],
                    "link": video['link'],
                    "likes": video['likes']
                })
                count += 1
        else:
            output_box.insert(tk.END, f"\n==== VIDEOCLIPURI CU CUVINTELE CHEIE: {', '.join(keywords)}\n", "big_bold")
            for video in has_word_videos:
                output_box.insert(tk.END, f"{count}) ", "white_text")
                insert_with_highlight(video['caption'], keywords)
                output_box.insert(tk.END, f" | {video['likes']}\n")
                output_box.insert(tk.END, f"Data: {video['title_date']} ({video['iso_date']})\n", "white_text")
                output_box.insert(tk.END, "Link: ", "white_text")
                insert_clickable_link(video['link'], video['link'] + "\n")
                output_box.insert(tk.END, "\n")
                data.append({
                    "counter": count,
                    "iso_date": video['iso_date'],
                    "title_date": video['title_date'],
                    "caption": video['caption'],
                    "link": video['link'],
                    "likes": video['likes'],
                    "keywords": keywords
                })
                count += 1
            output_box.insert(tk.END, f"\n==== VIDEOCLIPURI FĂRĂ CUVINTELE CHEIE: {', '.join(keywords)}\n", "big_bold")
            count = 1
            for video in no_word_videos:
                output_box.insert(tk.END, f"{count}) ", "white_text")
                output_box.insert(tk.END, f"{video['caption']} | {video['likes']}\n")
                output_box.insert(tk.END, f"Data: {video['title_date']} ({video['iso_date']})\n", "white_text")
                output_box.insert(tk.END, "Link: ", "white_text")
                insert_clickable_link(video['link'], video['link'] + "\n")
                output_box.insert(tk.END, "\n")
                data.append({
                    "counter": count,
                    "iso_date": video['iso_date'],
                    "title_date": video['title_date'],
                    "caption": video['caption'],
                    "link": video['link'],
                    "likes": video['likes']
                })
                count += 1

        export_to_json(data, mode="user", argument=user)
        
    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare: {e}\n", "error_text")
    finally:
        driver.quit()
    t2 = time.time()
    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")

def scrape_tags():
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    hashtags_input = input_entry.get().strip()
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    if not hashtags_input:
        output_box.insert(tk.END, "⚠️ Câmpul țintă este gol. ⚠️\n", "error_text")
        return

    hashtags = [tag.strip().lstrip("#") for tag in hashtags_input.replace(',', ' ').split() if tag]

    if not hashtags:
        output_box.insert(tk.END, "⚠️ Hashtag(uri) invalid. ⚠️", "error_text")
        return

    output_box.insert("end", f"✅ Căutare după hashtag(-uri): {', '.join(hashtags)}\n", "big_bold")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    if not load_cookies(driver):
        driver.get("https://www.instagram.com/accounts/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați ENTER în terminal.\n", "white_text")
        input("✅ După ce te-ai logat, apasă ENTER aici... ")
        save_cookies(driver)
        driver.quit()
        return

    data = []

    for hashtag in hashtags:
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        driver.get(url)
        time.sleep(5)

        output_box.insert("end", f"\n📌 Rezultate pentru #{hashtag}:\n", ["green_text", "big_bold"])

        # Scroll to load more posts
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(1):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Use reels/posts selector
        post_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/reel/'], a[href*='/p/']")
        unique_links = []
        for elem in post_links:
            href = elem.get_attribute("href")
            if href and href not in unique_links:
                unique_links.append(href)

        count = 1
        for link in unique_links:
            driver.get(link)
            time.sleep(2)

            wait = WebDriverWait(driver, 10)

            username_elem = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '//a[starts-with(@href, "/") and not(contains(@href, "/reel")) and not(contains(@href, "/p/"))]'
                ))
            )
            username = username_elem.text.strip()
            if not username:
                username = "N/A"

            caption = "N/A"
            raw_caption = "N/A"
            prediction = "N/A"
            captions = driver.find_elements(By.XPATH, '//div[contains(@class,"_aagv")]//img[@alt]')
            if captions:
                raw_caption = captions[0].get_attribute("alt")
            if not raw_caption or raw_caption == "":
                raw_caption = "N/A"
            else:
                phrase = "Ar putea fi"
                index = raw_caption.find(phrase)

                if index != -1:
                    caption = raw_caption[:index].strip()
                    prediction = raw_caption[index:].strip()
                else:
                    caption = raw_caption.strip()
                    
                
            try:
                verified_elem = driver.find_element(By.XPATH, '//svg/title[text()="Verified"]')
                is_verified = True
            except Exception:
                is_verified = False

            
            likes_elem = wait.until(EC.presence_of_element_located((
                By.XPATH,
                '//a[contains(@href, "/liked_by/")]//span[1]'
            )))
            likes = likes_elem.text.strip().replace(",", "")
            
            try:
                time_elem = wait.until(EC.presence_of_element_located((
                    By.XPATH,
                    '//time[@datetime]'
                )))
                iso_date = time_elem.get_attribute("datetime")
                title_date = time_elem.get_attribute("title")
            except Exception:
                iso_date = "N/A"
                title_date = "N/A"

            # Default fallback
            local_time_str = "N/A"

            if iso_date != "N/A":
                try:
                    utc_time = datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=pytz.utc)
                    local_tz = pytz.timezone("Europe/Bucharest")
                    local_time = utc_time.astimezone(local_tz)
                    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    local_time_str = "Invalid format"

            output_box.insert(tk.END, f"{count}) [", "white_text")
            insert_clickable_link(f"www.instagram.com/{username}", f"{username}")
            output_box.insert(tk.END, "] ")
            output_box.insert(tk.END, f"{caption} | {likes}\n")
            output_box.insert(tk.END, f"Data: {title_date} ({local_time_str})\n", "white_text")
            output_box.insert(tk.END, f"Analiză: {prediction}\n", "white_text")
            output_box.insert(tk.END, "Link: ", "white_text")
            insert_clickable_link(link, link + "\n")
            output_box.insert(tk.END, "\n")
            data.append({
                "counter": count,
                "username": username,
                "verified": is_verified,
                "iso_date": iso_date,
                "title_date": title_date,
                "caption": caption,
                "link": link,
                "hashtag": hashtag,
                "keywords": keywords,
                "likes": likes
            })
            count += 1

    export_to_json(data, mode="tags", argument="-".join(hashtags))
    driver.quit()
    t2 = time.time()
    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")






def run_scraper():
    mode = mode_var.get()
    if mode == "USER":
        scrape_user()
    else:
        scrape_tags()

# ---- Interface ----
background_color = "#0d2d61"
root = tk.Tk()
root.state('zoomed')
root.title("Instagram Scraper")
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
    print(f"export_to_json() called with {len(data)} items in mode {mode}")
    if mode == "user":
        filename = f"INSTAGRAM_USER_{argument}_{datetime.date.today()}.json"
    else:
        filename = f"INSTAGRAM_TAGS_{argument}_{datetime.date.today()}.json"
    try: 
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"data": data}, f, ensure_ascii=False, indent=4)
        output_box.insert(tk.END, f"✅ Fișier JSON \"{filename}\" creat cu succes.\n", "green_text")
        print(f"JSON file {filename} created.")
    except Exception as e:
        output_box.insert(tk.END, f"Eroare fișier JSON: {e}", "error_text")
        print(e)

root.mainloop()