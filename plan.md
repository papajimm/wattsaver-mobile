# Android App Development Plan (WattSaver - Flet)

We will convert the existing `customtkinter` (Tkinter) application to **Flet**, which allows us to build a responsive app for Android (and Desktop/Web) using Python.

## 1. Setup Environment
- Create a new directory `wattsaver_mobile`.
- Copy logic files: `bill_parser.py` and `scraper.py` into the new directory.
- Create a `assets` folder for local data (`providers.json`) if needed.

## 2. Refactor Core Logic
- **`bill_parser.py`**:
  - `PyMuPDF` (`fitz`) works on Android, but we need to ensure the file path handling works with Android's content URI system if we pick files.
  - *Constraint*: Android file picking returns a URI, not a direct path. We might need to copy the file to a temp cache to read it with standard file I/O.
- **`scraper.py`**:
  - **Major Challenge**: `selenium` + `chromedriver` **DOES NOT WORK on Android**.
  - **Solution**: We must replace the Selenium scraper with `requests` + `BeautifulSoup` if the site is static, or just use the Flet app to display a "WebView" if scraping is too complex to port.
  - *Alternative*: Since the scraper runs on `energycost.gr`, we need to check if we can fetch the data with simple HTTP requests. If the site relies heavily on JS to render tables (which the Selenium usage implies), we might need a different approach or run the scraping on a backend server.
  - **Decision for MVP**: We will try to replace Selenium with `requests`. If that fails, we will mock the data or disable the "Live Update" feature for the mobile version initially, or use a Flet `WebView` to let the user browse the site manually.
  - *Correction*: The user wants to "compile" the existing app. I will try to rewrite the scraper using `requests` if possible, otherwise I will mark it as a limitation. **Wait!** The logs show `energycost.gr`. I will check if I can just `curl` the page to see if data is in HTML.

## 3. Rewrite UI (Flet)
- Create `main.py` (entry point).
- Re-implement the layout:
  - **Tabs**: `ft.Tabs` for "Electricity" and "Gas".
  - **File Picker**: `ft.FilePicker` for uploading PDF bills.
  - **Sliders**: `ft.Slider` for kWh consumption.
  - **Data Table**: `ft.DataTable` or `ft.ListView` to show the list of providers.
  - **State Management**: Use Flet's state handling to update the UI when sliders move.

## 4. Build & Compile
- We will use `flet build apk` (requires Flet setup).
- *Note*: I cannot run the actual `flet build apk` command here because it requires the Android SDK/NDK installed and configured on the host machine, which I cannot guarantee or set up easily in this environment.
- **Deliverable**: I will provide the complete **source code** that allows the user to run `flet run` (to test on desktop) and instructions on how to run `flet build apk` on their own machine.

## 5. Specific Selenium Issue
- I will verify if `scraper.py` can be converted to `requests`.
- **Action**: I will try to `curl` the URL `https://energycost.gr/...` to see if the table is in the HTML.

## Plan Summary
1. Create `wattsaver_mobile/` folder.
2. Check `energycost.gr` accessibility.
3. Adapt `scraper.py` (attempt to remove Selenium).
4. Adapt `bill_parser.py` (file handling).
5. Write `main.py` (Flet UI).
6. Create `requirements.txt`.
7. Provide instructions for building APK.
