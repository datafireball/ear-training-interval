# Ear Training Exercise Generator

A Flask web application for generating ear training exercises by stitching together guitar note samples with TTS spoken prompts.

## Quick Start

This package is ready to deploy to Render.

### Deploy to Render

1. Push this directory to a GitHub repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" -> "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect the render.yaml or Procfile
6. The app will be available at your Render URL

### Manual Configuration (if needed)

- Build Command: pip install -r requirements.txt
- Start Command: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
- Environment: Python 3

### Environment Variables (Optional)

- SECRET_KEY: Flask secret key (auto-generated if using render.yaml)
- FLASK_ENV: Set to production
- PORT: Automatically set by Render

### Features

- Generate ear training exercises with customizable parameters
- Take tests directly in the browser
- Download audio files, answer sheets, and scripts
- Minimal dataset (~7.24 MB) for fast deployment

### Requirements

- Python 3.8+
- ffmpeg (optional, for MP3 export - falls back to WAV if not available)

### Dataset

The data/ folder contains 43 audio files (one per note) totaling ~7.24 MB.

### License

This project is provided as-is for educational purposes.
