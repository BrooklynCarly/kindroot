# Resources Page Setup Guide

This document explains how to set up and use the Resources Page system for KindRoot.

## Overview

The Resources Page system allows admins to manage parent support resources through an admin interface, which are then displayed on the consumer-facing website. The system includes:

- **Backend API**: SQLite database with full CRUD operations
- **Admin Frontend**: Resource management interface (port 3000)
- **Consumer Frontend**: Public-facing resources page (port 3001)

## Features

### Admin Features
- ✅ Create, edit, and delete resources
- ✅ Add categories and tags
- ✅ Upload thumbnails
- ✅ Mark resources as featured
- ✅ Duplicate existing resources
- ✅ Check links for validity (individual or bulk)
- ✅ Search and filter resources
- ✅ View analytics (view count)

### Consumer Features
- ✅ Browse resources by category
- ✅ Search resources by keyword
- ✅ Filter by tags
- ✅ View resource details
- ✅ See related resources
- ✅ Featured resources on homepage
- ✅ Pagination
- ✅ Mobile-responsive design
- ✅ Breadcrumb navigation

## Setup Instructions

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Initialize Database
```bash
# From the backend directory
python -m app.init_db
```

This will create:
- SQLite database at `backend/app/data/resources.db`
- Default categories (Early Intervention, Therapy Services, etc.)

#### Start Backend Server
```bash
# From the backend directory
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Admin Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

This will install:
- react-router-dom for routing
- All existing dependencies

#### Start Admin Frontend
```bash
npm run dev
# Runs on http://localhost:3000
```

Navigate to `/resources` to access the resource management interface.

### 3. Consumer Frontend Setup

#### Install Dependencies
```bash
cd consumer_frontend
npm install
```

This will install:
- react-router-dom for routing
- All existing dependencies

#### Start Consumer Frontend
```bash
npm run dev
# Runs on http://localhost:3001
```

## API Endpoints

### Public Endpoints (No Auth Required)

- `GET /api/resources` - List resources with filtering
  - Query params: `page`, `page_size`, `category`, `search`, `tags`, `featured_only`
- `GET /api/resources/{id}` - Get single resource (increments view count)
- `GET /api/resources/{id}/related` - Get related resources
- `GET /api/resources/categories/list` - Get all categories
- `GET /api/resources/tags/list` - Get all tags

### Admin Endpoints (Auth Required)

- `POST /api/resources` - Create resource
- `PUT /api/resources/{id}` - Update resource
- `DELETE /api/resources/{id}` - Delete resource
- `POST /api/resources/{id}/duplicate` - Duplicate resource
- `POST /api/resources/{id}/check-link` - Check single link
- `POST /api/resources/check-all-links` - Check all links
- `POST /api/resources/categories` - Create category
- `GET /api/resources/categories` - List categories (admin)

## Resource Schema

Each resource includes:

```typescript
{
  id: number
  title: string
  category: string
  short_description: string  // Max 500 chars
  long_description: string
  link: string               // URL to the resource
  thumbnail?: string         // Optional image URL
  is_featured: boolean
  tags: Tag[]
  view_count: number
  link_status: 'unchecked' | 'working' | 'broken'
  last_checked?: datetime
  created_at: datetime
  updated_at: datetime
}
```

## Default Categories

The system comes with these pre-configured categories:
- Early Intervention
- Therapy Services
- Educational Resources
- Support Groups
- Financial Assistance
- Medical Resources
- Legal Resources
- Community Activities

## Usage Guide

### Adding a Resource (Admin)

1. Log in to admin frontend (http://localhost:3000)
2. Navigate to Resources page
3. Click "Add Resource"
4. Fill in:
   - Title
   - Category (select from dropdown)
   - Short description (for cards)
   - Long description (for detail page)
   - Link (URL to the resource)
   - Thumbnail URL (optional)
   - Tags (add multiple by typing and pressing Enter)
   - Featured checkbox (to show on homepage)
5. Click "Create Resource"

### Editing a Resource

1. Find the resource in the list
2. Click "Edit"
3. Make changes
4. Click "Update Resource"

### Checking Links

- **Single Link**: Click "Check" next to any resource
- **All Links**: Click "Check All Links" button at the top

### Duplicating a Resource

Useful for creating similar resources:
1. Click "Duplicate" on an existing resource
2. Edit the duplicated resource
3. Update title and other fields as needed

## Consumer Frontend Routes

- `/` - Homepage with featured resources
- `/resources` - Browse all resources
- `/resources/:id` - Resource detail page

## Customization

### Colors

The consumer frontend uses the KindRoot color palette:
- Primary: `#4A7C59` (warm natural green)
- Accent: `#E8956B` (warm coral/peach)

### Adding Categories

Categories can be added via the admin interface or directly in the database:

```python
from app.database import SessionLocal
from app.models import Category

db = SessionLocal()
category = Category(name="New Category", description="Description")
db.add(category)
db.commit()
```

## Troubleshooting

### Database Issues

If you need to reset the database:
```bash
rm backend/app/data/resources.db
python -m app.init_db
```

### TypeScript Errors

If you see import errors after adding files:
```bash
npm install  # Ensures all dependencies are installed
```

### CORS Issues

The backend is configured to allow:
- http://localhost:3000 (admin frontend)
- http://localhost:3001 (consumer frontend)

Additional origins can be added in `backend/app/main.py`.

## Production Deployment

### Backend
1. Set environment variable for production database if needed
2. Run migrations if using PostgreSQL instead of SQLite
3. Configure CORS for production URLs

### Frontend
1. Update `VITE_API_URL` environment variable to production backend URL
2. Run `npm run build`
3. Deploy the `dist` folder to your hosting service

## Next Steps

1. Add sample resources to populate the database
2. Test the link checker functionality
3. Customize categories for your specific needs
4. Add resource thumbnails for better visual appeal
5. Set featured resources to appear on homepage

## Support

For issues or questions, refer to the main project README or contact the development team.
