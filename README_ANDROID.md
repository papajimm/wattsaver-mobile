# WattSaver Mobile (Android Version)

This is a port of the WattSaver application to **Flet**, allowing it to run on Android devices.

## Project Structure
- `main.py`: The main application entry point (UI).
- `bill_parser.py`: Logic for reading and parsing PDF bills.
- `assets/`: Contains `providers.json` (database of energy providers).
- `requirements.txt`: Python dependencies.

## Prerequisites
To build the APK, you need a computer with:
1. **Python 3.8+** installed.
2. **Flutter SDK** installed (Flet uses Flutter under the hood).
   - [Install Flutter](https://docs.flutter.dev/get-started/install)
3. **Android Studio** (for Android SDK and NDK).

## How to Run (Desktop Test)
Before compiling, you can run the app on your PC to test the UI:

```bash
cd wattsaver_mobile
pip install -r requirements.txt
flet run main.py
```

## How to Compile to APK (Android)

1. **Install Flet Build Tools**:
   ```bash
   pip install flet
   ```

2. **Build the APK**:
   Run the following command in the `wattsaver_mobile` directory:
   ```bash
   flet build apk
   ```

   *Note: The first time you run this, it might take a while to download the necessary Flutter dependencies.*

3. **Locate the APK**:
   The output file (usually `app-release.apk`) will be in the `build/apk` folder.

4. **Install on Phone**:
   Transfer the `.apk` file to your Android phone and install it.

## Limitations
- **Live Scraping**: The "Live Update" feature from `energycost.gr` is disabled in this version because the original scraper used Selenium, which does not run on Android. This version relies on the local `providers.json` database.
- **File Picking**: On some Android versions, picking a file might require specific permissions. Flet handles most of this, but if the PDF fails to load, ensure the app has storage permissions.
