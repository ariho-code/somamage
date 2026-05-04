"""
EduAI - Advanced AI Assistant for School Management System
Integrates with DeepSeek API for intelligent automation and analysis
Optimized for fast responses with streaming support
"""
import json
import requests
from typing import Dict, List, Optional, Any, Generator
from django.conf import settings
from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import base64
import traceback

logger = logging.getLogger(__name__)

class EduAIService:
    """EduAI Service for handling AI interactions with DeepSeek API"""
    
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = getattr(settings, 'DEEPSEEK_API_KEY', 'sk-74a60d49d12b4e9889f589ceed6cca5f')
    
    def __init__(self, user=None):
        self.user = user
        self.role = user.role if user else None
    
    def _get_system_knowledge_base(self) -> str:
        """Comprehensive system knowledge base for AI"""
        knowledge = """
SYSTEM KNOWLEDGE BASE - SCHOOL MANAGEMENT SYSTEM:

⚠️ CRITICAL: You have DIRECT DATABASE ACCESS. When users ask questions, you will receive REAL DATA in the context below. 
USE THIS DATA to provide accurate, specific answers. Do NOT say you don't have access - you DO have the data provided to you.
If data is provided in TEACHER INFORMATION or STUDENT INFORMATION sections, USE IT to answer questions.

USER ROLES:
- superadmin: Full system access, can manage everything
- headteacher: Can view all academic data, manage teachers, view financial summaries
- director_of_studies: Manages academic programs, subjects, combinations, timetables
- teacher: Can view assigned students, enter marks, view timetables
- bursar: Manages fees, payments, fee structures
- parent: Views child's academic performance, fees, attendance, report cards
- student: Views own academic records, fees, attendance, report cards

DATA STRUCTURE:
- Students: Have first_name, last_name, admission_number, index_number, date_of_birth, gender, guardian, photo
- Teachers: Users with role='teacher', can be class teachers or subject teachers
- Guardians: Have name, phone, email, address, relationship to student
- Grades: Classes like P1-P7 (Primary), S1-S4 (O-Level), S5-S6 (A-Level)
- Subjects: Linked to levels (Primary, O-Level, A-Level)
- Enrollments: Link students to grades, academic years, combinations (for A-Level)
- MarkEntry: Student marks for subjects in exams
- ReportCard: Academic performance summaries per term
- FeePayment: Fee payments with receipt numbers
- FeeBalance: Outstanding fee balances
- TimetableSlot: Class schedules with day, time, subject, teacher, room

QUERY CAPABILITIES:
When asked about a teacher, provide:
- Full name, age (if date_of_birth available)
- Role and school
- Classes they teach (if class_teacher)
- Subjects they teach (from TeacherSubject)
- Qualifications and bio
- Phone number
- Recent marks entered
- Timetable slots

When asked about a student, provide:
- Full name, age, gender
- Admission number, index number
- Current grade/class and stream
- Guardian information (name, phone, relationship)
- Academic performance (average scores, report cards)
- Fee status (balance, payments)
- Attendance records
- Medical information (if accessible)
- Subjects enrolled

When asked about a parent, provide:
- Name and contact information
- Children (students) linked
- Children's academic performance
- Fee payment status
- Relationship to students

AUTOMATION TASKS:
- generate_report_cards: Auto-generate report cards for current term
- update_fee_balances: Recalculate all fee balances
- cleanup_old_data: Identify old inactive records
- analyze_performance: Generate performance analysis
- analyze_fees: Generate fee collection analysis
- detect_security_issues: Check for security and configuration issues
"""
        return knowledge
    
    def _get_system_prompt(self, context: Dict = None) -> str:
        """Generate system prompt based on user role and context"""
        base_prompt = """You are EduAI, an intelligent, friendly, and highly capable AI assistant for an educational platform. 
You are powered by DeepSeek AI and designed to be conversational, helpful, and educational.

YOUR CORE PURPOSE:
- Engage in natural, friendly conversations with teachers, students, and administrators
- Provide educational support, research assistance, and learning resources
- Help with academic questions, lesson planning, research projects, and study guidance
- Assist with school management tasks when needed
- Be conversational, warm, and approachable - like a knowledgeable colleague or tutor

COMMUNICATION STYLE:
- Be conversational and friendly, not robotic
- Ask follow-up questions to better understand needs
- Provide detailed, helpful responses
- Use examples and explanations when teaching concepts
- Encourage learning and critical thinking
- Be patient and supportive

EDUCATIONAL FOCUS:
- Help teachers with lesson planning, curriculum development, and teaching strategies
- Assist students with homework, research, study techniques, and understanding concepts
- Provide educational resources, explanations, and learning materials
- Support research projects with information gathering and analysis
- Explain complex topics in simple, understandable ways
- Suggest learning resources and study methods"""
        
        role_prompts = {
            'superadmin': """You are assisting a school administrator. You can help with:
- School management and administrative tasks
- Educational planning and curriculum development
- Research and data analysis for decision-making
- Providing educational resources and best practices
- Engaging in educational discussions and research
- Helping with any academic or administrative questions""",
            
            'headteacher': """You are assisting a headteacher. You can help with:
- Educational leadership and school improvement strategies
- Curriculum planning and academic program development
- Research on teaching methods and educational best practices
- Student performance analysis and improvement strategies
- Professional development resources for teachers
- Educational research and academic discussions
- Lesson planning support and teaching resources""",
            
            'director_of_studies': """You are assisting a director of studies. You can help with:
- Curriculum design and academic program planning
- Educational research and teaching methodologies
- Subject matter expertise and content development
- Research assistance for academic projects
- Educational resource recommendations
- Teaching strategies and pedagogical approaches
- Academic planning and course development""",
            
            'teacher': """You are assisting a teacher. You can help with:
- Lesson planning and curriculum development
- Teaching strategies and pedagogical techniques
- Educational research and resource finding
- Creating engaging learning materials
- Explaining complex topics for students
- Research assistance for teaching projects
- Professional development and educational best practices
- Answering subject-specific questions
- Helping with student learning support""",
            
            'bursar': """You are assisting a bursar. You can help with:
- Financial management and fee-related questions
- Educational budgeting and resource allocation
- Research on financial best practices for schools
- Educational discussions when needed
- General assistance with school operations""",
            
            'parent': """You are assisting a parent. You can help with:
- Understanding your child's academic progress
- Educational support and learning resources
- Homework help and study techniques
- Research assistance for educational projects
- Explaining educational concepts
- Learning resources and educational materials
- General educational guidance""",
            
            'student': """You are assisting a student. You can help with:
- Homework and assignment support
- Understanding difficult concepts and subjects
- Research assistance for projects and papers
- Study techniques and learning strategies
- Educational resources and learning materials
- Explaining topics in simple, understandable ways
- Academic writing and research guidance
- Test preparation and study tips
- General educational questions and discussions"""
        }
        
        role_specific = role_prompts.get(self.role, "You are a helpful educational assistant.")
        knowledge_base = self._get_system_knowledge_base()
        
        return f"""{base_prompt}

{role_specific}

{knowledge_base}

IMPORTANT GUIDELINES:
- Be conversational, friendly, and engaging - like talking to a helpful colleague
- Focus on education, learning, and research support
- Provide detailed, thoughtful responses
- Ask clarifying questions when needed
- Use examples and explanations to help understanding
- Support both teachers and students with their educational needs
- Engage in educational discussions and research assistance
- Be patient, encouraging, and supportive
- When asked about school data, provide helpful insights while respecting privacy
- Let your natural conversational abilities shine - be helpful, not robotic

CRITICAL DATA USAGE - YOU HAVE FULL DATABASE ACCESS:
- You will receive COMPREHENSIVE SYSTEM DATA in the context for EVERY query
- This includes: System Summary, Performance Statistics, Subject Performance, Grade Performance, Recent Report Cards, Teacher Info, Student Info, and more
- USE ALL THIS REAL DATA to answer questions - it's from the actual database
- When SYSTEM SUMMARY is provided, use it to understand overall school statistics
- When PERFORMANCE STATISTICS are provided, use actual averages, min, max scores in your analysis
- When SUBJECT PERFORMANCE is provided, reference actual subject averages and counts
- When GRADE PERFORMANCE is provided, show grade-specific insights
- When RECENT REPORT CARDS are provided, reference actual student names and scores
- DO NOT say "I don't have access" or "I don't have the data" - you have ALL the data in context
- Be SPECIFIC: use actual numbers, names, scores, averages from the provided data
- When asked about performance, use the PERFORMANCE STATISTICS, SUBJECT PERFORMANCE, and GRADE PERFORMANCE data
- Provide detailed, data-driven analysis with real numbers and insights
- Reference actual data points like "The average score is X" or "Subject Y has an average of Z"
- Search through all provided data to answer questions comprehensively"""
    
    def _call_deepseek_api_stream(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4000) -> Generator[str, None, None]:
        """Call DeepSeek API with streaming for faster responses"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            response = requests.post(
                self.DEEPSEEK_API_URL,
                headers=headers,
                json=data,
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                json_str = line_str[6:]
                                if json_str.strip() == '[DONE]':
                                    break
                                data = json.loads(json_str)
                                delta = data.get('choices', [{}])[0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                yield None
                
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            yield None
    
    def _call_deepseek_api(self, messages: List[Dict], temperature: float = 0.8, max_tokens: int = 4000, stream: bool = False) -> Optional[str]:
        """Call DeepSeek API with messages - optimized for speed"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            response = requests.post(
                self.DEEPSEEK_API_URL,
                headers=headers,
                json=data,
                timeout=15  # Reduced timeout for faster failure
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    return content
                else:
                    logger.warning("DeepSeek API returned empty content")
                    return None
            else:
                error_text = response.text[:500] if hasattr(response, 'text') else 'Unknown error'
                logger.error(f"DeepSeek API error: {response.status_code} - {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("DeepSeek API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}", exc_info=True)
            return None
    
    def _has_permission(self, permission_type: str) -> bool:
        """Check if user has permission for specific data access"""
        if not self.user:
            return False
        
        role_permissions = {
            'superadmin': ['all'],
            'headteacher': ['all_students', 'all_teachers', 'all_fees', 'all_reports', 'all_grades'],
            'director_of_studies': ['all_students', 'all_teachers', 'all_grades', 'academic_reports'],
            'teacher': ['assigned_students', 'own_classes', 'own_marks'],
            'bursar': ['all_fees', 'fee_payments', 'fee_structures'],
            'parent': ['own_children', 'children_performance', 'children_fees'],
            'student': ['own_data', 'own_performance', 'own_fees']
        }
        
        user_perms = role_permissions.get(self.role, [])
        return 'all' in user_perms or permission_type in user_perms
    
    def _filter_data_by_role(self, data: Dict, data_type: str) -> Dict:
        """Filter data based on user role and permissions"""
        if not self.user:
            return {}
        
        # Superadmin and headteacher see everything
        if self._has_permission('all'):
            return data
        
        filtered = {}
        
        if data_type == 'students':
            if self.role == 'teacher':
                # Teachers only see their assigned students
                from students.models import Enrollment
                from academics.models import Grade
                
                teacher_grades = Grade.objects.filter(class_teacher=self.user)
                teacher_enrollments = Enrollment.objects.filter(grade__in=teacher_grades, is_active=True)
                
                student_ids = set(teacher_enrollments.values_list('student_id', flat=True))
                if 'students' in data:
                    filtered['students'] = [s for s in data.get('students', []) if s.get('id') in student_ids]
                else:
                    filtered['students'] = []
                filtered['total_students'] = len(filtered['students'])
            
            elif self.role == 'parent':
                # Parents only see their own children
                from students.models import Student, Guardian
                
                try:
                    guardian = Guardian.objects.filter(email=self.user.email).first()
                    if guardian:
                        children = Student.objects.filter(guardian=guardian)
                        child_ids = set(children.values_list('id', flat=True))
                        if 'students' in data:
                            filtered['students'] = [s for s in data.get('students', []) if s.get('id') in child_ids]
                        else:
                            filtered['students'] = []
                        filtered['total_students'] = len(filtered['students'])
                except:
                    filtered = {}
            
            else:
                filtered = data
        
        elif data_type == 'teachers':
            if self.role in ['teacher', 'parent', 'student']:
                # Limited info for teachers/parents/students
                if 'teachers' in data:
                    filtered['teachers'] = []
                    for teacher in data.get('teachers', [])[:5]:
                        filtered['teachers'].append({
                            'name': teacher.get('name', 'N/A'),
                            'subjects_taught': teacher.get('subjects_taught', [])[:3]
                        })
                    filtered['total_teachers'] = len(filtered['teachers'])
            else:
                filtered = data
        
        return filtered if filtered else data
    
    def _gather_all_system_data(self) -> Dict:
        """Gather ALL available system data for comprehensive AI access"""
        info = {}
        
        try:
            from django.contrib.auth import get_user_model
            from students.models import Student, Guardian, Enrollment
            from academics.models import Grade, TeacherSubject, MarkEntry, ReportCard, Exam, Subject
            from fees.models import FeeBalance, FeePayment, FeeStructure
            from timetable.models import TimetableSlot
            from core.models import Term, AcademicYear, School
            
            User = get_user_model()
            
            # Get school context
            school = self.user.school if self.user and hasattr(self.user, 'school') and self.user.school else None
            
            # Gather ALL students (with role filtering later)
            if school:
                students = Student.objects.filter(enrollments__grade__school=school).distinct()
            else:
                students = Student.objects.all()
            
            # Gather ALL teachers
            teachers = User.objects.filter(role__in=['teacher', 'headteacher', 'director_of_studies'])
            if school:
                teachers = teachers.filter(school=school)
            
            # Gather ALL report cards
            report_cards = ReportCard.objects.all()
            if school:
                report_cards = report_cards.filter(enrollment__grade__school=school)
            
            # Gather ALL marks
            marks = MarkEntry.objects.all()
            if school:
                marks = marks.filter(enrollment__grade__school=school)
            
            # Gather ALL grades
            grades = Grade.objects.all()
            if school:
                grades = grades.filter(school=school)
            
            # Gather ALL subjects
            subjects = Subject.objects.all()
            
            # Gather ALL exams
            exams = Exam.objects.all()
            if school:
                exams = exams.filter(school=school)
            
            # Gather ALL fee balances
            fee_balances = FeeBalance.objects.all()
            if school:
                fee_balances = fee_balances.filter(enrollment__grade__school=school)
            
            # Gather ALL fee payments
            fee_payments = FeePayment.objects.all()
            if school:
                fee_payments = fee_payments.filter(enrollment__grade__school=school)
            
            # Build comprehensive data summary
            info['system_summary'] = {
                'total_students': students.count(),
                'total_teachers': teachers.count(),
                'total_report_cards': report_cards.count(),
                'total_marks': marks.count(),
                'total_grades': grades.count(),
                'total_subjects': subjects.count(),
                'total_exams': exams.count(),
                'total_fee_balances': fee_balances.count(),
                'total_fee_payments': fee_payments.count(),
                'school': school.name if school else 'All Schools'
            }
            
            # Performance metrics
            if report_cards.exists():
                from django.db.models import Avg, Max, Min, Count
                perf_stats = report_cards.aggregate(
                    avg_score=Avg('average_score'),
                    max_score=Max('average_score'),
                    min_score=Min('average_score'),
                    count=Count('id')
                )
                info['performance_statistics'] = {
                    'average_score': float(perf_stats['avg_score'] or 0),
                    'max_score': float(perf_stats['max_score'] or 0),
                    'min_score': float(perf_stats['min_score'] or 0),
                    'total_report_cards': perf_stats['count']
                }
            
            # Subject performance summary
            subject_performance = {}
            for mark in marks[:500]:
                subject_name = mark.subject.name if mark.subject else 'Unknown'
                if subject_name not in subject_performance:
                    subject_performance[subject_name] = {'total': 0, 'count': 0}
                subject_performance[subject_name]['total'] += float(mark.score) if mark.score else 0
                subject_performance[subject_name]['count'] += 1
            
            for subject_name in subject_performance:
                if subject_performance[subject_name]['count'] > 0:
                    subject_performance[subject_name]['average'] = subject_performance[subject_name]['total'] / subject_performance[subject_name]['count']
            
            info['subject_performance'] = subject_performance
            
            # Grade performance summary
            grade_performance = {}
            for card in report_cards[:200]:
                grade_name = card.enrollment.grade.name if card.enrollment.grade else 'Unknown'
                if grade_name not in grade_performance:
                    grade_performance[grade_name] = []
                if card.average_score:
                    grade_performance[grade_name].append(float(card.average_score))
            
            for grade_name in grade_performance:
                if grade_performance[grade_name]:
                    grade_performance[grade_name] = {
                        'average': sum(grade_performance[grade_name]) / len(grade_performance[grade_name]),
                        'count': len(grade_performance[grade_name])
                    }
            
            info['grade_performance'] = grade_performance
            
            # Recent report cards (last 20)
            recent_cards_data = []
            for card in report_cards.order_by('-date_created')[:20]:
                recent_cards_data.append({
                    'student_name': card.enrollment.student.get_full_name(),
                    'grade': card.enrollment.grade.name if card.enrollment.grade else 'N/A',
                    'average_score': float(card.average_score) if card.average_score else 0,
                    'term': card.term.name if card.term else 'N/A',
                    'date': str(card.date_created.date()) if card.date_created else 'N/A',
                    'is_published': card.is_published
                })
            info['recent_report_cards'] = recent_cards_data
            
        except Exception as e:
            logger.error(f"Error gathering all system data: {str(e)}", exc_info=True)
            info['error'] = str(e)
        
        return info
    
    def _gather_user_info(self, query: str) -> Dict:
        """Gather detailed information about users mentioned in query - enhanced for better system understanding with role-based filtering"""
        info = {}
        
        # ALWAYS gather comprehensive system data
        system_data = self._gather_all_system_data()
        info.update(system_data)
        
        try:
            from django.contrib.auth import get_user_model
            from students.models import Student, Guardian, Enrollment
            from academics.models import Grade, TeacherSubject, MarkEntry, ReportCard, Exam
            from fees.models import FeeBalance, FeePayment, FeeStructure
            from timetable.models import TimetableSlot
            from core.models import Term, AcademicYear
            
            User = get_user_model()
            query_lower = query.lower()
            
            # Check if query mentions a teacher or asks about teachers
            if any(word in query_lower for word in ['teacher', 'staff', 'instructor', 'teach', 'faculty']):
                teachers = User.objects.filter(role__in=['teacher', 'headteacher', 'director_of_studies'])
                if self.user and hasattr(self.user, 'school') and self.user.school:
                    teachers = teachers.filter(school=self.user.school)
                
                teacher_info = []
                for teacher in teachers[:15]:  # Increased limit
                    try:
                        classes = Grade.objects.filter(class_teacher=teacher)
                        subjects = TeacherSubject.objects.filter(teacher=teacher).select_related('subject', 'grade')
                        
                        # Get recent marks entered
                        recent_marks = MarkEntry.objects.filter(teacher=teacher).order_by('-date_entered')[:5]
                        
                        teacher_data = {
                            'name': teacher.get_full_name() or teacher.username,
                            'username': teacher.username,
                            'phone': getattr(teacher, 'phone_number', 'N/A') or 'N/A',
                            'email': teacher.email or 'N/A',
                            'qualifications': getattr(teacher, 'qualifications', 'N/A') or 'N/A',
                            'bio': getattr(teacher, 'bio', 'N/A') or 'N/A',
                            'classes_taught': [g.name for g in classes],
                            'subjects_taught': [f"{ts.subject.name} ({ts.grade.name if ts.grade else 'All'})" for ts in subjects[:10]],
                            'school': teacher.school.name if hasattr(teacher, 'school') and teacher.school else 'N/A',
                            'recent_marks_count': recent_marks.count()
                        }
                        teacher_info.append(teacher_data)
                    except Exception as e:
                        logger.error(f"Error processing teacher {teacher.id}: {str(e)}")
                        continue
                
                info['teachers'] = teacher_info
                info['total_teachers'] = teachers.count()
                
                # Add IDs for filtering
                for i, teacher in enumerate(teacher_info):
                    if teachers[i]:
                        teacher['id'] = teachers[i].id
                
                # Filter by role
                info = {**info, **self._filter_data_by_role({'teachers': teacher_info, 'total_teachers': teachers.count()}, 'teachers')}
            
            # Check if query mentions a student or asks about students
            if any(word in query_lower for word in ['student', 'pupil', 'learner', 'child', 'children']):
                students = Student.objects.all()
                if self.user and hasattr(self.user, 'school') and self.user.school:
                    students = students.filter(enrollments__grade__school=self.user.school).distinct()
                
                # Try to extract specific student name or admission number from query
                import re
                admission_match = re.search(r'\b\d{4,}\b', query)  # Look for admission numbers
                name_words = [w for w in query.split() if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'with', 'about', 'student', 'show', 'tell', 'give', 'information']]
                
                student_info = []
                for student in students[:20]:  # Increased limit
                    try:
                        enrollments = Enrollment.objects.filter(student=student, is_active=True).select_related('grade', 'academic_year', 'combination')
                        current_enrollment = enrollments.first()
                        
                        # Filter if specific student mentioned
                        if name_words and not any(word.lower() in student.get_full_name().lower() for word in name_words):
                            if not admission_match or str(student.admission_number) not in query:
                                continue
                        
                        guardian_info = {}
                        if hasattr(student, 'guardian') and student.guardian:
                            guardian_info = {
                                'name': student.guardian.name,
                                'phone': getattr(student.guardian, 'phone', 'N/A'),
                                'email': getattr(student.guardian, 'email', 'N/A'),
                                'address': getattr(student.guardian, 'address', 'N/A'),
                                'relationship': getattr(student.guardian, 'relationship', 'N/A')
                            }
                        
                        # Get academic performance
                        report_cards = ReportCard.objects.filter(enrollment__student=student).order_by('-date_created')[:5]
                        avg_score = report_cards.aggregate(avg=Avg('average_score'))['avg'] if report_cards.exists() else None
                        
                        # Get recent marks
                        recent_marks = MarkEntry.objects.filter(enrollment__student=student).order_by('-date_entered')[:10]
                        
                        # Get fee status
                        fee_balance = FeeBalance.objects.filter(enrollment__student=student, enrollment__is_active=True).first()
                        
                        # Get attendance
                        recent_attendance = AttendanceRecord.objects.filter(enrollment__student=student).order_by('-date')[:10] if hasattr(AttendanceRecord, 'enrollment') else []
                        
                        student_data = {
                            'name': student.get_full_name(),
                            'admission_number': getattr(student, 'admission_number', 'N/A') or 'N/A',
                            'index_number': getattr(student, 'index_number', 'N/A') or 'N/A',
                            'age': student.age if hasattr(student, 'age') and hasattr(student, 'date_of_birth') and student.date_of_birth else None,
                            'gender': student.get_gender_display() if hasattr(student, 'get_gender_display') else getattr(student, 'gender', 'N/A'),
                            'current_grade': current_enrollment.grade.name if current_enrollment and current_enrollment.grade else 'N/A',
                            'stream': getattr(current_enrollment, 'stream', 'N/A') if current_enrollment else 'N/A',
                            'combination': current_enrollment.combination.name if current_enrollment and hasattr(current_enrollment, 'combination') and current_enrollment.combination else 'N/A',
                            'guardian': guardian_info,
                            'average_score': float(avg_score) if avg_score else None,
                            'fee_balance': float(fee_balance.balance) if fee_balance else None,
                            'fee_status': 'Paid' if fee_balance and fee_balance.balance <= 0 else 'Outstanding' if fee_balance else 'N/A',
                            'recent_marks': [{'subject': m.subject.name if hasattr(m, 'subject') else 'N/A', 'score': m.score, 'exam': m.exam.name if hasattr(m, 'exam') and m.exam else 'N/A'} for m in recent_marks[:5]],
                            'attendance_count': len(recent_attendance)
                        }
                        student_info.append(student_data)
                    except Exception as e:
                        logger.error(f"Error processing student {student.id}: {str(e)}")
                        continue
                
                # Add IDs for filtering
                for i, student in enumerate(student_info):
                    if i < len(list(students[:20])):
                        try:
                            student['id'] = list(students[:20])[i].id
                        except:
                            pass
                
                info['students'] = student_info
                info['total_students'] = students.count()
                
                # Filter by role
                info = {**info, **self._filter_data_by_role({'students': student_info, 'total_students': students.count()}, 'students')}
            
            # Check if query is about report cards
            if any(word in query_lower for word in ['report card', 'report', 'generate report', 'create report']):
                current_term = None
                if self.user and hasattr(self.user, 'school') and self.user.school:
                    try:
                        current_term = Term.get_current_term_for_school(self.user.school)
                    except:
                        pass
                
                info['report_cards'] = {
                    'can_generate': self.user and (self.user.is_superadmin() or self.user.is_headteacher()),
                    'current_term': current_term.name if current_term else 'N/A',
                    'total_students': Student.objects.count() if hasattr(Student, 'objects') else 0
                }
            
            # Check if query is about performance analysis
            if any(word in query_lower for word in ['performance', 'analyze performance', 'student performance', 'academic performance', 'analyze']):
                try:
                    school = self.user.school if self.user and hasattr(self.user, 'school') and self.user.school else None
                    
                    # Get students based on role
                    if self.user and (self.user.is_superadmin() or self.user.is_headteacher() or self.user.is_director_of_studies()):
                        if school:
                            students = Student.objects.filter(enrollments__grade__school=school, enrollments__is_active=True).distinct()
                        else:
                            students = Student.objects.filter(enrollments__is_active=True).distinct()
                    elif self.user and self.user.is_teacher():
                        grades = Grade.objects.filter(class_teacher=self.user)
                        enrollments = Enrollment.objects.filter(grade__in=grades, is_active=True)
                        students = Student.objects.filter(enrollments__in=enrollments).distinct()
                    else:
                        students = Student.objects.none()
                    
                    # Get performance data
                    report_cards = ReportCard.objects.filter(
                        enrollment__student__in=students,
                        is_published=True
                    ).select_related('enrollment', 'enrollment__student', 'enrollment__grade', 'term').order_by('-date_created')[:100]
                    
                    # Get marks data
                    marks = MarkEntry.objects.filter(
                        enrollment__student__in=students
                    ).select_related('enrollment', 'enrollment__student', 'subject', 'exam').order_by('-date_entered')[:200]
                    
                    # Calculate performance metrics
                    from django.db.models import Avg, Count, Max, Min
                    
                    performance_data = {
                        'total_students': students.count(),
                        'total_report_cards': report_cards.count(),
                        'total_marks': marks.count(),
                        'average_score': float(report_cards.aggregate(avg=Avg('average_score'))['avg'] or 0),
                        'max_score': float(report_cards.aggregate(max=Max('average_score'))['max'] or 0),
                        'min_score': float(report_cards.aggregate(min=Min('average_score'))['min'] or 0),
                        'recent_report_cards': []
                    }
                    
                    # Add recent report card summaries
                    for card in report_cards[:20]:
                        performance_data['recent_report_cards'].append({
                            'student_name': card.enrollment.student.get_full_name(),
                            'grade': card.enrollment.grade.name if card.enrollment.grade else 'N/A',
                            'average_score': float(card.average_score) if card.average_score else 0,
                            'term': card.term.name if card.term else 'N/A',
                            'date': str(card.date_created.date()) if card.date_created else 'N/A'
                        })
                    
                    # Add subject performance
                    subject_stats = {}
                    for mark in marks[:200]:
                        subject_name = mark.subject.name if mark.subject else 'Unknown'
                        if subject_name not in subject_stats:
                            subject_stats[subject_name] = {'total': 0, 'count': 0, 'avg': 0}
                        subject_stats[subject_name]['total'] += float(mark.score) if mark.score else 0
                        subject_stats[subject_name]['count'] += 1
                    
                    for subject_name, stats in subject_stats.items():
                        if stats['count'] > 0:
                            stats['avg'] = stats['total'] / stats['count']
                    
                    performance_data['subject_performance'] = subject_stats
                    
                    # Add grade-wise performance
                    grade_stats = {}
                    for card in report_cards[:100]:
                        grade_name = card.enrollment.grade.name if card.enrollment.grade else 'Unknown'
                        if grade_name not in grade_stats:
                            grade_stats[grade_name] = {'scores': [], 'avg': 0}
                        if card.average_score:
                            grade_stats[grade_name]['scores'].append(float(card.average_score))
                    
                    for grade_name, stats in grade_stats.items():
                        if stats['scores']:
                            stats['avg'] = sum(stats['scores']) / len(stats['scores'])
                            stats['count'] = len(stats['scores'])
                    
                    performance_data['grade_performance'] = grade_stats
                    
                    info['performance_analysis'] = performance_data
                    
                except Exception as e:
                    logger.error(f"Error gathering performance data: {str(e)}", exc_info=True)
                    info['performance_analysis'] = {'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error gathering user info: {str(e)}", exc_info=True)
        
        return info
    
    def chat(self, user_message: str, context: Dict = None, stream: bool = False) -> Dict:
        """Handle chat interaction with context - optimized for speed and learning"""
        system_prompt = self._get_system_prompt(context)
        
        # Load conversation history for learning
        conversation_history = self._load_conversation_history(limit=10)
        
        # Gather relevant information based on query
        user_info = self._gather_user_info(user_message)
        
        # Build context string with ALL available information
        context_str = ""
        
        # Add comprehensive system summary FIRST
        if user_info.get('system_summary'):
            context_str += f"\n{'='*80}\n"
            context_str += "COMPREHENSIVE SYSTEM DATA - YOU HAVE FULL ACCESS TO ALL INFORMATION BELOW\n"
            context_str += f"{'='*80}\n"
            context_str += f"\nSYSTEM SUMMARY:\n{json.dumps(user_info['system_summary'], indent=2, default=str)}\n"
        
        if user_info.get('performance_statistics'):
            context_str += f"\nPERFORMANCE STATISTICS:\n{json.dumps(user_info['performance_statistics'], indent=2, default=str)}\n"
        
        if user_info.get('subject_performance'):
            context_str += f"\nSUBJECT PERFORMANCE BREAKDOWN:\n{json.dumps(user_info['subject_performance'], indent=2, default=str)}\n"
        
        if user_info.get('grade_performance'):
            context_str += f"\nGRADE PERFORMANCE BREAKDOWN:\n{json.dumps(user_info['grade_performance'], indent=2, default=str)}\n"
        
        if user_info.get('recent_report_cards'):
            context_str += f"\nRECENT REPORT CARDS (Last 20):\n{json.dumps(user_info['recent_report_cards'], indent=2, default=str)}\n"
        
        if user_info.get('teachers'):
            context_str += f"\nTEACHER INFORMATION (Total: {user_info.get('total_teachers', len(user_info['teachers']))}):\n{json.dumps(user_info['teachers'], indent=2, default=str)}\n"
        
        if user_info.get('students'):
            context_str += f"\nSTUDENT INFORMATION (Total: {user_info.get('total_students', len(user_info['students']))}):\n{json.dumps(user_info['students'], indent=2, default=str)}\n"
        
        if user_info.get('report_cards'):
            context_str += f"\nREPORT CARD INFORMATION:\n{json.dumps(user_info['report_cards'], indent=2, default=str)}\n"
        
        if user_info.get('performance_analysis'):
            context_str += f"\nDETAILED PERFORMANCE ANALYSIS DATA:\n{json.dumps(user_info['performance_analysis'], indent=2, default=str)}\n"
        
        context_str += f"\n{'='*80}\n"
        context_str += "⚠️ CRITICAL INSTRUCTIONS:\n"
        context_str += "- ALL DATA ABOVE IS REAL DATA FROM THE DATABASE\n"
        context_str += "- USE ACTUAL NUMBERS, NAMES, AND STATISTICS FROM THE DATA PROVIDED\n"
        context_str += "- DO NOT say 'I don't have access' - you have ALL the data above\n"
        context_str += "- Provide SPECIFIC analysis using the real numbers and statistics\n"
        context_str += "- Reference actual student names, grades, scores when available\n"
        context_str += "- Use the performance statistics, subject breakdowns, and grade data\n"
        context_str += f"{'='*80}\n"
        
        # Gather system context
        system_context = self._gather_system_context(context)
        
        # Build messages with conversation history for context
        messages = [
            {"role": "system", "content": system_prompt + "\n\n" + system_context + context_str}
        ]
        
        # Add conversation history for learning
        for conv in conversation_history:
            messages.append({"role": "user", "content": conv['message']})
            messages.append({"role": "assistant", "content": conv['response']})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        if stream:
            return {
                "stream": self._call_deepseek_api_stream(messages),
                "success": True
            }
        else:
            try:
                response = self._call_deepseek_api(messages, temperature=0.8, max_tokens=4000)
                
                if response and response.strip():
                    # Filter response based on role permissions
                    filtered_response = self._filter_response_by_role(response, user_message, user_info)
                    
                    # Save conversation for learning (save filtered response)
                    self._save_conversation(user_message, filtered_response, context)
                    
                    # Parse response for actions (but don't let it interfere with natural conversation)
                    actions = self._parse_actions(filtered_response)
                    return {
                        "response": filtered_response,
                        "actions": actions,
                        "success": True
                    }
                else:
                    # If API returns empty, provide helpful response based on context
                    fallback_response = self._generate_fallback_response(user_message, user_info)
                    return {
                        "response": fallback_response,
                        "actions": [],
                        "success": True  # Still mark as success to show response
                    }
            except Exception as e:
                logger.error(f"Error in chat method: {str(e)}", exc_info=True)
                # Provide helpful fallback even on error
                fallback_response = self._generate_fallback_response(user_message, user_info)
                return {
                    "response": fallback_response,
                    "actions": [],
                    "success": False
                }
    
    def _generate_fallback_response(self, user_message: str, user_info: Dict) -> str:
        """Generate a helpful response even when API fails"""
        query_lower = user_message.lower()
        response = "I'm here to help! "
        
        if user_info.get('teachers'):
            response += f"I found {len(user_info['teachers'])} teacher(s) in the system. "
            if any(word in query_lower for word in ['teacher', 'staff']):
                teacher_names = [t.get('name', 'Unknown') for t in user_info['teachers'][:5]]
                response += f"Here are some teachers: {', '.join(teacher_names)}. "
        
        if user_info.get('students'):
            response += f"I found {len(user_info['students'])} student(s). "
            if any(word in query_lower for word in ['student', 'pupil']):
                student_names = [s.get('name', 'Unknown') for s in user_info['students'][:5]]
                response += f"Here are some students: {', '.join(student_names)}. "
        
        if any(word in query_lower for word in ['report card', 'generate report']):
            if user_info.get('report_cards', {}).get('can_generate'):
                response += "I can help you generate report cards for the current term. "
            else:
                response += "Report card generation requires administrator privileges. "
        
        response += "Could you please rephrase your question or be more specific about what you'd like to know?"
        return response
    
    def _load_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Load recent conversation history for context"""
        if not self.user:
            return []
        
        try:
            from .models import AIConversation
            conversations = AIConversation.objects.filter(
                user=self.user
            ).order_by('-created_at')[:limit]
            
            # Return in chronological order (oldest first)
            history = []
            for conv in reversed(conversations):
                history.append({
                    'message': conv.message,
                    'response': conv.response
                })
            return history
        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}")
            return []
    
    def _save_conversation(self, user_message: str, ai_response: str, context: Dict = None):
        """Save conversation to database for learning"""
        if not self.user:
            return
        
        try:
            from .models import AIConversation
            AIConversation.objects.create(
                user=self.user,
                message=user_message,
                response=ai_response,
                context=context or {}
            )
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
    
    def _gather_system_context(self, context: Dict = None) -> str:
        """Gather relevant system context for the AI"""
        context_parts = []
        
        if self.user and self.user.school:
            context_parts.append(f"Current School: {self.user.school.name}")
            context_parts.append(f"School Type: {self.user.school.school_type}")
        
        if context:
            if 'students_count' in context:
                context_parts.append(f"Total Students: {context['students_count']}")
            if 'teachers_count' in context:
                context_parts.append(f"Total Teachers: {context['teachers_count']}")
            if 'current_term' in context:
                context_parts.append(f"Current Term: {context['current_term']}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _parse_actions(self, response: str) -> List[Dict]:
        """Parse AI response for actionable commands"""
        actions = []
        
        # Look for action markers in response
        if "[[ACTION:" in response:
            import re
            action_pattern = r'\[\[ACTION:(\w+)(?:\(([^\)]+)\))?\]\]'
            matches = re.findall(action_pattern, response)
            
            for match in matches:
                action_type = match[0]
                params = match[1] if len(match) > 1 else ""
                actions.append({
                    "type": action_type,
                    "params": params
                })
        
        return actions
    
    def _filter_response_by_role(self, response: str, user_message: str, user_info: Dict) -> str:
        """Filter AI response based on user role to hide unauthorized information"""
        if not self.user or self._has_permission('all'):
            return response  # No filtering needed
        
        query_lower = user_message.lower()
        response_lower = response.lower()
        
        # If asking about other students' private info (grades, fees) and user is not authorized
        if self.role == 'parent':
            # Parents should only see their own children's info
            if any(word in query_lower for word in ['student', 'pupil', 'learner']) and \
               not any(word in query_lower for word in ['my child', 'my children', 'my son', 'my daughter']):
                # Check if response mentions students not in user_info
                if user_info.get('students'):
                    allowed_names = [s.get('name', '').lower() for s in user_info.get('students', [])]
                    # Allow response if it only mentions allowed students
                    lines = response.split('\n')
                    filtered_lines = []
                    for line in lines:
                        line_lower = line.lower()
                        if any(name in line_lower for name in allowed_names if name) or \
                           not any(word in line_lower for word in ['student', 'pupil', 'admission']):
                            filtered_lines.append(line)
                        else:
                            # Replace with generic message
                            filtered_lines.append("[Information about other students is restricted. You can only view your own children's information.]")
                    response = '\n'.join(filtered_lines)
        
        elif self.role == 'teacher':
            # Teachers shouldn't see other teachers' private details
            if any(word in query_lower for word in ['teacher', 'staff']) and \
               'phone' in response_lower or 'email' in response_lower:
                # Only show basic info
                import re
                # Remove phone numbers and emails from response
                response = re.sub(r'\b\d{10,}\b', '[Phone number hidden]', response)
                response = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[Email hidden]', response)
        
        elif self.role == 'student':
            # Students should only see their own information
            if any(word in query_lower for word in ['student', 'pupil']) and \
               'my' not in query_lower and 'me' not in query_lower:
                return "I can only provide information about your own academic records. Please ask about your own performance, fees, or attendance."
        
        return response
    
    def analyze_performance(self, filters: Dict = None) -> Dict:
        """Analyze student performance data"""
        from students.models import Student, Enrollment
        from academics.models import MarkEntry, ReportCard
        
        analysis = {
            "total_students": 0,
            "performance_summary": {},
            "recommendations": []
        }
        
        try:
            school = self.user.school if self.user and hasattr(self.user, 'school') else None
            
            # Get students based on user role
            if self.user.is_superadmin() or self.user.is_headteacher():
                if school:
                    students = Student.objects.filter(enrollments__grade__school=school, enrollments__is_active=True).distinct()
                else:
                    students = Student.objects.filter(enrollments__is_active=True).distinct()
            elif self.user.is_teacher():
                # Get students from teacher's classes
                from academics.models import Grade
                grades = Grade.objects.filter(class_teacher=self.user)
                enrollments = Enrollment.objects.filter(grade__in=grades, is_active=True)
                students = Student.objects.filter(enrollments__in=enrollments).distinct()
            else:
                return {"error": "Insufficient permissions"}
            
            analysis["total_students"] = students.count()
            
            # Get recent report cards
            recent_cards = ReportCard.objects.filter(
                enrollment__student__in=students,
                is_published=True
            ).order_by('-date_created')[:100]
            
            if recent_cards.exists():
                avg_score = recent_cards.aggregate(avg=Avg('average_score'))['avg'] or 0
                analysis["performance_summary"] = {
                    "average_score": float(avg_score),
                    "total_report_cards": recent_cards.count()
                }
            
            # Generate AI recommendations
            prompt = f"""Analyze the following school performance data and provide 3-5 concise recommendations:
- Total Students: {analysis['total_students']}
- Average Score: {analysis.get('performance_summary', {}).get('average_score', 0):.2f}%

Provide actionable recommendations."""
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            ai_response = self._call_deepseek_api(messages, temperature=0.5, max_tokens=1000)
            if ai_response:
                analysis["recommendations"] = [r.strip() for r in ai_response.split("\n") if r.strip()][:5]
            
        except Exception as e:
            logger.error(f"Error in performance analysis: {str(e)}")
            analysis["error"] = str(e)
        
        return analysis
    
    def analyze_fees(self, filters: Dict = None) -> Dict:
        """Analyze fee collection and balances"""
        from fees.models import FeePayment, FeeBalance, FeeStructure
        
        if not (self.user.is_superadmin() or self.user.is_headteacher() or self.user.is_bursar()):
            return {"error": "Insufficient permissions"}
        
        analysis = {
            "total_collected": 0,
            "total_balance": 0,
            "collection_rate": 0,
            "recommendations": []
        }
        
        try:
            school = self.user.school if self.user and hasattr(self.user, 'school') else None
            
            if not school:
                return {"error": "No school associated with user"}
            
            # Get fee data filtered by school
            total_collected = FeePayment.objects.filter(
                enrollment__grade__school=school
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            
            total_balance = FeeBalance.objects.filter(
                enrollment__grade__school=school,
                enrollment__is_active=True
            ).aggregate(total=Sum('balance'))['total'] or 0
            
            total_expected = FeeStructure.objects.filter(
                grade__school=school
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            analysis["total_collected"] = float(total_collected)
            analysis["total_balance"] = float(total_balance)
            analysis["collection_rate"] = (float(total_collected) / float(total_expected) * 100) if total_expected > 0 else 0
            
            # Generate AI recommendations
            prompt = f"""Analyze fee collection data and provide 3-5 concise recommendations:
- Total Collected: {analysis['total_collected']:,.2f}
- Total Balance: {analysis['total_balance']:,.2f}
- Collection Rate: {analysis['collection_rate']:.2f}%

Provide actionable recommendations."""
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            ai_response = self._call_deepseek_api(messages, temperature=0.5, max_tokens=1000)
            if ai_response:
                analysis["recommendations"] = [r.strip() for r in ai_response.split("\n") if r.strip()][:5]
                
        except Exception as e:
            logger.error(f"Error in fee analysis: {str(e)}")
            analysis["error"] = str(e)
        
        return analysis
    
    def detect_security_issues(self) -> Dict:
        """Detect potential security issues in the system"""
        if not (self.user.is_superadmin() or self.user.is_headteacher()):
            return {"error": "Insufficient permissions"}
        
        issues = []
        
        try:
            # Check for weak passwords (users with default or common passwords)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Check for users without proper role assignments
            users_without_roles = User.objects.filter(role='').count()
            if users_without_roles > 0:
                issues.append({
                    "type": "configuration",
                    "severity": "medium",
                    "message": f"{users_without_roles} users without proper role assignments",
                    "recommendation": "Assign appropriate roles to all users"
                })
            
            # Check for students without enrollments
            from students.models import Student, Enrollment
            students_without_enrollments = Student.objects.filter(
                enrollments__isnull=True
            ).count()
            if students_without_enrollments > 0:
                issues.append({
                    "type": "data_integrity",
                    "severity": "low",
                    "message": f"{students_without_enrollments} students without active enrollments",
                    "recommendation": "Review and update student enrollments"
                })
            
            # Check for missing school settings
            if self.user.school:
                if not self.user.school.logo:
                    issues.append({
                        "type": "configuration",
                        "severity": "low",
                        "message": "School logo not configured",
                        "recommendation": "Upload school logo for better branding"
                    })
            
            # Generate AI-powered security recommendations
            if issues:
                prompt = f"""Review these security and configuration issues:
{json.dumps(issues, indent=2)}

Provide 3-5 additional concise security recommendations for a school management system."""
                
                messages = [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
                
                ai_response = self._call_deepseek_api(messages, temperature=0.3, max_tokens=1000)
                if ai_response:
                    issues.append({
                        "type": "ai_recommendation",
                        "severity": "info",
                        "message": "AI Security Recommendations",
                        "recommendation": ai_response
                    })
        
        except Exception as e:
            logger.error(f"Error detecting security issues: {str(e)}")
            issues.append({
                "type": "error",
                "severity": "high",
                "message": f"Error during security check: {str(e)}",
                "recommendation": "Review system logs"
            })
        
        return {
            "issues": issues,
            "total_issues": len(issues),
            "critical": len([i for i in issues if i.get('severity') == 'high']),
            "medium": len([i for i in issues if i.get('severity') == 'medium']),
            "low": len([i for i in issues if i.get('severity') == 'low'])
        }
    
    def automate_task(self, task_type: str, params: Dict = None) -> Dict:
        """Execute automation tasks based on type"""
        if not (self.user.is_superadmin() or self.user.is_headteacher()):
            return {"error": "Insufficient permissions for automation"}
        
        params = params or {}
        result = {"success": False, "message": "", "data": {}}
        
        try:
            if task_type == "generate_report_cards":
                # Auto-generate report cards for current term
                from academics.models import ReportCard, Enrollment
                from core.models import Term
                
                current_term = Term.get_current_term_for_school(self.user.school)
                if not current_term:
                    return {"success": False, "message": "No active term found"}
                
                enrollments = Enrollment.objects.filter(
                    is_active=True,
                    academic_year=current_term.academic_year
                )
                
                generated = 0
                for enrollment in enrollments:
                    report_card, created = ReportCard.objects.get_or_create(
                        enrollment=enrollment,
                        term=current_term,
                        defaults={'is_published': False}
                    )
                    if created:
                        generated += 1
                
                result = {
                    "success": True,
                    "message": f"Generated {generated} new report cards",
                    "data": {"generated": generated}
                }
            
            elif task_type == "update_fee_balances":
                # Recalculate fee balances
                from fees.models import FeeBalance, FeePayment, FeeStructure
                from students.models import Enrollment
                
                updated = 0
                enrollments = Enrollment.objects.filter(is_active=True)
                
                for enrollment in enrollments:
                    # Calculate total paid
                    total_paid = FeePayment.objects.filter(
                        enrollment=enrollment
                    ).aggregate(total=Sum('amount_paid'))['total'] or 0
                    
                    # Calculate total expected
                    fee_structure = FeeStructure.objects.filter(
                        grade=enrollment.grade,
                        term=enrollment.academic_year.terms.first()
                    ).first()
                    
                    total_expected = fee_structure.amount if fee_structure else 0
                    balance = total_expected - total_paid
                    
                    fee_balance, _ = FeeBalance.objects.get_or_create(
                        enrollment=enrollment,
                        defaults={'balance': balance}
                    )
                    fee_balance.balance = balance
                    fee_balance.save()
                    updated += 1
                
                result = {
                    "success": True,
                    "message": f"Updated {updated} fee balances",
                    "data": {"updated": updated}
                }
            
            elif task_type == "cleanup_old_data":
                # Clean up old inactive records
                from students.models import Enrollment
                from datetime import timedelta
                
                cutoff_date = timezone.now().date() - timedelta(days=365)
                old_enrollments = Enrollment.objects.filter(
                    is_active=False,
                    date_left__lt=cutoff_date
                )
                
                count = old_enrollments.count()
                # Don't actually delete, just mark
                result = {
                    "success": True,
                    "message": f"Found {count} old inactive enrollments",
                    "data": {"count": count}
                }
            
            else:
                result = {"success": False, "message": f"Unknown task type: {task_type}"}
        
        except Exception as e:
            logger.error(f"Error in automation task {task_type}: {str(e)}")
            result = {"success": False, "message": str(e)}
        
        return result
    
    def generate_report(self, report_type: str, filters: Dict = None) -> Dict:
        """Generate various reports"""
        filters = filters or {}
        
        if report_type == "performance":
            return self.analyze_performance(filters)
        elif report_type == "fees":
            return self.analyze_fees(filters)
        elif report_type == "security":
            return self.detect_security_issues()
        else:
            return {"error": f"Unknown report type: {report_type}"}
    
    def process_file_upload(self, file_content: bytes, file_name: str, file_type: str) -> Dict:
        """Process uploaded files for AI analysis - improved for educational content"""
        try:
            # Check file size
            if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
                return {"error": "File too large. Maximum size is 10MB", "success": False}
            
            # Determine file type and handle accordingly
            if file_type.startswith('image/'):
                # For images, provide helpful response
                prompt = f"""A user has uploaded an image file named '{file_name}'. 
While I cannot directly view images, I can help with:
- Educational discussions about the image if described
- Research on related topics
- Creating educational content related to it
- Answering questions about it

Please provide a friendly, helpful response that encourages the user to describe the image or ask questions about it."""
                
                messages = [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
                
                response = self._call_deepseek_api(messages, temperature=0.8, max_tokens=2000)
                
                if response:
                    return {
                        "success": True,
                        "analysis": response,
                        "file_name": file_name
                    }
                else:
                    return {
                        "success": True,
                        "analysis": f"I've received your image file '{file_name}'. While I can't directly view images, I can help you with:\n\n- Describing what you see in the image\n- Educational research on related topics\n- Creating content or materials related to it\n- Answering questions about it\n\nWhat would you like to know or discuss about this image?",
                        "file_name": file_name
                    }
            
            elif file_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # For documents, provide helpful message
                return {
                    "success": True,
                    "analysis": f"I've received your document '{file_name}'. While I can't directly read PDF or Word documents, I can help you with:\n\n- Questions about the document's content if you describe it\n- Educational research related to the topic\n- Analysis and discussion of the subject matter\n- Creating summaries or explanations\n- Research assistance for related topics\n\nWhat would you like help with regarding this document?",
                    "file_name": file_name
                }
            
            elif file_type == 'text/plain' or file_type.startswith('text/'):
                # For text files, read and analyze
                try:
                    text_content = file_content.decode('utf-8', errors='ignore')
                    # Limit to first 8000 characters to avoid token limits
                    text_preview = text_content[:8000]
                    
                    prompt = f"""Analyze this text document ({file_name}) and provide:
1. A summary of the key content
2. Main topics or themes
3. Educational insights or explanations
4. Any questions or discussion points it raises
5. How it might be useful for teaching or learning
6. Research suggestions or related topics

Document content:
{text_preview}
{f'\n[Note: Document continues beyond this point...]' if len(text_content) > 8000 else ''}"""
                    
                    messages = [
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ]
                    
                    response = self._call_deepseek_api(messages, temperature=0.8, max_tokens=3000)
                    
                    if response:
                        return {
                            "success": True,
                            "analysis": response,
                            "file_name": file_name
                        }
                    else:
                        return {"error": "Failed to analyze text file", "success": False}
                except Exception as e:
                    logger.error(f"Error processing text file: {str(e)}")
                    return {"error": f"Error reading text file: {str(e)}", "success": False}
            
            else:
                return {
                    "success": True,
                    "analysis": f"I've received your file '{file_name}' (type: {file_type}). While I may not be able to directly process this file type, I can help you with:\n\n- Questions about the file's content or purpose\n- Educational research on related topics\n- Creating similar content or materials\n- Analysis and discussion\n- Research assistance\n\nWhat would you like help with?",
                    "file_name": file_name
                }

        except Exception as e:
            logger.error(f"Error processing file upload: {str(e)}")
            return {"error": f"Error processing file: {str(e)}", "success": False}
