# CloudFlow

CloudFlow is an intelligent cloud storage and workspace application built with Vue 3 and Flask.

## Features

- File uploads, folders, favorites, sharing, and a recycle bin.
- AI-assisted file analysis and background tasks.
- Personal workspace tools and an administration dashboard.

## Project structure

```text
cloudflow/
  admin/             Vue frontend
  backend/           Flask API and local application data
  requirements.txt   Python dependencies
```

## Development

Use Node.js 20.19+ or 22.12+ and a Python environment with the project dependencies installed.

```sh
cd cloudflow/admin
npm ci
npm run dev
```

In a separate terminal from the repository root:

```sh
cd cloudflow
python -m pip install -r requirements.txt
cd backend
python app.py
```

Configure external AI services using environment variables or `cloudflow/backend/.env`. Do not commit credentials or local application data.

## Frontend build

```sh
cd cloudflow/admin
npm run build
```

The Flask application serves the generated frontend from `admin/dist` on port 8080. Its health endpoint is `/api/health`.

Existing database filenames are retained for compatibility with local data.
