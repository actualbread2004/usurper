import tkinter as tk
from tkinter import ttk, scrolledtext, font, messagebox
import webbrowser
import time
import datetime
import json
import re
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pytz
from selenium.common.exceptions import NoSuchElementException

COOKIE_FILE = "x_cookies.pkl"
link_map = {}

def save_cookies(driver, path=COOKIE_FILE):
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("Cookies saved.")

def load_cookies(driver, path=COOKIE_FILE):
    if not os.path.exists(path):
        print("Cookie file not found.")
        return False

    driver.get("https://x.com/home")
    with open(path, "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)
    driver.refresh()
    print("Cookies loaded.")
    return True

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

def insert_with_highlight(text, keywords):
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


# ---- JSON Export ----
def export_to_json(data, mode, argument):
    if mode == "user":
        filename = f"X_USER_{argument}_{datetime.date.today()}.json"
    else:
        filename = f"X_TAGS_{argument}_{datetime.date.today()}.json"
    try: 
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"data": data}, f, ensure_ascii=False, indent=4)
        output_box.insert(tk.END, f"✅ Fișier JSON \"{filename}\" creat cu succes.\n", "green_text")
    except Exception as e:
        output_box.insert(tk.END, f"Eroare fișier JSON: {e}", "error_text")
        
def extract_profile_info(driver):
    try:
        name_el = driver.find_element(By.XPATH, '//div[@data-testid="UserName"]//span[1]')
        output_box.insert(tk.END, f"Nume public: {name_el.text}\n")

        try:
            bio_el = driver.find_element(By.XPATH, '//div[@data-testid="UserDescription"]')
            output_box.insert(tk.END, f"Bio: {bio_el.text}\n")
        except:
            output_box.insert(tk.END, "Bio: N/A\n", "error_text")

        try:
            join_el = driver.find_element(By.XPATH, '//span[contains(text(), "Joined ")]')
            join_date = join_el.text.replace("Joined ", "")
            output_box.insert(tk.END, f"Data creării contului: {join_date}\n")
        except:
            output_box.insert(tk.END, "Data creării contului: N/A\n", "error_text")

        try:
            following_el = driver.find_element(By.XPATH, '//a[contains(@href,"/following")]/span[1]/span')
            output_box.insert(tk.END, f"Urmărit de: {following_el.text}\n conturi. (following)")
        except:
            output_box.insert(tk.END, "Urmărit de: N/A (following)\n", "error_text")

        try:
            followers_el = driver.find_element(By.XPATH, '//a[contains(@href,"/verified_followers")]/span[1]/span')
            output_box.insert(tk.END, f"Urmăritori: {followers_el.text}\n")
        except:
            output_box.insert(tk.END, "Urmăritori: N/A (followers)\n\n", "error_text")


    except Exception as e:
        print(f"⚠️ Failed to extract profile info: {e}")

def scrape_tags():
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    tag = input_entry.get().strip()
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    if not tag:
        output_box.insert(tk.END, "⚠️ Câmpul hashtag este gol. ⚠️\n", "error_text")
        return

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


    if not load_cookies(driver):
        driver.get("https://x.com/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați OK.\n", "white_text")
        messagebox.showinfo("Autentificare", "✅ După ce te-ai logat, apasă OK aici")
        save_cookies(driver)
        driver.quit()
        return
    try:
        tag_clean = tag.lstrip("#")
        hashtags = [tag.strip().lstrip("#") for tag in tag.replace(',', ' ').split() if tag]
        url = f"https://x.com/search?q=%23{tag_clean}&src=typed_query&f=live"
        driver.get(url)
        time.sleep(5)
        output_box.insert("end", f"✅ Căutare după hashtag(-uri): {', '.join(hashtags)}\n\n", ["big_bold", "green_text"])


        # Scroll for more tweets
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        articles = driver.find_elements(By.XPATH, '//article')
        has_word_videos = []
        no_word_videos = []
        seen_links = set()

        for article in articles:
            try:
                # Extract full tweets
                blocks = article.find_elements(By.XPATH, ".//div[@data-testid='tweetText']")
                quoted_caption = ""
                if len(blocks) == 1:
                    caption = blocks[0].text
                elif len(blocks) >= 2:
                    caption = blocks[0].text
                    quoted_caption = blocks[1].text
                else:
                    caption = article.text

                link_elements = article.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')
                tweet_url = None
                for a in link_elements:
                    href = a.get_attribute("href")
                    if "/status/" in href:
                        tweet_url = href
                        break

                if not tweet_url or tweet_url in seen_links:
                    continue
                
                date_element = article.find_element(By.XPATH, ".//time")
                iso_date = date_element.get_attribute("datetime")
                title_date = date_element.get_attribute("title")

                local_time_str = "N/A"
                if iso_date != "N/A":
                    try:
                        utc_time = datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=pytz.utc)
                        local_tz = pytz.timezone("Europe/Bucharest")
                        local_time = utc_time.astimezone(local_tz)
                        local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        local_time_str = "Invalid format"

                seen_links.add(tweet_url)

                matched = not keywords or any(kw in caption.lower() for kw in keywords)
                
                retweets_button = driver.find_element(By.XPATH, '//button[@data-testid="retweet"]')
                aria_label = retweets_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+repost', aria_label)
                retweets = match.group(1) if match else "N/A"
                
                reply_button = driver.find_element(By.XPATH, '//button[@data-testid="reply"]')
                aria_label = reply_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+repl(?:ies|y)', aria_label, re.IGNORECASE)
                replies = match.group(1) if match else "N/A"
                
                like_button = driver.find_element(By.XPATH, '//button[@data-testid="like"]')
                aria_label = like_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+like', aria_label, re.IGNORECASE)
                likes = match.group(1) if match else "N/A"

                item = {
                    "caption": caption,
                    "title_date": title_date,
                    "iso_date": local_time_str,
                    "likes": likes,
                    "retweets": retweets,
                    "comments": replies,
                    "quoted_caption": quoted_caption,
                    "link": tweet_url,
                    "matched": matched
                }

                if matched:
                    has_word_videos.append(item)
                else:
                    no_word_videos.append(item)

            except Exception as e:
                print(f"Tweet error: {e}")

        all_items = []

        if not keywords:
            combined = has_word_videos + no_word_videos
            for i, r in enumerate(combined, 1):
                output_box.insert(tk.END, f"{i}) ", "bold")
                output_box.insert(tk.END, f"{r['caption']}\n", "white_text")
                output_box.insert(tk.END, f"Data: {r['iso_date']}\n", "white_text")
                if r.get("quoted_caption"):
                    output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                output_box.insert(tk.END, f"💬 {r['comments']}   🔁 {r['retweets']}   ❤️ {r['likes']}\nLink:")
                insert_clickable_link(r["link"], f"{r['link']}\n")
                r["counter"] = i
                all_items.append(r)
                output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")


        else:
            if has_word_videos:
                output_box.insert(tk.END, f"\n==== POSTĂRI CU CUVINTELE CHEIE \"{', '.join(keywords)}\" ====\n", "big_bold")
                for i, r in enumerate(has_word_videos, 1):
                    output_box.insert(tk.END, f"{i}) ", "bold")
                    insert_with_highlight(f"{r['caption']}\n", keywords)
                    output_box.insert(tk.END, f"Data: {r['iso_date']}\n", "white_text")
                    if r.get("quoted_caption"):
                        output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                    output_box.insert(tk.END, f"💬 {r['comments']}   🔁 {r['retweets']}   ❤️ {r['likes']}\n")
                    output_box.insert(tk.END, "Link: ")
                    insert_clickable_link(r["link"], f"{r['link']}\n\n")
                    r["counter"] = i
                    all_items.append(r)
                    output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")


            if no_word_videos:
                output_box.insert(tk.END, f"\n==== POSTĂRI FĂRĂ CUVINTELE CHEIE \"{', '.join(keywords)}\" ====\n", "big_bold")
                for i, r in enumerate(no_word_videos, 1):
                    output_box.insert(tk.END, f"{i}) ", "bold")
                    output_box.insert(tk.END, f"{r['caption']}\n", "white_text")
                    output_box.insert(tk.END, f"Data: {r['iso_date']}\n", "white_text")
                    if r.get("quoted_caption"):
                        output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                    output_box.insert(tk.END, "Link: ")
                    insert_clickable_link(r["link"], f"{r['link']}\n\n")
                    r["counter"] = len(all_items) + 1
                    all_items.append(r)
                    output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")

        if not all_items:
            output_box.insert(tk.END, "\n❌ Niciun rezultat găsit.\n", "error_text")
        else:
            export_to_json(all_items, mode="tag", argument=tag_clean)

    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare: {e}\n", "error_text")
    finally:
        driver.quit()

    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {time.time() - t1:.2f} secunde.\n", "bold")
    status_var.set("Status: Căutare finalizată.")
    root.update_idletasks()  # refresh the UI

def scrape_user():
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    username = input_entry.get().strip().lstrip("@")
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    if not username:
        output_box.insert(tk.END, "⚠️ Câmpul user este gol. ⚠️\n", "error_text")
        return
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    if not load_cookies(driver):
        driver.get("https://x.com/login")
        output_box.insert(tk.END, "🔐 Vă rog să vă logați în browserul care s-a deschis...\nDupă logare, apăsați OK.\n", "white_text")
        messagebox.showinfo("Autentificare", "✅ După ce te-ai logat, apasă OK aici")
        save_cookies(driver)
        driver.quit()
        return

    try:
        url = f"https://x.com/{username}"
        driver.get(url)
        time.sleep(5)

        body_text = driver.page_source

        if "Hmm...this page doesn’t exist. Try searching for something else" in body_text or "This account doesn’t exist" in body_text:
            output_box.insert(tk.END, f"❌ Contul '@{username}' nu există.\n", "error_text")
            driver.quit()
            return

        if "These posts are protected" in body_text or "Only approved followers can see" in body_text:
            output_box.insert(tk.END, f"🔒 Contul '@{username}' este privat.\n", "error_text")
            driver.quit()
            return
        
        output_box.insert(tk.END, "Utilizator ", "green_text")
        insert_clickable_link(f"https://x.com/{username}", f"@{username}")
        output_box.insert(tk.END, " găsit!\n\n", "green_text")
        extract_profile_info(driver)
        output_box.insert(tk.END, "\nPOSTĂRI:\n\n", "big_bold")

        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        articles = driver.find_elements(By.XPATH, '//article')
        has_word_videos = []
        no_word_videos = []
        seen_links = set()

        for article in articles:
            try:
                blocks = article.find_elements(By.XPATH, ".//div[@data-testid='tweetText']")
                quoted_caption = ""
                if len(blocks) == 1:
                    caption = blocks[0].text
                elif len(blocks) >= 2:
                    caption = blocks[0].text
                    quoted_caption = blocks[1].text
                else:
                    caption = article.text

                link_elements = article.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')
                tweet_url = None
                for a in link_elements:
                    href = a.get_attribute("href")
                    if "/status/" in href:
                        tweet_url = href
                        break

                    
                date_element = article.find_element(By.XPATH, ".//time")
                iso_date = date_element.get_attribute("datetime")
                title_date = date_element.get_attribute("title")

                local_time_str = "N/A"
                if iso_date != "N/A":
                    try:
                        utc_time = datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=pytz.utc)
                        local_tz = pytz.timezone("Europe/Bucharest")
                        local_time = utc_time.astimezone(local_tz)
                        local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        local_time_str = "Invalid format"

                if not tweet_url or tweet_url in seen_links:
                    continue

                seen_links.add(tweet_url)

                matched = not keywords or any(kw in caption.lower() for kw in keywords)
                
                retweets_button = driver.find_element(By.XPATH, './/button[@data-testid="retweet"]')
                aria_label = retweets_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+repost', aria_label)
                retweets = match.group(1) if match else "N/A"
                
                reply_button = driver.find_element(By.XPATH, './/button[@data-testid="reply"]')
                aria_label = reply_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+repl(?:ies|y)', aria_label, re.IGNORECASE)
                replies = match.group(1) if match else "N/A"
                
                like_button = driver.find_element(By.XPATH, './/button[@data-testid="like"]')
                aria_label = like_button.get_attribute("aria-label")
                match = re.search(r'([\d,.]+[KkMm]?)\s+like', aria_label, re.IGNORECASE)
                likes = match.group(1) if match else "N/A"
                
                wait = WebDriverWait(driver, 10)
                views_span = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, './/div[contains(@style, "color: rgb(231, 233, 234)")]//span[contains(text(), "M") or contains(text(), "K")]')
                    )
                )
                views = views_span.text
                

                item = {
                    "caption": caption,
                    "iso_date": local_time_str,
                    "title_date": title_date,
                    "likes": likes,
                    "retweets": retweets,
                    "comments": replies,
                    "views": views,
                    "quoted_caption": quoted_caption,
                    "link": tweet_url,
                    "matched": matched
                }

                if matched:
                    has_word_videos.append(item)
                else:
                    no_word_videos.append(item)

            except Exception as e:
                print(f"Tweet error: {e}")

        all_items = []

        if not keywords:
            combined = has_word_videos + no_word_videos
            for i, r in enumerate(combined, 1):
                output_box.insert(tk.END, f"{i}) ", "bold")
                output_box.insert(tk.END, f"{r['caption']}\nData: {r['iso_date']}\n", "white_text")
                if r.get("quoted_caption"):
                    output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                output_box.insert(tk.END, f"💬 {r['comments']}   🔁 {r['retweets']}   ❤️ {r['likes']}\n") 
                output_box.insert(tk.END, "Link: ")
                insert_clickable_link(r["link"], f"{r['link']}\n\n")
                r["counter"] = i
                all_items.append(r)
                output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")

        else:
            if has_word_videos:
                output_box.insert(tk.END, f"\n==== POSTĂRI CU CUVINTELE CHEIE \"{', '.join(keywords)}\" ====\n", "big_bold")
                for i, r in enumerate(has_word_videos, 1):
                    output_box.insert(tk.END, f"{i}) ", "bold")
                    insert_with_highlight(f"{r['caption']}\n", keywords)
                    output_box.insert(tk.END, f"Data: {r['iso_date']}\n", "white_text")
                    if r.get("quoted_caption"):
                        output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                    output_box.insert(tk.END, f"💬 {r['comments']}   🔁 {r['retweets']}   ❤️ {r['likes']}\n")
                    output_box.insert(tk.END, "Link: ")
                    insert_clickable_link(r["link"], f"{r['link']}\n\n")
                    r["counter"] = i
                    all_items.append(r)
                    output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")


            if no_word_videos:
                output_box.insert(tk.END, f"\n==== POSTĂRI FĂRĂ CUVINTELE CHEIE \"{', '.join(keywords)}\" ====\n", "big_bold")
                for i, r in enumerate(no_word_videos, 1):
                    output_box.insert(tk.END, f"{i}) ", "bold")
                    output_box.insert(tk.END, f"{r['caption']}\n", "white_text")
                    output_box.insert(tk.END, f"Data: {r['iso_date']}\n", "white_text")
                    if r.get("quoted_caption"):
                        output_box.insert(tk.END, f"↳ {r['quoted_caption']}\n", "dim_text")
                    output_box.insert(tk.END, f"💬 {r['comments']}   🔁 {r['retweets']}   ❤️ {r['likes']}\n")
                    output_box.insert(tk.END, "Link: ")
                    insert_clickable_link(r["link"], f"{r['link']}\n")
                    r["counter"] = len(all_items) + 1
                    all_items.append(r)
                    output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")

        if not all_items:
            output_box.insert(tk.END, "\nUtilizatorul nu are postări.\n", "error_text")
        else:
            export_to_json(all_items, mode="user", argument=username)

    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare: {e}\n", "error_text")
    finally:
        driver.quit()

    output_box.insert(tk.END, f"\n⏱ Timp total de execuție: {time.time() - t1:.2f} secunde.\n", "bold")
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
root.title("Twitter/X Scraper")
root.configure(bg=background_color)

mode_var = tk.StringVar(value="USER")
mode_label = tk.Label(root, text="Căutare după:", bg=background_color, fg="white")
mode_label.pack(pady=5)

mode_dropdown = ttk.Combobox(root, textvariable=mode_var, values=["USER", "TAGS"], state="readonly")
mode_dropdown.pack(pady=5)

def update_input_label(event=None):
    mode = mode_var.get()
    input_entry.delete(0, tk.END)
    output_box.delete('1.0', tk.END)
    input_label.config(text="Introduceți USERNAME țintă:" if mode == "USER" else "Introduceți TAG-uri țintă:")

mode_dropdown.bind("<<ComboboxSelected>>", update_input_label)

input_label = tk.Label(root, text="Introduceți USERNAME țintă:", bg=background_color, fg="white")
input_label.pack(pady=5)

input_entry = tk.Entry(root, width=40)
input_entry.pack(pady=5)
input_entry.bind("<Return>", lambda e: run_scraper())

keyword_label = tk.Label(root, text="Cuvinte cheie (separate prin spațiu sau virgulă):", bg=background_color, fg="white")
keyword_label.pack(pady=5)

keyword_entry = tk.Entry(root, width=40)
keyword_entry.pack(pady=5)
keyword_entry.bind("<Return>", lambda e: run_scraper())

run_button = tk.Button(root, text="Caută", command=run_scraper)
run_button.pack(pady=10)

status_var = tk.StringVar(value="Status: Așteptare")
status_label = tk.Label(root, textvariable=status_var, bg=background_color, fg="white", anchor="w")
status_label.pack(anchor="w", padx=10, pady=0)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=200, height=50, font=("Consolas", 14), bg="#081d40", fg="white")
output_box.pack(padx=10, pady=10)

bold_font = font.Font(output_box, output_box.cget("font"))
bold_font.configure(weight="bold")
output_box.tag_configure("highlight", background="#abab61")
output_box.tag_configure("green_text", foreground="#1fff2a")
output_box.tag_configure("error_text", foreground="red", font=("Consolas", 11, "bold"))
output_box.tag_configure("bold", font=bold_font)
output_box.tag_configure("big_bold", font=("Consolas", 14, "bold"))
output_box.tag_configure("white_text", foreground="white")
output_box.tag_configure("dim_text", foreground="#888888")


root.mainloop()
