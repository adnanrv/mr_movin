# MR. MOVIN (Apartment Relocation Assistant)

This project is a **simple, laptop-friendly chatbot** that helps users explore and compare U.S. metro areas
based on Zillow Home Value Index (ZHVI) data. It uses the cleaned Zillow dataset included in `data/` and
exposes a chat interface via **Gradio**.

## Features

TODO
---

## Setup Instructions

### Prerequisites

- Python 3.9+ installed
- `pip` available

### Step 1 — Create & activate a virtual environment (optional)

```bash
cd mr_movin

# Create venv (Mac/Linux)
python -m venv .venv
source .venv/bin/activate

# On Windows
# python -m venv .venv
# .venv\Scripts\Activate.ps1
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Run the demo app

```bash
python app.py
```

Gradio will print a **local URL** in the terminal (e.g. `http://127.0.0.1:7860`). Open it in your browser.
