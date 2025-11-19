# Resources Page - Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Initialize Backend Database
```bash
cd backend
python -m app.init_db
```
✅ Creates SQLite database with 8 default categories

### 2. Install Frontend Dependencies
```bash
# Admin frontend
cd frontend
npm install

# Consumer frontend
cd consumer_frontend
npm install
```
✅ Installs react-router-dom and all dependencies

### 3. Start All Services
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Admin Frontend
cd frontend
npm run dev
# Opens at http://localhost:3000

# Terminal 3: Consumer Frontend
cd consumer_frontend
npm run dev
# Opens at http://localhost:3001
```

## 📍 Access Points

**Admin Interface:** http://localhost:3000/resources
- Create, edit, and manage resources
- Check links, add tags, set featured status

**Consumer Website:** http://localhost:3001/resources
- Browse and search resources
- View resource details
- See related resources

**Featured Resources:** http://localhost:3001
- Homepage shows 3 featured resources

## ✨ Quick Test

1. **Log in** to admin frontend (http://localhost:3000)
2. **Navigate** to Resources page
3. **Click** "Add Resource"
4. **Fill in** sample resource:
   - Title: "Autism Speaks"
   - Category: "Support Groups"
   - Short Description: "Leading autism advocacy organization"
   - Long Description: "Autism Speaks is dedicated to promoting solutions..."
   - Link: "https://www.autismspeaks.org"
   - Tags: autism, support, advocacy
   - Featured: ✓ (checked)
5. **Click** "Create Resource"
6. **Go to** consumer frontend (http://localhost:3001)
7. **Check** homepage shows featured resource
8. **Click** "Resources" or "View All Resources"
9. **Browse** and click on the resource
10. **Verify** detail page shows all information

## 🎯 What You Can Do

### Admin Features
✅ Create/edit/delete resources  
✅ Add categories and tags  
✅ Upload thumbnails  
✅ Mark resources as featured  
✅ Duplicate existing resources  
✅ Check if links are working  
✅ Search and filter  
✅ View analytics (view count)

### Consumer Features
✅ Search resources by keyword  
✅ Filter by category  
✅ Browse paginated list  
✅ View full resource details  
✅ See related resources  
✅ Featured resources on homepage  
✅ Mobile-responsive design

## 📚 Documentation

- **RESOURCES_SETUP.md** - Complete setup and usage guide
- **RESOURCES_IMPLEMENTATION.md** - Technical implementation details

## 🐛 Troubleshooting

**Issue:** TypeScript errors about react-router-dom
- **Fix:** Run `npm install` in both frontend directories

**Issue:** Database not found
- **Fix:** Run `python -m app.init_db` from backend directory

**Issue:** CORS errors
- **Fix:** Ensure backend is running on port 8000

**Issue:** No resources showing
- **Fix:** Create resources via admin interface first

## 🎨 Default Categories

- Early Intervention
- Therapy Services
- Educational Resources
- Support Groups
- Financial Assistance
- Medical Resources
- Legal Resources
- Community Activities

## 💡 Pro Tips

1. **Use Featured Flag**: Mark 2-3 best resources as featured for homepage
2. **Add Thumbnails**: Visual resources get more clicks
3. **Tag Everything**: Better search and filtering
4. **Check Links**: Run bulk link checker monthly
5. **Duplicate for Speed**: Use duplicate feature for similar resources
6. **Short Descriptions**: Keep under 200 chars for best display
7. **Related Resources**: System auto-suggests based on tags/category

## 🔐 Security

- Admin endpoints require OAuth authentication
- Consumer endpoints are public (no login needed)
- Links open in new tabs for security

## ✅ Status

All systems ready! Database initialized with default categories.
Dependencies installed. Ready to create resources!
