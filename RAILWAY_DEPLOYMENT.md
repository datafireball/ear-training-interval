# Railway Deployment Guide

This guide explains how to deploy the Ear Training Exercise Generator to Railway using Docker.

## Prerequisites

- Docker installed locally (for testing)
- Railway account
- GitHub repository with the `deployed/` directory

## Deployment Methods

### Method 1: Deploy from GitHub (Recommended)

1. **Push to GitHub:**
   ```bash
   cd deployed
   git add .
   git commit -m "Add Docker configuration for Railway"
   git push
   ```

2. **Create Railway Project:**
   - Go to [Railway](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect the Dockerfile

3. **Configure Service:**
   - Railway will automatically detect the Dockerfile
   - The app will build and deploy automatically
   - Set environment variables if needed (SECRET_KEY, etc.)

4. **Generate Domain:**
   - Go to Settings → Networking
   - Click "Generate Domain" to get a public URL

### Method 2: Deploy via Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Project:**
   ```bash
   cd deployed
   railway init
   ```

3. **Deploy:**
   ```bash
   railway up
   ```

### Method 3: Deploy Docker Image Directly

1. **Build Docker Image:**
   ```bash
   cd deployed
   docker build -t ear-training-app .
   ```

2. **Test Locally:**
   ```bash
   docker run -p 5000:5000 -e PORT=5000 ear-training-app
   ```

3. **Push to Railway:**
   - Use Railway's Docker registry or connect via CLI

## Docker Image Details

- **Base Image:** Python 3.13-slim
- **System Dependencies:** ffmpeg (for audio processing)
- **Python Dependencies:** See requirements.txt
- **Port:** Uses PORT environment variable (Railway sets this automatically)
- **Worker Processes:** 4 gunicorn workers

## Environment Variables

Optional environment variables you can set in Railway:

- `SECRET_KEY`: Flask secret key (auto-generated if not set)
- `FLASK_ENV`: Set to `production` (default in Dockerfile)
- `PORT`: Automatically set by Railway

## File Structure

```
deployed/
├── Dockerfile              # Docker configuration
├── .dockerignore          # Files to exclude from Docker build
├── railway.json           # Railway-specific config (optional)
├── requirements.txt       # Python dependencies
├── app.py                 # Flask application
├── data/                  # Audio dataset
├── templates/             # HTML templates
└── static/                # CSS and static files
```

## Testing Locally

Before deploying, test the Docker image locally:

```bash
# Build the image
docker build -t ear-training-app .

# Run the container
docker run -p 5000:5000 -e PORT=5000 ear-training-app

# Test in browser
# Open http://localhost:5000
```

## Troubleshooting

### Build Fails
- Check Dockerfile syntax
- Verify all files are in the correct location
- Check that requirements.txt is valid

### App Won't Start
- Check Railway logs for errors
- Verify PORT environment variable is set
- Check that gunicorn is in requirements.txt

### Audio Processing Fails
- Verify ffmpeg is installed (check Dockerfile)
- Check that data/ directory is included in Docker image
- Review app logs for specific errors

## Differences from Render

- Uses Docker instead of build commands
- More control over the environment
- Better for complex dependencies
- Easier to test locally before deploying

## Next Steps

After deployment:
1. Test the application at your Railway URL
2. Set up custom domain if needed
3. Configure environment variables
4. Monitor logs for any issues

