# SomaMange - School Management System

A modern, comprehensive school management system built for Ugandan schools (P1-P7, O-Level, A-Level). Built with Django and designed for the UNEB curriculum.

## 🚀 Features

- **Multi-School Support**: Manage multiple schools from one platform
- **Student Management**: Enrollment, profiles, guardians, and medical records
- **Academic Management**: UNEB-aligned grading (PLE, UCE, UACE), report cards, transcripts
- **Fee Management**: Structure fees, track payments, generate receipts
- **Attendance Tracking**: Daily registers, absence alerts, analytics
- **Timetable Management**: Clash-free scheduling, teacher assignments
- **E-Learning Platform**: Assignments, quizzes, digital resources
- **AI Assistant**: Natural language queries and insights
- **Parent Portal**: Secure access to student progress and fees
- **Role-Based Access**: Superadmin, Headteachers, Teachers, Bursars, Parents

## 🛠 Technology Stack

- **Backend**: Django 5.2.6 with Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: JWT tokens with custom user model
- **Background Tasks**: Celery with Redis
- **File Storage**: Cloudinary integration
- **PDF Generation**: WeasyPrint
- **Frontend**: Django templates with Bootstrap4, modern CSS

## 📋 Requirements

- Python 3.9+
- PostgreSQL 12+
- Redis (for Celery)
- Node.js (for asset compilation, optional)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/somamage.git
cd somamage
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/somamage
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### 5. Database Setup

```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Set Up Initial Data

```bash
python manage.py setup_users
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## 🌐 Deployment

### Render (Recommended)

1. **Create a Render Account**: Sign up at [render.com](https://render.com)

2. **Connect GitHub Repository**: 
   - Create a new Web Service
   - Connect your GitHub repository
   - Select the `school_management_system` directory as the root directory

3. **Configure Environment Variables**:
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   SECRET_KEY=your-production-secret-key
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.onrender.com
   DEEPSEEK_API_KEY=your-deepseek-api-key
   ```

4. **Build Command**:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```

5. **Start Command**:
   ```bash
   gunicorn sms.wsgi:application --bind 0.0.0.0:$PORT
   ```

### Manual Deployment

For manual deployment on any server:

1. Set up PostgreSQL database
2. Configure environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Collect static files: `python manage.py collectstatic`
6. Use Gunicorn for production: `gunicorn sms.wsgi:application`

## 📁 Project Structure

```
school_management_system/
├── sms/                 # Main Django project settings
├── core/               # Core models and utilities
├── tenants/            # Multi-tenant support
├── students/           # Student management
├── academics/          # Academic records and grading
├── fees/              # Fee management
├── attendance/        # Attendance tracking
├── timetable/         # Timetable management
├── elearning/         # E-learning platform
├── templates/         # Django templates
├── static/           # Static files
├── media/            # User uploads
└── manage.py         # Django management script
```

## 👥 User Roles

- **Superadmin**: Full system access, multi-school management
- **Headteacher**: School-specific operations and oversight
- **Teacher**: Grade entry, timetable, student records
- **Bursar**: Fee management and payment tracking
- **Director of Studies**: Academic management
- **Parent**: View student progress and fees (no login required)

## 🔐 Default Credentials

After running `python manage.py setup_users`:

- **Superadmin**: `admin` / `admin123`
- **Headteacher (Primary)**: `headteacher_primary` / `headteacher123`
- **Headteacher (High School)**: `headteacher_high` / `headteacher123`
- **Teachers**: `teacher1-4` / `teacher123`
- **Bursar**: `bursar` / `bursar123`
- **Director**: `director` / `director123`

**Parent Access**: Use student admission number (auto-generated) with default password `parent{ADMISSION_NUMBER}`

## 📞 Support

- **Email**: hello@arihoforge.com
- **Phone**: +256 760 730 254
- **WhatsApp**: +256 760 730 254

## 📄 License

© 2024 SomaMange by ArihoForge. All rights reserved.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🐛 Bug Reports

Please report bugs via GitHub Issues or email us directly.

---

**Built with ❤️ for Ugandan schools by ArihoForge**
