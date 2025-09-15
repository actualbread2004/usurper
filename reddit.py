import json
import praw
import prawcore
import tkinter as tk
from tkinter import ttk, scrolledtext, font
import webbrowser
import time
import datetime

# ---- Reddit API Auth ----
reddit = praw.Reddit(
    client_id="YjC9EegtIH7gvlCieoYwyw",
    client_secret="s78mpoCUMqa3ea-2CBTQ65UFkV-Qfw",
    user_agent="myScraper by u/EntirePlantain",
    username="EntirePlantain",
    password="alin2004"
)

link_map = {}

# ---- Hyperlink click ----
def open_link(event):
    index = output_box.index("@%s,%s" % (event.x, event.y))
    for tag in output_box.tag_names(index):
        if tag in link_map:
            webbrowser.open(link_map[tag])
            return

# ---- Insert clickable link ----
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

# ---- Reddit ----
def scrape_user(username, output_box):
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    try:
        redditor = reddit.redditor(username)
        _ = redditor.id
        output_box.insert(tk.END, f"✅ Utilizatorul \"{username}\" a fost găsit.\n", ("green_text", "big_bold"))
    except prawcore.exceptions.NotFound:
        output_box.insert(tk.END, f"❌ Utilizatorul \"{username}\" NU există sau nu poate fi accesat.\n", "error_text")
        return
    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare la verificare: {e}\n", "error_text")
        return

    # ---- Informatii generale despre user
    output_box.insert(tk.END, f"Profil: ", "bold")
    insert_clickable_link(f"https://www.reddit.com/user/{redditor.name}", display_text=redditor.name)
    output_box.insert(tk.END, f"\nID unic: {redditor.id}\n", "bold")
    output_box.insert(tk.END, f"\nKarma: {redditor.link_karma + redditor.comment_karma} ({redditor.link_karma} din postări și {redditor.comment_karma} din comentarii)\n", "bold")
    output_box.insert(tk.END, "Data creării contului: ", "bold")
    output_box.insert(tk.END, f"{time_created(redditor.created_utc)}\n", "white_text")

    # Este moderator
    output_box.insert(tk.END, "Este moderator la minim un subreddit: ", "bold")
    if redditor.is_mod:
        output_box.insert(tk.END, "Da\n", ("bold", "green_text"))
    else:
        output_box.insert(tk.END, "Nu\n", ("bold", "white_text"))

    # Este administrator
    output_box.insert(tk.END, "Este administrator: ", "bold")
    if redditor.is_employee:
        output_box.insert(tk.END, "Da\n", ("bold", "green_text"))
    else:
        output_box.insert(tk.END, "Nu\n", ("bold", "white_text"))

    # Este verificat
    output_box.insert(tk.END, "Este verificat: ", "bold")
    if redditor.verified:
        output_box.insert(tk.END, "Da\n", ("bold", "green_text"))
    else:
        output_box.insert(tk.END, "Nu\n", ("bold", "white_text"))

    # ---- Postări și comentarii ale user-ului
    has_word_posts, no_word_posts = [], []
    for submission in redditor.submissions.new(limit=int(limita_entry.get())):
        text = (submission.title + " " + (submission.selftext or "")).lower()
        if keywords and any(kw in text for kw in keywords):
            has_word_posts.append(submission)
        else:
            no_word_posts.append(submission)
    data = []
    if has_word_posts or no_word_posts:
        output_box.insert(tk.END, "\nPostări găsite:\n", ("green_text", "big_bold"))
        if keywords:
            output_box.insert(tk.END, f"\n=== POSTĂRI CU CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, post in enumerate(has_word_posts, 1):
            output_box.insert(tk.END, f"{i}) ", "bold")
            output_box.insert(tk.END, "[")
            output_box.insert(tk.END, f"{post.subreddit}", "bold")
            output_box.insert(tk.END, "] ")
            insert_with_highlight(post.selftext or "", keywords)
            insert_with_highlight(post.title + "\nUpvotes: " + str(post.score) + "\nConținut: ", keywords)
            output_box.insert(tk.END, f"\nData postării: {time_created(post.created_utc)}")
            output_box.insert(tk.END, "\nLink: ")
            insert_clickable_link(post.url)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "type": "post",
                "count": i,
                "subreddit": str(post.subreddit),
                "post_text": post.selftext or "",
                "score": str(post.score),
                "link": post.url,
                "created_utc": time_created(post.created_utc),
                "keywords": keywords
            })
        prev_count = len(data)
        if keywords:
            output_box.insert(tk.END, f"\n=== POSTĂRI FĂRĂ CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, post in enumerate(no_word_posts, 1):
            output_box.insert(tk.END, f"{i}) ", "bold")
            output_box.insert(tk.END, "[")
            output_box.insert(tk.END, f"{post.subreddit}", "bold")
            output_box.insert(tk.END, "] ")
            insert_with_highlight(post.selftext or "", keywords)
            insert_with_highlight(post.title + "\nUpvotes: " + str(post.score) + "\nConținut: ", keywords)
            output_box.insert(tk.END, f"\nData postării: {time_created(post.created_utc)}")
            output_box.insert(tk.END, "\nLink: ")
            insert_clickable_link(post.url)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "type": "post",
                "count": i + prev_count,
                "subreddit": str(post.subreddit),
                "selftext": post.selftext or "",
                "score": str(post.score),
                "link": post.url,
                "created_utc": time_created(post.created_utc)
            })
    else:
        output_box.insert(tk.END, "Utilizatorul nu are postări.\n", "bold")

    has_word_comments, no_word_comments = [], []
    for comment in redditor.comments.new(limit=int(limita_entry.get())):
        text = comment.body.lower()
        if keywords and any(kw in text for kw in keywords):
            has_word_comments.append(comment)
        else:
            no_word_comments.append(comment)

    if has_word_comments or no_word_comments:
        output_box.insert(tk.END, "\nComentarii găsite:\n", ("green_text", "big_bold"))
        if keywords:
            output_box.insert(tk.END, f"\n=== COMENTARII CU CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, comment in enumerate(has_word_comments, 1):
            output_box.insert(tk.END, f"{i}) ", "bold")
            output_box.insert(tk.END, "[", "bold")
            output_box.insert(tk.END, f"{comment.subreddit}", "bold")
            output_box.insert(tk.END, "] ")
            insert_with_highlight(comment.body, keywords)
            output_box.insert(tk.END, f"\nUpvotes: {comment.score}\nLink: ")
            insert_clickable_link("https://reddit.com" + comment.permalink)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "type": "comment",
                "count": i,
                "subreddit": str(comment.subreddit),
                "selftext": comment.body,
                "score": str(comment.score),
                "link": comment.permalink,
                "keywords": keywords
            })
        prev_count = len(data)
        if keywords:
            output_box.insert(tk.END, f"\n=== COMENTARII FĂRĂ CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, comment in enumerate(no_word_comments, 1):
            output_box.insert(tk.END, f"{i})", "bold")
            output_box.insert(tk.END, " [")
            output_box.insert(tk.END, f"{comment.subreddit}", "bold")
            output_box.insert(tk.END, "] ")
            insert_with_highlight(comment.body, keywords)
            output_box.insert(tk.END, f"\nUpvotes: {comment.score}\nLink: ")
            insert_clickable_link("https://reddit.com" + comment.permalink)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "type": "comment",
                "count": i + prev_count,
                "subreddit": str(comment.subreddit),
                "selftext": comment.body,
                "score": str(comment.score),
                "link": comment.permalink
            })
    else:
        output_box.insert(tk.END, "Utilizatorul nu are comentarii.\n", "bold")

    export_to_json(data, mode="user", argument=username)
    t2 = time.time()
    output_box.insert(tk.END, f"\nTimp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")
    status_var.set("Status: Căutare finalizată.")
    root.update_idletasks()  # refresh the UI

# ---- Scrape subreddit ----
def scrape_subreddit(subreddit_name, sort_type, output_box):
    t1 = time.time()
    output_box.delete('1.0', tk.END)
    raw = keyword_entry.get().strip()
    keywords = [kw.strip().lower() for kw in raw.replace(",", " ").split() if kw.strip()]

    try:
        subreddit = reddit.subreddit(subreddit_name)
        _ = subreddit.id
        output_box.insert(tk.END, f"✅ Subreddit-ul \"{subreddit_name}\" a fost găsit.\n", ("green_text", "big_bold"))
    except prawcore.exceptions.NotFound:
        output_box.insert(tk.END, f"❌ Subreddit-ul \"{subreddit_name}\" NU există sau este privat.\n", "error_text")
        return
    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Eroare la verificare: {e}\n", "error_text")
        return
    
    output_box.insert(tk.END, f"Subreddit: ", "bold")
    insert_clickable_link(f"https://www.reddit.com/r/{subreddit_name}", display_text=subreddit_name)

    output_box.insert(tk.END, "\nData creării subreddit-ului: ", "bold")
    output_box.insert(tk.END, f"{time_created(subreddit.created_utc)}", "white_text")
    # --- Moderatorii subreddit-ului si link catre pagina fiecaruia
    output_box.insert(tk.END, "\nModeratori: ", "bold")
    mods = list(subreddit.moderator())
    for i, mod in enumerate(mods):
        profile_url = f"https://www.reddit.com/user/{mod.name}"
        insert_clickable_link(profile_url, display_text=mod.name)
        if i < len(mods) - 1:
            output_box.insert(tk.END, ", ")

    output_box.insert(tk.END, f"\n\nPrimele {limita_entry.get()} postări sortate după {sort_type.upper()}:\n", "bold")
    if sort_type == "hot":
        posts = subreddit.hot(limit=int(limita_entry.get()))
    elif sort_type == "new":
        posts = subreddit.new(limit=int(limita_entry.get()))
    elif sort_type == "top":
        posts = subreddit.top(limit=int(limita_entry.get()))
    elif sort_type == "latest":
        posts = subreddit.new(limit=int(limita_entry.get()))
    elif sort_type == "rising":
        posts = subreddit.rising(limit=int(limita_entry.get()))
    else:
        posts = subreddit.hot(limit=int(limita_entry.get()))

    has_word_posts, no_word_posts = [], []
    for post in posts:
        text = (post.title + " " + (post.selftext or "")).lower()
        if keywords and any(kw in text for kw in keywords):
            has_word_posts.append(post)
        else:
            no_word_posts.append(post)
    data = []
    if has_word_posts or no_word_posts:
        if keywords:
            output_box.insert(tk.END, f"\n=== POSTĂRI CU CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, post in enumerate(has_word_posts, 1):
            output_box.insert(tk.END, f"{i}) [{post.author}]", "bold")
            insert_with_highlight(post.selftext or "", keywords)
            insert_with_highlight(post.title + "\nUpvotes: " + str(post.score) + "\nConținut: ", keywords)
            output_box.insert(tk.END, f"\n\nData postării: {time_created(post.created_utc)}")
            output_box.insert(tk.END, "\nNumăr de comentarii: " + str(post.num_comments))
            output_box.insert(tk.END, "\nLink: ")
            insert_clickable_link(post.url)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "title": post.title,
                "author": str(post.author),
                "created_utc": time_created(post.created_utc),
                "url": post.url,
                "score": post.score,
                "num_comments": post.num_comments,
                "selftext": post.selftext or "",
                "keywords": keywords
            })
        if keywords:
            output_box.insert(tk.END, f"\n=== POSTĂRI FĂRĂ CUVINTELE \"{', '.join(keywords)}\" ===\n", "big_bold")
        for i, post in enumerate(no_word_posts, 1):
            output_box.insert(tk.END, f"{i}) ", "bold")
            insert_with_highlight(post.selftext or "", keywords)
            insert_with_highlight(post.title + "\nUpvotes: " + str(post.score) + "\nConținut: ", keywords)
            output_box.insert(tk.END, f"\n\nData postării: {time_created(post.created_utc)}")
            output_box.insert(tk.END, "\nNumăr de comentarii: " + str(post.num_comments))
            output_box.insert(tk.END, "\nLink: ")
            insert_clickable_link(post.url)
            output_box.insert(tk.END, '\n' + "-" * 150 + '\n\n', "bold")
            data.append({
                "title": post.title,
                "author": str(post.author),
                "created_utc": time_created(post.created_utc),
                "url": post.url,
                "score": post.score,
                "num_comments": post.num_comments,
                "selftext": post.selftext or ""
            })
    else:
        output_box.insert(tk.END, "Nu s-au găsit postări.\n", "bold")

    export_to_json(data, mode="subreddit", argument=subreddit)
    t2 = time.time()
    output_box.insert(tk.END, f"\nTimp total de execuție: {t2 - t1:.2f} secunde.\n", "bold")
    status_var.set("Status: Căutare finalizată.")
    root.update_idletasks()  # refresh the UI


def run_scraper():
    output_box.delete('1.0', tk.END)
    if not input_entry.get().strip():
        output_box.insert(tk.END, " /!\\ Introduceți un nume de utilizator sau subreddit /!\\")
        return
    if not limita_entry.get().isdigit():
        output_box.insert(tk.END, " /!\\ Introduceți o limită validă de postări /!\\")
        return
    mode = mode_var.get()
    status_var.set("Status: Căutare în curs...")
    root.update_idletasks()  # refresh the UI
    if mode == "USER":
        username = input_entry.get().strip()
        scrape_user(username, output_box)
    else:
        subreddit_name = input_entry.get().strip()
        sort_type = sort_var.get().lower()
        scrape_subreddit(subreddit_name, sort_type, output_box)

    content = output_box.get("1.0", tk.END).strip()
    if not content:
        output_box.delete('1.0', tk.END)
        output_box.insert(tk.END, "Utilizatorul/Subreddit-ul nu are conținut.")
        return

# ---- View/Hide filtre specifice ----
def update_input_label(event=None):
    mode = mode_var.get()
    input_entry.delete(0, tk.END)
    output_box.delete('1.0', tk.END)
    if mode == "USER":
        input_label.config(text="Introduceți USERNAME țintă:")
        sort_label.pack_forget()
        sort_dropdown.pack_forget()
    else:
        input_label.config(text="Introduceți SUBREDDIT țintă:")
        output_box.pack_forget()
        run_button.pack_forget()
        sort_label.pack(pady=5)
        sort_dropdown.pack(pady=5)
        run_button.pack(pady=10)
        output_box.pack(padx=10, pady=10)

# ---- Interfata ----
background_color = "#0d2d61"
root = tk.Tk()
root.state('zoomed')
root.title("Scraper")
root.configure(bg=background_color)

mode_var = tk.StringVar(value="USER")
sort_var = tk.StringVar(value="Hot")

mode_label = tk.Label(root, text="Căutare după:")
mode_label.pack(pady=5)
mode_dropdown = ttk.Combobox(root, textvariable=mode_var, values=["USER", "SUBREDDIT"], state="readonly")
mode_dropdown.pack(pady=5)
mode_dropdown.bind("<<ComboboxSelected>>", update_input_label)

limita_label = tk.Label(root, text="Limita de postări:")
limita_label.pack(pady=5)
limita_entry = tk.Entry(root, width=5)
limita_entry.pack(pady=5)
limita_entry.insert(0, "5")
limita_entry.bind("<Return>", lambda e: run_scraper())

input_label = tk.Label(root, text="Introduceți USERNAME țintă:")
input_label.pack(pady=5)
input_entry = tk.Entry(root, width=40)
input_entry.pack(pady=5)
input_entry.bind("<Return>", lambda e: run_scraper())


sort_label = tk.Label(root, text="Sortare după:")
sort_label.pack_forget()
sort_dropdown = ttk.Combobox(root, textvariable=sort_var, values=["Hot", "New", "Top", "Latest", "Rising"], state="readonly")
sort_dropdown.pack_forget()

keyword_label = tk.Label(root, text="Opțional - cuvânt cheie (pentru cuvinte multiple, separați prin spațiu sau virgulă):")
keyword_label.pack(pady=5)
keyword_entry = tk.Entry(root, width=20)
keyword_entry.pack(pady=5)
keyword_entry.bind("<Return>", lambda e: run_scraper())

# ---- Culori & Design
mode_label.configure(bg=background_color, fg="white")
limita_label.configure(bg=background_color, fg="white")
input_label.configure(bg=background_color, fg="white")
keyword_label.configure(bg=background_color, fg="white")
sort_label.configure(bg=background_color, fg="white")

run_button = tk.Button(root, text="Caută", command=run_scraper)
run_button.pack(pady=10)

status_var = tk.StringVar(value="Status: Așteptare")
status_label = tk.Label(root, textvariable=status_var, bg=background_color, fg="white", anchor="w")
status_label.pack(anchor="w", padx=10, pady=0)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=200, height=50, font=("Consolas", 14), bg = "#081d40", fg="white")
output_box.pack(padx=10, pady=10)

# ---- Config tags ----
big_font = font.Font(output_box, output_box.cget("font"))
big_font.configure(size=16, weight="bold")
output_box.tag_configure("big_bold", font=big_font)
bold_font = font.Font(output_box, output_box.cget("font"))
bold_font.configure(weight="bold")
output_box.tag_configure("green_text", foreground="#1fff2a")
output_box.tag_configure("error_text", foreground="red")
output_box.tag_configure("white_text", foreground="white")
output_box.tag_configure("bold", font=bold_font)
output_box.tag_configure("highlight", background="#abab61")

# ---- Bind Enter ----
def on_enter_pressed(event):
    run_scraper()
root.bind('<Return>', on_enter_pressed)

def export_to_json(data, mode, argument):
    print(f"export_to_json called with {len(data)} items in mode {mode}")
    filename = f"REDDIT_{mode.upper()}_{argument}_{datetime.date.today()}.json"
    try: 
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"data": data}, f, ensure_ascii=False, indent=4)
        output_box.insert(tk.END, f"✅ Fișier JSON \"{filename}\" creat cu succes.\n", "green_text")
        print(f"JSON file {filename} created.")
    except Exception as e:
        output_box.insert(tk.END, f"Eroare fișier JSON: {e}", "error_text")
        print(e)

root.mainloop()
