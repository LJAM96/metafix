# MetaFix

**MetaFix** is a comprehensive Plex library management tool designed to fix artwork issues and manage edition metadata automatically.

## Features

### 🎨 Artwork Scanner & Fixer
- **Scan** your Plex libraries for missing posters, backgrounds, and logos.
- **Detect** unmatched items and "placeholder" artwork (e.g., horizontal screenshots used as posters).
- **Aggregate** high-quality artwork from multiple providers:
  - **Fanart.tv** (HD Logos, Clearart)
  - **The Movie Database (TMDB)**
  - **The TVDB (v4)**
  - **Mediux** (Community sets)
- **Review** issues in a clean UI and apply fixes with one click.
- **Auto-Fix** capability to automatically apply the best available artwork.

### 🎬 Edition Manager
- **Generate** rich edition metadata for your movies (e.g., "4K · Dolby Vision · Director's Cut").
- **22 Modules** available including Resolution, HDR, Audio Codec, Cut, Source, and more.
- **Customizable** order and formatting.
- **Backup** existing edition tags before modifying.

### 📅 Scheduling & Automation
- **Schedule** periodic scans using Cron expressions.
- **Auto-Commit** fixes found during scheduled scans.
- **Background Processing** ensuring scans continue even if you close the browser.

## Installation

### Docker (Recommended)

1. Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  metafix:
    image: metafix:latest
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
    environment:
      - SECRET_KEY=your_secret_key_here
    restart: unless-stopped
```

2. Run the container:
```bash
docker-compose up -d
```

3. Open http://localhost:3000

### Manual Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run build
npm start
```

## Getting Started

1. **Onboarding:** When you first open MetaFix, you'll be guided to connect your Plex server.
2. **Settings:** Go to `/settings` to configure metadata providers (Fanart.tv, TMDB, etc.). Adding API keys improves results significantly.
3. **Scan:** Go to `/scan` to start your first analysis. You can choose to scan for Artwork issues, Edition metadata, or both.
4. **Review:** Visit `/issues` to see what was found. Use "Auto-Fix All" or manually select the best artwork.
5. **Editions:** Visit `/edition` to configure how movie editions are named.

## Project Structure

- `backend/`: FastAPI Python application
- `frontend/`: Next.js 14 React application
- `data/`: SQLite database storage

## License

MIT License
