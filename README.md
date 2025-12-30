# Ear Training Exercise Generator

A Flask web application for generating ear training exercises by stitching together guitar note samples with TTS spoken prompts.

## Quick Start

This package is ready to deploy to Railway using Docker.

### Deploy to Railway

#### Option 1: Deploy from GitHub (Recommended)

1. Push this directory to a GitHub repository
2. Go to [Railway](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect the Dockerfile
6. The app will build and deploy automatically
7. Generate a domain in Settings → Networking

#### Option 2: Deploy via Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and initialize
railway login
railway init

# Deploy
railway up
```

### Test Docker Image Locally

```bash
# Build the image
docker build -t ear-training-app .

# Run the container
docker run -p 5000:5000 -e PORT=5000 ear-training-app

# Open http://localhost:5000
```

### Environment Variables (Optional)

Set these in Railway dashboard if needed:
- `SECRET_KEY`: Flask secret key (auto-generated if not set)
- `FLASK_ENV`: Set to `production` (default in Dockerfile)
- `PORT`: Automatically set by Railway

### Features

- Generate ear training exercises with customizable parameters
- Take tests directly in the browser
- Download audio files, answer sheets, and scripts
- Minimal dataset (~7.24 MB) for fast deployment
- Docker-based deployment for easy portability

### Requirements

- Python 3.13
- ffmpeg (included in Docker image)
- All dependencies listed in requirements.txt

### Dataset

The `data/` folder contains 43 audio files (one per note) totaling ~7.24 MB.

### Docker Details

- **Base Image:** Python 3.13-slim
- **Includes:** ffmpeg, all Python dependencies
- **Port:** Uses PORT environment variable (Railway sets automatically)
- **Workers:** 4 gunicorn workers

### License

This project is provided as-is for educational purposes.
