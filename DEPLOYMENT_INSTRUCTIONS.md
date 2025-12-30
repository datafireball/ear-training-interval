# Deployment Instructions for Render

This directory contains everything needed to deploy the Ear Training Exercise Generator to Render.

## Quick Deploy Steps

### 1. Push to GitHub

```bash
cd deployed
git init
git add .
git commit -m "Initial deployment package"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub account and select the repository
4. Render will automatically detect the configuration:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
   - **Environment:** Python 3

### 3. Environment Variables (Optional)

Render will automatically:
- Set `PORT` environment variable
- Generate `SECRET_KEY` if using `render.yaml`

You can manually add in Render dashboard:
- `FLASK_ENV=production`
- `SECRET_KEY=<your-secret-key>` (if not using render.yaml)

### 4. Wait for Deployment

Render will:
1. Install dependencies from `requirements.txt`
2. Start the app using gunicorn
3. Provide you with a public URL

## File Structure

```
deployed/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Render start command (alternative to render.yaml)
├── render.yaml        # Render configuration file
├── README.md          # Project documentation
├── .gitignore         # Git ignore rules
├── data/              # Audio dataset (43 files, ~7.24 MB)
│   ├── A2/
│   ├── A3/
│   └── ...
├── templates/         # HTML templates
│   ├── index.html
│   ├── test.html
│   └── error.html
└── static/            # CSS and static files
    └── css/
        └── style.css
```

## Configuration Files

### Procfile
Simple start command for Render:
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

### render.yaml
More detailed configuration with environment variables:
- Auto-generates SECRET_KEY
- Sets FLASK_ENV to production
- Configures build and start commands

## Troubleshooting

### Build Fails
- Check that all files are committed to GitHub
- Verify `requirements.txt` is correct
- Check Render build logs for specific errors

### App Won't Start
- Verify gunicorn is in requirements.txt
- Check that PORT environment variable is set (Render does this automatically)
- Review Render logs for startup errors

### Dataset Not Found
- Ensure `data/` folder is committed to Git
- Check that files are actually in the folder (not just empty directories)
- Verify file paths in app.py match the folder structure

### MP3 Export Not Working
- Install ffmpeg in build command (add to render.yaml):
  ```yaml
  buildCommand: |
    apt-get update && apt-get install -y ffmpeg
    pip install -r requirements.txt
  ```
- Or the app will automatically fall back to WAV format

## Size Information

- **Total package size:** ~7.29 MB
- **Dataset size:** ~7.24 MB (43 audio files)
- **Code size:** ~50 KB

This is well within GitHub and Render limits.

## Support

If you encounter issues:
1. Check Render build/deploy logs
2. Verify all files are in the repository
3. Test locally first: `python app.py`
4. Check that Python version matches (3.8+)


