# SomaMange Deployment Guide - Render Free Tier

## 🚀 Step-by-Step Deployment (100% Free)

### Option 1: Basic Free Deployment (Recommended)
**Cost: $0/month** - No background workers

### Option 2: Full Features (Optional)
**Cost: $7/month** - With background workers for advanced features

---

## 📋 Option 1: Basic Free Deployment ($0/month)

### What Works Without Background Workers:
✅ **All Core Features:**
- Student management and enrollment
- Academic grading and report cards
- Fee management and receipts
- Attendance tracking
- Timetable management
- User authentication and roles
- Parent portal access
- All dashboard features

❌ **What Requires Background Workers:**
- AI assistant (DeepSeek integration)
- Email notifications
- Scheduled tasks (automated reports, etc.)
- Real-time notifications

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (ariho-code)
3. Authorize repository access

### Step 2: Create Web Service
1. Click **"New +"** → **"Web Service"**
2. Select **somamage** repository
3. Configure:

**Basic Settings:**
- **Name**: `somamage-web`
- **Environment**: `Python 3`
- **Branch**: `master`
- **Root Directory**: `school_management_system`

**Build Settings:**
- **Build Command**: 
  ```bash
pip install -r requirements-render.txt && python manage.py migrate && python manage.py createsuperuser_auto && python manage.py setup_demo_data && python manage.py collectstatic --noinput
```
- **Start Command**: 
  ```
  gunicorn sms.wsgi:application --bind 0.0.0.0:$PORT
  ```

### Step 3: Add Database
1. Click **"New +"** → **"PostgreSQL"**
2. **Name**: `somamage-db`
3. **Plan**: **Free**
4. **Database Name**: `somamage`
5. **User**: `somamage_user`

### Step 4: Environment Variables
Add these to your web service:

```bash
# Database (auto-populated by Render)
DATABASE_URL=postgresql://somamage_user:password@host:5432/somamage

# Security
SECRET_KEY=django-insecure-change-this-to-very-long-random-string
DEBUG=False
ALLOWED_HOSTS=somamage-web.onrender.com

# CORS
CSRF_TRUSTED_ORIGINS=https://somamage-web.onrender.com
CORS_ALLOWED_ORIGINS=https://somamage-web.onrender.com

# Optional (get from deepseek.com)
DEEPSEEK_API_KEY=sk-your-api-key-here
```

### Step 5: Deploy
Click **"Create Web Service"** - takes 5-10 minutes

### Step 6: Setup Initial Data
After deployment, visit: `https://somamage-web.onrender.com/admin/`
- Login with: `admin` / `admin123`
- Run setup: `https://somamage-web.onrender.com/setup/`

---

## 📋 Option 2: Full Features ($7/month)

### Add Background Workers for Advanced Features:

### Step 1: Add Redis
1. Click **"New +"** → **"Redis"**
2. **Name**: `somamage-redis`
3. **Plan**: **Free**

### Step 2: Add Celery Worker
1. Click **"New +"** → **"Worker"**
2. **Name**: `somamage-celery`
3. **Environment**: `Python 3`
4. **Plan**: **Starter** ($7/month)
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `celery -A sms worker -l info`

### Step 3: Add Environment Variables to Worker
```bash
DATABASE_URL=postgresql://somamage_user:password@host:5432/somamage
REDIS_URL=redis://host:port
SECRET_KEY=your-secret-key
DEBUG=False
```

---

## 🔧 Quick Setup Commands

### Generate Secure SECRET_KEY:
```bash
python -c "import secrets; print('django-insecure-' + secrets.token_urlsafe(50))"
```

### Test Locally First:
```bash
cd school_management_system
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## 📱 What You Get With Each Option

### Basic Free ($0):
- ✅ Complete school management
- ✅ Student records and grading
- ✅ Fee tracking and receipts
- ✅ Attendance management
- ✅ Timetables
- ✅ Multi-school support
- ✅ Parent portal
- ✅ All admin features
- ✅ UNEB-aligned grading
- ❌ AI assistant
- ❌ Email notifications
- ❌ Scheduled tasks

### Full Features ($7):
- ✅ Everything in Basic
- ✅ AI teaching assistant
- ✅ Email notifications
- ✅ Automated reports
- ✅ Real-time alerts
- ✅ Background processing

---

## 🚀 Deployment Checklist

### Before Deploying:
- [ ] GitHub repo is pushed
- [ ] SECRET_KEY generated
- [ ] DeepSeek API key (optional)
- [ ] Test locally works

### After Deploying:
- [ ] Visit admin panel
- [ ] Create superuser
- [ ] Setup initial schools
- [ ] Test login functionality
- [ ] Verify all features work

---

## 🆘 Troubleshooting

### Common Issues:
1. **Build fails**: Check requirements.txt
2. **Database errors**: Verify DATABASE_URL
3. **Static files not loading**: Run collectstatic
4. **Login not working**: Check SECRET_KEY and ALLOWED_HOSTS

### Getting Help:
- Check Render logs
- Verify environment variables
- Test database connection

---

## 📞 Support

**Your SomaMange will be live at:**
`https://somamage-web.onrender.com`

**For issues:**
- Email: arihotimothy89@gmail.com
- GitHub: ariho-code/somamage
- Render: Check dashboard logs

---

**🎉 Start with the free version and upgrade anytime!**
