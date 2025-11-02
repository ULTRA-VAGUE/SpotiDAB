from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, NoSuchElementException
import pandas as pd
import re
import time
import tkinter as tk
from tkinter import filedialog

def select_csv_file():
    """Open file dialog to pick CSV file"""
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Select Spotify CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    root.destroy()
    return file_path

def clean_text(text):
    """Clean up text for searching"""
    if pd.isna(text):
        return ""
    
    text = str(text)
    text = text.replace(';', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def normalize_string(s):
    """Make strings comparable for matching"""
    if pd.isna(s):
        return ""
    
    s = str(s)
    s = s.lower()
    s = s.replace('&', ' ')
    s = s.replace(';', ' ')
    s = s.replace(',', ' ')
    s = s.replace(' feat ', ' ')
    s = s.replace(' ft ', ' ')
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s

def find_with_retry(element, by, value, retries=3):
    """Try to find element multiple times if page is slow"""
    for attempt in range(retries):
        try:
            return element.find_element(by, value)
        except NoSuchElementException:
            if attempt == retries - 1:
                raise
            time.sleep(1)
    return None

def find_matching_track(driver, search_track, search_artist):
    """Look through results to find the right track"""
    try:
        time.sleep(2)
        
        search_track_norm = normalize_string(search_track)
        search_artist_norm = normalize_string(search_artist)
        
        print(f"  Looking for: '{search_track_norm}' by '{search_artist_norm}'")
        
        try:
            results = driver.find_elements(By.XPATH, "//div[contains(@class, 'p-4')]")
            print(f"  Found {len(results)} results")
        except NoSuchElementException:
            print("  No results found")
            return None
        
        matches = []
        
        for i, result in enumerate(results):
            try:
                track_element = find_with_retry(result, By.XPATH, ".//h3[contains(@class, 'font-medium')]")
                result_track = track_element.text if track_element else "Unknown"
                
                result_artist = "Unknown"
                try:
                    p_elements = result.find_elements(By.XPATH, ".//p[contains(@class, 'text-emerald-400') or contains(@class, 'text-white')]")
                    for p in p_elements:
                        text = p.text
                        if text and not text.startswith("Album:") and len(text) > 2:
                            result_artist = text
                            break
                except:
                    pass
                
                result_track_norm = normalize_string(result_track)
                result_artist_norm = normalize_string(result_artist)
                
                track_match = search_track_norm in result_track_norm or result_track_norm in search_track_norm
                artist_match = (search_artist_norm in result_artist_norm or 
                               result_artist_norm in search_artist_norm or
                               any(word in result_artist_norm for word in search_artist_norm.split()))
                
                if track_match and artist_match:
                    confidence = len(search_track_norm) / len(result_track_norm) if result_track_norm else 0
                    matches.append({
                        'track': result_track,
                        'artist': result_artist,
                        'element': result,
                        'confidence': confidence
                    })
                    print(f"  Possible match: {result_track} - {result_artist}")
                
            except Exception as e:
                continue
        
        if matches:
            best_match = max(matches, key=lambda x: x['confidence'])
            print(f"  Best match: {best_match['track']} - {best_match['artist']}")
            return best_match
        else:
            print("  No matching track found")
            return None
            
    except Exception as e:
        print(f"  Search error: {e}")
        return None

def click_like_button(driver, result_element, track_name):
    """Click the like button, only show what worked"""
    try:
        time.sleep(1)
        
        # Try direct container search first
        try:
            track_container = find_with_retry(result_element, By.XPATH, ".//div[contains(@class, 'flex items-center gap-2')]")
            like_button = find_with_retry(track_container, By.XPATH, ".//button[.//svg[contains(@class, 'lucide-heart')]]")
            
            svg_element = find_with_retry(like_button, By.XPATH, ".//svg")
            svg_class = svg_element.get_attribute("class")
            
            if "fill-red-400" in svg_class:
                print(f"  Already liked: {track_name}")
                return True
            else:
                like_button.click()
                time.sleep(1)
                print(f"  Liked: {track_name}")
                return True
        except:
            pass
        
        # Try aria-label search
        try:
            like_buttons = result_element.find_elements(By.XPATH, ".//button[@aria-label='Add to favorites']")
            if like_buttons:
                svg_element = like_buttons[0].find_element(By.XPATH, ".//svg")
                svg_class = svg_element.get_attribute("class")
                
                if "fill-red-400" in svg_class:
                    print(f"  Already liked: {track_name}")
                    return True
                else:
                    like_buttons[0].click()
                    time.sleep(1)
                    print(f"  Liked: {track_name}")
                    return True
        except:
            pass
        
        # Last resort: JavaScript click
        try:
            like_buttons = result_element.find_elements(By.XPATH, ".//button[.//*[name()='svg']]")
            for button in like_buttons:
                svg = button.find_element(By.XPATH, ".//*[name()='svg']")
                svg_html = svg.get_attribute('outerHTML')
                if 'lucide-heart' in svg_html:
                    svg_class = svg.get_attribute("class")
                    
                    if "fill-red-400" in svg_class:
                        print(f"  Already liked: {track_name}")
                        return True
                    else:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        print(f"  Liked: {track_name}")
                        return True
        except:
            pass
        
        print(f"  Could not like: {track_name}")
        return False
        
    except Exception as e:
        print(f"  Like error: {e}")
        return False

def check_driver_connection(driver):
    """Check if browser connection is still working"""
    try:
        driver.current_url
        return True
    except WebDriverException:
        return False

def validate_csv_columns(df):
    """Make sure CSV has the right columns"""
    required_columns = ["Track Name", "Artist Name(s)"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"Missing columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")
        return False
    
    return True

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

        try:
            df = pd.read_csv(csv_file)
            print(f"Loaded CSV: {len(df)} songs found")
            
            if not validate_csv_columns(df):
                print("Wrong CSV format. Please check your file.")
                driver.quit()
                return
                
        except pd.errors.EmptyDataError:
            print("CSV file is empty")
            driver.quit()
            return
        except pd.errors.ParserError:
            print("Could not read CSV file")
            driver.quit()
            return
        except Exception as e:
            print(f"Error loading CSV: {e}")
            driver.quit()
            return

        print(f"\nStarting SpotiDAB for {len(df)} songs...")
        print("=" * 50)
        
        found_tracks = []
        not_found = []
        liked_tracks = []
        
        start_index = 0
        
        for index, row in df.iloc[start_index:].iterrows():
            if not check_driver_connection(driver):
                print("Browser connection lost! Restart SpotiDAB.")
                break
                
            track = clean_text(row["Track Name"])
            artist = clean_text(row["Artist Name(s)"])
            
            if track and artist:
                search_term = f"{track} {artist}"
                print(f"\n{index+1}/{len(df)}: {search_term}")
                
                try:
                    search_field = driver.find_element(By.XPATH, "//input[@placeholder='Search for songs, artists, or albums...']")
                    search_field.clear()
                    search_field.send_keys(search_term)
                    search_field.send_keys(Keys.RETURN)
                    
                    time.sleep(3)
                    
                    match = find_matching_track(driver, track, artist)
                    
                    if match:
                        found_tracks.append({
                            'original_track': track,
                            'original_artist': artist,
                            'found_track': match['track'],
                            'found_artist': match['artist']
                        })
                        
                        if click_like_button(driver, match['element'], match['track']):
                            liked_tracks.append(f"{match['track']} - {match['artist']}")
                        
                    else:
                        not_found.append(f"{track} - {artist}")
                    
                    print("  Returning to homepage...")
                    driver.get("https://dab.yeet.su")
                    time.sleep(2)
                    
                except WebDriverException as e:
                    print(f"  Browser error: {e}")
                    try:
                        driver.get("https://dab.yeet.su")
                        time.sleep(2)
                    except:
                        break
                except Exception as e:
                    print(f"  Error: {e}")
                    try:
                        driver.get("https://dab.yeet.su")
                        time.sleep(2)
                    except:
                        pass
        
        print("\n" + "=" * 50)
        print("SPOTIDAB RESULTS:")
        print(f"Found tracks: {len(found_tracks)}/{len(df)}")
        print(f"Liked tracks: {len(liked_tracks)}")
        print(f"Not found: {len(not_found)}")
        
        if liked_tracks:
            print("\nLiked tracks:")
            for track in liked_tracks[:10]:
                print(f"  {track}")
        
        if not_found:
            print(f"\nNot found (first 10):")
            for track in not_found[:10]:
                print(f"  {track}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        print("\nPress ENTER to exit...")
        try:
            input()
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()