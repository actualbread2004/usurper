import instaloader
import sys
import time
import random

USERNAME = "biborteni2000"
PASSWORD = "alin2004"
TARGET_PROFILE = "irinarimes"

def main():
    L = instaloader.Instaloader()

    # Try to load saved session first
    try:
        L.load_session_from_file(USERNAME)
        print(f"Session loaded for {USERNAME}")
    except FileNotFoundError:
        print("No saved session found. Logging in...")
        try:
            L.login(USERNAME, PASSWORD)
        except instaloader.exceptions.BadCredentialsException:
            print("Login failed: check your username and password.")
            sys.exit(1)
        L.save_session_to_file()
        print("Session saved.")

    try:
        profile = instaloader.Profile.from_username(L.context, TARGET_PROFILE)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"Profile '{TARGET_PROFILE}' doesn't exist.")
        sys.exit(1)

    print(f"Scraping posts from: {profile.username}")
    post_count = 0

    try:
        for post in profile.get_posts():
            print(f"Post URL: {post.url}")
            post_count += 1
            time.sleep(random.randint(5, 10))  # Correct sleep with random delay

            if post_count >= 10:
                print("Reached post limit, stopping.")
                break
    except instaloader.exceptions.ConnectionException as e:
        print("Connection error:", e)
    except instaloader.exceptions.QueryReturnedBadRequestException:
        print("Too many requests - rate limited by Instagram, please wait and try later.")

if __name__ == "__main__":
    main()
