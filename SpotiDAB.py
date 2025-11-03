from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException, StaleElementReferenceException
import pandas as pd
import re
import time
import tkinter as tk
from tkinter import filedialog

def select_csv_file():
    """Let user pick the Spotify CSV file"""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Spotify CSV file",
        filetypes=[("CSV files", "*.csv")]
    )
    root.destroy()
    return file_path

def extract_isrc(isrc_value):
    """Clean and validate ISRC code"""
    if pd.isna(isrc_value):
        return None
    
    isrc = str(isrc_value).strip().upper()
    isrc = re.sub(r'[^A-Z0-9]', '', isrc)
    
    return isrc if len(isrc) == 12 else None

def wait_for_search_results(driver, timeout=15):
    """Wait for search results to load, handle network errors"""
    try:
        # First wait for the search to actually start
        print("  ⏳ Waiting for search to complete...")
        
        # Wait for either results or loading to finish
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'p-4')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'No results') or contains(text(), 'no results') or contains(text(), 'not found')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Network error') or contains(text(), 'network error')]"))
            )
        )
        
        # Check for network error
        if driver.find_elements(By.XPATH, "//*[contains(text(), 'Network error') or contains(text(), 'network error')]"):
            print("  🌐 Network error detected, retrying...")
            return "retry"
        
        # Check which one we got
        if driver.find_elements(By.XPATH, "//div[contains(@class, 'p-4')]"):
            # Wait a bit more for results to fully render
            time.sleep(1.5)
            return "success"
        else:
            print("  📭 No tracks found for this ISRC")
            return "no_results"
        
    except TimeoutException:
        print("  ⏰ Search timed out")
        return "timeout"

def find_matching_track(driver):
    """Find the first valid track in search results"""
    max_retries = 2
    for attempt in range(max_retries):
        result = wait_for_search_results(driver)
        
        if result == "retry":
            if attempt < max_retries - 1:
                print("  🔄 Retrying search due to network error...")
                time.sleep(2)
                continue
            else:
                return None
        elif result == "no_results" or result == "timeout":
            return None
        elif result == "success":
            break
    
    if result != "success":
        return None
    
    try:
        # Get fresh references to results
        results = driver.find_elements(By.XPATH, "//div[contains(@class, 'p-4')]")
        if not results:
            return None
        
        # Use the first result
        result = results[0]
        
        # Extract track info
        track_name = "Unknown"
        artist_name = "Unknown"
        
        # Get track name | try multiple selectors
        selectors = [
            ".//h3[contains(@class, 'font-medium')]",
            ".//h2",
            ".//h1", 
            ".//div[contains(@class, 'text-lg')]",
            ".//div[contains(@class, 'font-bold')]"
        ]
        
        for selector in selectors:
            try:
                elements = result.find_elements(By.XPATH, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 1:
                        track_name = text
                        break
                if track_name != "Unknown":
                    break
            except:
                continue
        
        # Get artist name
        try:
            # Look for artist text
            all_text_elements = result.find_elements(By.XPATH, ".//p | .//span | .//div[@class]")
            for elem in all_text_elements:
                text = elem.text.strip()
                if (text and text != track_name and len(text) > 1 and 
                    len(text) < 100 and not text.startswith("Album:")):
                    artist_name = text
                    break
        except:
            pass
        
        if track_name != "Unknown":
            print(f"  ✅ Found: {track_name} - {artist_name}")
            return {
                'track': track_name,
                'artist': artist_name,
                'result_index': 0
            }
        else:
            print("  ❌ Could not extract track info")
            return None
            
    except Exception as e:
        print(f"  ❌ Search error: {e}")
        return None

def click_like_button(driver, result_index, track_name):
    """Click the like button"""
    try:
        # Get fresh result reference
        results = driver.find_elements(By.XPATH, "//div[contains(@class, 'p-4')]")
        if not results or len(results) <= result_index:
            return False
        
        result = results[result_index]
        
        # Look for like button with heart icon
        like_buttons = result.find_elements(By.XPATH, ".//button[.//*[name()='svg']]")
        
        for button in like_buttons:
            try:
                svg = button.find_element(By.XPATH, ".//*[name()='svg']")
                svg_html = svg.get_attribute('outerHTML')
                if 'heart' in svg_html.lower() or 'lucide-heart' in svg_html:
                    svg_class = svg.get_attribute("class") or ""
                    
                    if "fill-red" in svg_class:
                        print(f"  💖 Already liked: {track_name}")
                        return True
                    else:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)  # Wait for like to register
                        print(f"  💖 Liked: {track_name}")
                        return True
            except StaleElementReferenceException:
                continue
        
        print(f"  ❌ No like button found: {track_name}")
        return False
        
    except Exception as e:
        print(f"  ❌ Like error: {e}")
        return False

def main():
    try:
        print("Starting SpotiDAB...")
        print("Opening Firefox...")
        driver = webdriver.Firefox()
        driver.get("https://dab.yeet.su/login")

        print("\nPlease log into DAB now")
        print("Press ENTER after you're logged in...")
        input()

        print("\nSelect your Spotify CSV file...")
        csv_file = select_csv_file()
        
        if not csv_file:
            print("No file selected. Exiting.")
            driver.quit()
            return

        # Load and validate CSV
        df = pd.read_csv(csv_file)
        print(f"Loaded CSV with {len(df)} songs")
        
        if "ISRC" not in df.columns:
            print("CSV missing ISRC column. Please export from Exportify.app with ISRC codes.")
            driver.quit()
            return

        # ISRC cleanup
        valid_tracks = []
        for index, row in df.iterrows():
            isrc = extract_isrc(row.get("ISRC"))
            if isrc:
                track = row.get("Track Name", "Unknown")
                artist = row.get("Artist Name(s)", "Unknown")
                valid_tracks.append({
                    'isrc': isrc,
                    'track': track,
                    'artist': artist
                })

        print(f"\nFound {len(valid_tracks)} songs with valid ISRC codes")
        print("Starting the like party! 🎉")
        print("=" * 50)
        
        liked_count = 0
        not_found = []
        
        for i, item in enumerate(valid_tracks):
            print(f"\n{i+1}/{len(valid_tracks)}: {item['track']} - {item['artist']}")
            print(f"  ISRC: {item['isrc']}")
            
            try:
                # Search by ISRC
                search_field = driver.find_element(By.XPATH, "//input[@placeholder='Search for songs, artists, or albums...']")
                search_field.clear()
                search_field.send_keys(item['isrc'])
                search_field.send_keys(Keys.RETURN)
                
                # Wait longer for search to complete
                time.sleep(3)
                
                # Find and like track
                match = find_matching_track(driver)
                
                if match:
                    if click_like_button(driver, match['result_index'], match['track']):
                        liked_count += 1
                else:
                    print(f"  ❌ Track not found in DAB database")
                    not_found.append(f"{item['track']} - {item['artist']} (ISRC: {item['isrc']})")
                
                # Return to homepage with longer wait
                print("  ↪️ Returning to homepage...")
                driver.get("https://dab.yeet.su")
                time.sleep(2)
                
            except Exception as e:
                print(f"  ❌ Error processing track: {e}")
                try:
                    driver.get("https://dab.yeet.su")
                    time.sleep(3)
                except:
                    print("  💥 Browser crashed, stopping...")
                    break

        print("\n" + "=" * 50)
        print("ALL DONE! 🎵")
        print(f"Successfully liked: {liked_count}/{len(valid_tracks)} songs")
        
        if not_found:
            print(f"\nCouldn't find {len(not_found)} songs in DAB database:")
            for track in not_found[:10]:
                print(f"  {track}")

    except Exception as e:
        print(f"Oops, something went wrong: {e}")

    finally:
        print("\nPress ENTER to close the browser...")
        input()
        driver.quit()

if __name__ == "__main__":
    main()
