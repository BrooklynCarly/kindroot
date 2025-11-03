# KindRoot Frontend

Modern React application for viewing patient records and generating comprehensive reports.

## Features

- **Patient List View**: Display all patient entries from Google Sheets
- **Report Generation**: One-click report generation with real-time status
- **Google Docs Integration**: Generated reports open directly in Google Docs
- **Modern UI**: Built with React, TypeScript, and TailwindCSS

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will run on `http://localhost:3000` and proxy API requests to the backend at `http://localhost:8000`.

## Architecture

- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **TailwindCSS** for modern, responsive styling
- **Lucide React** for beautiful icons

## API Integration

The frontend connects to the following backend endpoints:

- `GET /api/patients` - Fetch all patient records
- `POST /api/generate-report/{row}` - Generate a comprehensive report for a patient

## Development

The app uses Vite's proxy feature to forward `/api/*` requests to the backend server, avoiding CORS issues during development.
