# Fonts Directory

This directory contains fonts for Arabic text rendering in the CV Privacy Cleaner.

## Required Fonts for Streamlit Cloud

Download these fonts and place them in this directory:

### 1. Noto Sans Arabic (Recommended)
- Download from: https://fonts.google.com/noto/specimen/Noto+Sans+Arabic
- Files needed:
  - `NotoSansArabic-Regular.ttf`
  - `NotoSansArabic-Bold.ttf`

### 2. Amiri (Alternative)
- Download from: https://fonts.google.com/specimen/Amiri
- Files needed:
  - `Amiri-Regular.ttf`
  - `Amiri-Bold.ttf`

### 3. DejaVu Sans (Fallback)
- Download from: https://dejavu-fonts.github.io/
- File needed:
  - `DejaVuSans.ttf`

## How to Download

### Option 1: Direct Download Links
- Noto Sans Arabic: https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf
- Amiri: https://github.com/alif-type/amiri/releases/download/0.111/Amiri-Regular.ttf
- DejaVu Sans: https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf

### Option 2: Using curl (Linux/Mac)
```bash
cd fonts
curl -L "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf" -o NotoSansArabic-Regular.ttf
curl -L "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Bold.ttf" -o NotoSansArabic-Bold.ttf
curl -L "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf" -o DejaVuSans.ttf
```

### Option 3: Using wget (Linux)
```bash
cd fonts
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Bold.ttf
wget https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf
```

## Why These Fonts?

1. **Noto Sans Arabic**: Google's open-source Arabic font, excellent for modern UI
2. **Amiri**: Classic Arabic Naskh style, good for formal documents
3. **DejaVu Sans**: Universal fallback that works on most Linux systems

## Deployment

When deploying to Streamlit Cloud, ensure this `fonts/` directory is included in your repository. The fonts will be automatically loaded by the application.

## Local Development

On Windows, the application will use system fonts (Arial, Tahoma, Calibri) by default if the project fonts are not found.
