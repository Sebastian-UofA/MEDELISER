# Meter Excel Processor

## Quick Start

### Option 1: Automatic Setup (Recommended)
1. Double-click `install_deps.py` or run:
   ```bash
   python3 install_deps.py
   ```

### Option 2: Manual Setup
1. Install Python 3.8+ if not already installed
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run streamdep.py
   ```

### Option 3: One-Command Setup
```bash
pip3 install -r requirements.txt && streamlit run streamdep.py
```

## What it does
- Processes Excel files with multiple sheets
- Splits datetime columns
- Limits meter readings to 7 per day
- Separates gateway and walkby data
- Generates processed Excel with multiple sheets

## Requirements
- Python 3.8+
- Internet connection for first-time dependency installation
