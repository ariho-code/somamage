from django.core.management.base import BaseCommand
from academics.models import Subject, SubjectPaper


class Command(BaseCommand):
    help = 'Delete all existing O-Level subjects and populate new ones from Ugandan UCE curriculum'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Deleting all existing O-Level subjects...'))
        
        # Delete all O-Level subjects and their papers
        o_level_subjects = Subject.objects.filter(level='O')
        count = o_level_subjects.count()
        o_level_subjects.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} existing O-Level subjects'))
        self.stdout.write(self.style.SUCCESS('Starting to populate new O-Level subjects...'))
        
        # Subject data with papers
        subjects_data = [
            # Compulsory Subjects
            {
                'name': 'English Language',
                'code': '112',
                'is_compulsory': True,
                'papers': [
                    {'name': 'English Language', 'code': '112/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Mathematics',
                'code': '456',
                'is_compulsory': True,
                'papers': [
                    {'name': 'Mathematics', 'code': '456/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'History & Political Education',
                'code': '241',
                'is_compulsory': True,
                'papers': [
                    {'name': 'History & Political Education', 'code': '241/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Geography',
                'code': '273',
                'is_compulsory': True,
                'papers': [
                    {'name': 'Geography', 'code': '273/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Christian Religious Education',
                'code': '223',
                'is_compulsory': True,
                'papers': [
                    {'name': 'Christian Religious Education', 'code': '223/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Islamic Religious Education',
                'code': '225',
                'is_compulsory': True,
                'papers': [
                    {'name': 'Islamic Religious Education', 'code': '225/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'General Science',
                'code': '500',
                'is_compulsory': True,
                'papers': [
                    {'name': 'General Science - Physics', 'code': '500/1', 'paper_number': 1},
                    {'name': 'General Science - Chemistry', 'code': '500/2', 'paper_number': 2},
                    {'name': 'General Science - Biology', 'code': '500/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Information & Communications Technology',
                'code': '840',
                'is_compulsory': True,
                'papers': [
                    {'name': 'Theory', 'code': '840/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '840/2', 'paper_number': 2}
                ]
            },
            # Optional/Elective Subjects - Separate Sciences
            {
                'name': 'Biology',
                'code': '553',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '553/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '553/2', 'paper_number': 2},
                    {'name': 'Practical', 'code': '553/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Chemistry',
                'code': '545',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '545/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '545/2', 'paper_number': 2},
                    {'name': 'Practical', 'code': '545/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Physics',
                'code': '535',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '535/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '535/2', 'paper_number': 2},
                    {'name': 'Practical', 'code': '535/3', 'paper_number': 3}
                ]
            },
            # Optional/Elective Subjects - Others
            {
                'name': 'Agriculture',
                'code': '527',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '527/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '527/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Literature in English',
                'code': '208',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Literature in English', 'code': '208/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Lugha na Fasihi ya Kiswahili',
                'code': '336',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Lugha na Fasihi ya Kiswahili', 'code': '336/1', 'paper_number': 1},
                    {'name': 'Lugha na Fasihi ya Kiswahili', 'code': '336/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Entrepreneurship',
                'code': '845',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Entrepreneurship', 'code': '845/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Art',
                'code': '612',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Art History & Studio Technology - Theory', 'code': '612/1', 'paper_number': 1},
                    {'name': 'Art Making - Planning', 'code': '612/2', 'paper_number': 2},
                    {'name': 'Art Making - Production', 'code': '612/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Performing Arts',
                'code': '621',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Aural, Composition and Theory', 'code': '621/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Technology and Design',
                'code': '745',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '745/1', 'paper_number': 1},
                    {'name': 'Design & Drawing', 'code': '745/2', 'paper_number': 2},
                    {'name': 'Practical', 'code': '745/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Nutrition & Food Technology',
                'code': '662',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '662/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': '662/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Physical Education',
                'code': '555',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Theory', 'code': '555/1', 'paper_number': 1},
                    {'name': 'Performance', 'code': '555/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Ugandan Sign Language',
                'code': '397',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Reading Comprehension & Writing', 'code': '397/1', 'paper_number': 1},
                    {'name': 'Observing and Signing - Oral', 'code': '397/2', 'paper_number': 2}
                ]
            },
            # Local Languages
            {
                'name': 'Leb Acoli',
                'code': '305',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Leb Acoli', 'code': '305/1', 'paper_number': 1},
                    {'name': 'Leb Acoli', 'code': '305/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Leb Lango',
                'code': '315',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Leb Lango', 'code': '315/1', 'paper_number': 1},
                    {'name': 'Leb Lango', 'code': '315/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'LugbaraTi',
                'code': '325',
                'is_compulsory': False,
                'papers': [
                    {'name': 'LugbaraTi', 'code': '325/1', 'paper_number': 1},
                    {'name': 'LugbaraTi', 'code': '325/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Luganda',
                'code': '335',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Luganda', 'code': '335/1', 'paper_number': 1},
                    {'name': 'Luganda', 'code': '335/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Runyankore/Rukiga',
                'code': '345',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Runyankore/Rukiga', 'code': '345/1', 'paper_number': 1},
                    {'name': 'Runyankore/Rukiga', 'code': '345/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Lusoga',
                'code': '355',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Lusoga', 'code': '355/1', 'paper_number': 1},
                    {'name': 'Lusoga', 'code': '355/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Ateso',
                'code': '365',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Ateso', 'code': '365/1', 'paper_number': 1},
                    {'name': 'Ateso', 'code': '365/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Dhopadhola',
                'code': '375',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Dhopadhola', 'code': '375/1', 'paper_number': 1},
                    {'name': 'Dhopadhola', 'code': '375/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Runyoro/Rutoro',
                'code': '385',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Runyoro/Rutoro', 'code': '385/1', 'paper_number': 1},
                    {'name': 'Runyoro/Rutoro', 'code': '385/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Lumasaaba',
                'code': '395',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Lumasaaba', 'code': '395/1', 'paper_number': 1},
                    {'name': 'Lumasaaba', 'code': '395/2', 'paper_number': 2}
                ]
            },
            # Foreign Languages
            {
                'name': 'Latin',
                'code': '301',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Latin', 'code': '301/1', 'paper_number': 1},
                    {'name': 'Latin', 'code': '301/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'German',
                'code': '309',
                'is_compulsory': False,
                'papers': [
                    {'name': 'German', 'code': '309/1', 'paper_number': 1},
                    {'name': 'German', 'code': '309/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'French',
                'code': '314',
                'is_compulsory': False,
                'papers': [
                    {'name': 'French', 'code': '314/1', 'paper_number': 1},
                    {'name': 'French', 'code': '314/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Arabic',
                'code': '337',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Arabic', 'code': '337/1', 'paper_number': 1},
                    {'name': 'Arabic', 'code': '337/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Chinese',
                'code': '396',
                'is_compulsory': False,
                'papers': [
                    {'name': 'Chinese', 'code': '396/1', 'paper_number': 1},
                    {'name': 'Chinese', 'code': '396/2', 'paper_number': 2}
                ]
            },
        ]
        
        created_count = 0
        updated_count = 0
        paper_count = 0
        
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subject_data['name'],
                level='O',  # Include level in lookup to avoid duplicates
                defaults={
                    'code': subject_data['code'],
                    'is_compulsory': subject_data.get('is_compulsory', False),
                    'has_papers': len(subject_data['papers']) > 1
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created subject: {subject.name} (Compulsory: {subject.is_compulsory})'))
            else:
                # Update existing subject
                subject.code = subject_data['code']
                subject.level = 'O'
                subject.is_compulsory = subject_data.get('is_compulsory', False)
                subject.has_papers = len(subject_data['papers']) > 1
                subject.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated subject: {subject.name}'))
            
            # Create/update papers
            for paper_data in subject_data['papers']:
                paper, paper_created = SubjectPaper.objects.get_or_create(
                    subject=subject,
                    name=paper_data['name'],
                    defaults={
                        'code': paper_data['code'],
                        'paper_number': paper_data.get('paper_number'),
                        'is_active': True
                    }
                )
                
                if paper_created:
                    paper_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created paper: {paper.name}'))
                else:
                    # Update existing paper
                    paper.code = paper_data['code']
                    paper.paper_number = paper_data.get('paper_number')
                    paper.is_active = True
                    paper.save()
        
        # Summary
        compulsory_count = Subject.objects.filter(level='O', is_compulsory=True).count()
        optional_count = Subject.objects.filter(level='O', is_compulsory=False).count()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Subjects created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Subjects updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Papers created/updated: {paper_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Total O-Level subjects: {compulsory_count + optional_count}'))
        self.stdout.write(self.style.SUCCESS(f'    - Compulsory: {compulsory_count}'))
        self.stdout.write(self.style.SUCCESS(f'    - Optional: {optional_count}'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('\nAll O-Level subjects and papers have been populated successfully!'))
