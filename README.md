# SpotiDAB

Automatically transfer your Spotify listening history to DAB. Upload your Spotify CSV export from [Exportify](https://exportify.app/) and SpotiDAB will search for each track on DAB and like the matching songs.

### How fast is it? 
It will take around 7 Seconds per Track, or 11 Mintutes per 100 Tracks or 1 hour 56 Minutes per 1000 Tracks.

**I Know** that this is not exactly instant but keep it running in the background and it will snyc your tracks without any issues. **I am working on a new version that will use the DAB API to automatically Sync your CSV in an instant.**
## Quick Start

```bash
# Clone the repository
git clone https://github.com/ULTRA-VAGUE/SpotiDAB
cd SpotiDAB

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download Firefox if not installed
https://www.mozilla.org/firefox/

# Get your Spotify Playlists as .csv from Exportify
https://exportify.app/

# Run SpotiDAB
python spotidab.py
```

## What Happens Next

1. Firefox opens to the DAB login page
2. You log in manually
3. A file dialog appears for CSV selection
4. Automatic searching and liking begins
5. Progress and summary are displayed when complete

## Requirements

- Python 3.8+
- Firefox browser
- Spotify CSV export from [Exportify](https://exportify.app/)


## Troubleshooting

**Windows:**
- Ensure Firefox is installed
- Run Command Prompt as Admin if needed
- Check if Python is in PATH

**Linux:**
- Use `python3` command if `python` doesn't work
- Install tkinter if file dialog fails:
  ```bash
  sudo apt install python3-tk
  ```
- Install geckodriver if WebDriver errors occur:
  ```bash
  sudo apt install firefox-geckodriver
  ```

**Common Issues:**
- Verify CSV has `Track Name` and `Artist Name(s)` columns
- Check internet connection
- Confirm DAB login works
- Ensure virtual environment is activated

---

*Use responsibly according to DAB's terms of service.*
