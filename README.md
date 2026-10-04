# Flow Automator

A local web-based automation tool that reliably processes a list of image generation prompts for Google Flow.

## Features
- **Web Interface**: Simple Flask-based UI to upload text files containing prompts.
- **Global Instructions**: Easily provide a block of global instructions at the top of your prompts file.
- **Intelligent Orchestration**: Sequentially processes each prompt without skipping. Uses Playwright for robust browser automation and intelligent UI-state detection to wait for image generation to complete before proceeding.
- **Headless & Headed Browser Modes**: Configurable via Playwright.

## Prerequisites
- Python 3.8+
- [Playwright](https://playwright.dev/python/) `playwright install`

## Installation
1. Clone this repository (or copy the files).
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browser binaries:
   ```bash
   playwright install
   ```

## Usage
1. Start the Flask application:
   ```bash
   python app.py
   ```
2. Open your browser and navigate to `http://localhost:8000`.
3. Upload a text file with your prompts. Make sure your global instructions are at the top, separated by two empty lines from the rest of the prompts.
4. Click **Start Automation** and watch your terminal/command prompt to monitor the live progress.

## How the Prompts File works
The `.txt` file should follow the layout below:
```text
[Global Instructions Go Here]

[Prompt 1]
[Prompt 2]
[Prompt 3]
```

## Structure
- `app.py`: The Flask backend running the web interface.
- `main.py`: The Playwright script responsible for browser automation on Google Flow.
- `requirements.txt`: Python package dependencies.
