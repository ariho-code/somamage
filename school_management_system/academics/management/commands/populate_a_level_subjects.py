from django.core.management.base import BaseCommand
from academics.models import Subject, SubjectPaper


class Command(BaseCommand):
    help = 'Populate all A-Level subjects and papers from Ugandan UACE curriculum'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate A-Level subjects...'))
        
        # Subject data with papers
        subjects_data = [
            # Compulsory and Subsidiary
            {
                'name': 'General Paper',
                'code': 'S101',
                'papers': [
                    {'name': 'General Paper', 'code': 'S101/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Subsidiary Mathematics',
                'code': 'S475',
                'papers': [
                    {'name': 'Subsidiary Mathematics', 'code': 'S475/1', 'paper_number': 1}
                ]
            },
            {
                'name': 'Subsidiary ICT',
                'code': 'S850',
                'papers': [
                    {'name': 'Subsidiary ICT', 'code': 'S850/1', 'paper_number': 1},
                    {'name': 'Practical', 'code': 'S850/2', 'paper_number': 2},
                    {'name': 'Practical', 'code': 'S850/3', 'paper_number': 3}
                ]
            },
            # Humanities & Social Sciences
            {
                'name': 'History',
                'code': 'P210',
                'papers': [
                    {'name': 'National Movements & New States', 'code': 'P210/1', 'paper_number': 1},
                    {'name': 'Economic & Social History of East Africa', 'code': 'P210/2', 'paper_number': 2},
                    {'name': 'European History 1789–1970', 'code': 'P210/3', 'paper_number': 3},
                    {'name': 'World Affairs since 1939', 'code': 'P210/4', 'paper_number': 4},
                    {'name': 'Theory of Government & Constitutional Development', 'code': 'P210/5', 'paper_number': 5},
                    {'name': 'History of Africa 1855–1914', 'code': 'P210/6', 'paper_number': 6}
                ]
            },
            {
                'name': 'Economics',
                'code': 'P220',
                'papers': [
                    {'name': 'Economics', 'code': 'P220/1', 'paper_number': 1},
                    {'name': 'Economics', 'code': 'P220/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Geography',
                'code': 'P250',
                'papers': [
                    {'name': 'Geography', 'code': 'P250/1', 'paper_number': 1},
                    {'name': 'Geography', 'code': 'P250/2', 'paper_number': 2},
                    {'name': 'Geography', 'code': 'P250/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Entrepreneurship Education',
                'code': 'P230',
                'papers': [
                    {'name': 'Entrepreneurship Education', 'code': 'P230/1', 'paper_number': 1},
                    {'name': 'Entrepreneurship Education', 'code': 'P230/2', 'paper_number': 2},
                    {'name': 'Entrepreneurship Education', 'code': 'P230/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Islamic Religious Education (IRE)',
                'code': 'P235',
                'papers': [
                    {'name': 'The Glorious Qur\'an', 'code': 'P235/1', 'paper_number': 1},
                    {'name': 'Hadith & Fiqh', 'code': 'P235/2', 'paper_number': 2},
                    {'name': 'History of Islam', 'code': 'P235/3', 'paper_number': 3},
                    {'name': 'Islam in Africa', 'code': 'P235/4', 'paper_number': 4}
                ]
            },
            {
                'name': 'Christian Religious Education (CRE)',
                'code': 'P245',
                'papers': [
                    {'name': 'The Old Testament', 'code': 'P245/1', 'paper_number': 1},
                    {'name': 'The New Testament', 'code': 'P245/2', 'paper_number': 2},
                    {'name': 'Christianity in East Africa', 'code': 'P245/3', 'paper_number': 3},
                    {'name': 'Social & Ethical Issues', 'code': 'P245/4', 'paper_number': 4}
                ]
            },
            # Sciences
            {
                'name': 'Principal Mathematics',
                'code': 'P425',
                'papers': [
                    {'name': 'Principal Mathematics', 'code': 'P425/1', 'paper_number': 1},
                    {'name': 'Principal Mathematics', 'code': 'P425/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Chemistry',
                'code': 'P525',
                'papers': [
                    {'name': 'Chemistry', 'code': 'P525/1', 'paper_number': 1},
                    {'name': 'Chemistry', 'code': 'P525/2', 'paper_number': 2},
                    {'name': 'Chemistry Practical', 'code': 'P525/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Biology',
                'code': 'P530',
                'papers': [
                    {'name': 'Biology', 'code': 'P530/1', 'paper_number': 1},
                    {'name': 'Biology', 'code': 'P530/2', 'paper_number': 2},
                    {'name': 'Biology Practical', 'code': 'P530/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Physics',
                'code': 'P510',
                'papers': [
                    {'name': 'Physics', 'code': 'P510/1', 'paper_number': 1},
                    {'name': 'Physics', 'code': 'P510/2', 'paper_number': 2},
                    {'name': 'Physics Practical', 'code': 'P510/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Agriculture Principles & Practices',
                'code': 'P515',
                'papers': [
                    {'name': 'Agriculture Principles & Practice', 'code': 'P515/1', 'paper_number': 1},
                    {'name': 'Agriculture Principles & Practice', 'code': 'P515/2', 'paper_number': 2},
                    {'name': 'Agriculture Principles & Practices Practical', 'code': 'P515/3', 'paper_number': 3}
                ]
            },
            # Languages & Literature
            {
                'name': 'Literature in English',
                'code': 'P310',
                'papers': [
                    {'name': 'Prose & Poetry', 'code': 'P310/1', 'paper_number': 1},
                    {'name': 'Plays', 'code': 'P310/2', 'paper_number': 2},
                    {'name': 'Novels', 'code': 'P310/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Fasihi ya Kiswahili',
                'code': 'P320',
                'papers': [
                    {'name': 'Nathari na Ushairi', 'code': 'P320/1', 'paper_number': 1},
                    {'name': 'Tamthilia', 'code': 'P320/2', 'paper_number': 2},
                    {'name': 'Riwaya', 'code': 'P320/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'French',
                'code': 'P330',
                'papers': [
                    {'name': 'Oral French', 'code': 'P330/1', 'paper_number': 1},
                    {'name': 'Language & Reading Comprehension', 'code': 'P330/2', 'paper_number': 2},
                    {'name': 'Literature & Background Studies', 'code': 'P330/3', 'paper_number': 3},
                    {'name': 'Composition & Translation', 'code': 'P330/4', 'paper_number': 4}
                ]
            },
            {
                'name': 'German',
                'code': 'P340',
                'papers': [
                    {'name': 'Essay', 'code': 'P340/1', 'paper_number': 1},
                    {'name': 'Reading Comprehension & Commentary', 'code': 'P340/2', 'paper_number': 2},
                    {'name': 'Prescribed Texts', 'code': 'P340/3', 'paper_number': 3},
                    {'name': 'Orals', 'code': 'P340/4', 'paper_number': 4}
                ]
            },
            {
                'name': 'Latin',
                'code': 'P350',
                'papers': [
                    {'name': 'Prose Composition', 'code': 'P350/1', 'paper_number': 1},
                    {'name': 'Unprepared Translation', 'code': 'P350/2', 'paper_number': 2},
                    {'name': 'Prescribed Texts', 'code': 'P350/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Arabic',
                'code': 'P370',
                'papers': [
                    {'name': 'Grammar, Morphology & Composition', 'code': 'P370/1', 'paper_number': 1},
                    {'name': 'Comprehension, Summary & Translation', 'code': 'P370/2', 'paper_number': 2},
                    {'name': 'Literature: Prose, Poetry, Novels & Plays', 'code': 'P370/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Chinese',
                'code': 'P372',
                'papers': [
                    {'name': 'Chinese Oral', 'code': 'P372/1', 'paper_number': 1},
                    {'name': 'Chinese', 'code': 'P372/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Luganda',
                'code': 'P360',
                'papers': [
                    {'name': 'Grammar and Culture', 'code': 'P360/1', 'paper_number': 1},
                    {'name': 'Translation, Composition, Comprehension & Summary', 'code': 'P360/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P360/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Leb Acoli',
                'code': 'P361',
                'papers': [
                    {'name': 'Leb Acoli', 'code': 'P361/1', 'paper_number': 1},
                    {'name': 'Leb Acoli', 'code': 'P361/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P361/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Leb Lango',
                'code': 'P362',
                'papers': [
                    {'name': 'Leb Lango', 'code': 'P362/1', 'paper_number': 1},
                    {'name': 'Leb Lango', 'code': 'P362/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P362/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'LugbaraTi',
                'code': 'P363',
                'papers': [
                    {'name': 'LugbaraTi', 'code': 'P363/1', 'paper_number': 1},
                    {'name': 'Translation', 'code': 'P363/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P363/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Runyankore/Rukiga',
                'code': 'P364',
                'papers': [
                    {'name': 'Grammar and Culture', 'code': 'P364/1', 'paper_number': 1},
                    {'name': 'Composition', 'code': 'P364/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P364/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Lusoga',
                'code': 'P366',
                'papers': [
                    {'name': 'Lusoga', 'code': 'P366/1', 'paper_number': 1},
                    {'name': 'Comprehension', 'code': 'P366/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P366/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Ateso',
                'code': 'P367',
                'papers': [
                    {'name': 'Ateso', 'code': 'P367/1', 'paper_number': 1},
                    {'name': 'Ateso', 'code': 'P367/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P367/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Dhopadhola',
                'code': 'P368',
                'papers': [
                    {'name': 'Dhopadhola', 'code': 'P368/1', 'paper_number': 1},
                    {'name': 'Dhopadhola', 'code': 'P368/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P368/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Runyoro/Rutoro',
                'code': 'P369',
                'papers': [
                    {'name': 'Runyoro/Rutoro', 'code': 'P369/1', 'paper_number': 1},
                    {'name': 'Runyoro/Rutoro', 'code': 'P369/2', 'paper_number': 2},
                    {'name': 'Literature', 'code': 'P369/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Lumasaaba',
                'code': 'P371',
                'papers': [
                    {'name': 'Lumasaaba', 'code': 'P371/1', 'paper_number': 1},
                    {'name': 'Lumasaaba', 'code': 'P371/2', 'paper_number': 2},
                    {'name': 'Lumasaaba', 'code': 'P371/3', 'paper_number': 3}
                ]
            },
            # Arts & Vocational
            {
                'name': 'Art',
                'code': 'P615',
                'papers': [
                    {'name': 'Drawing/Painting from Nature & Still-Life', 'code': 'P615/1', 'paper_number': 1},
                    {'name': 'Study of a Living Person (Alt A) & Imaginative Composition in Colour (Alt B) – Sketching & Test', 'code': 'P615/2', 'paper_number': 2},
                    {'name': 'Craft A: Graphic Design Planning & Test', 'code': 'P615/3', 'paper_number': 3},
                    {'name': 'Craft B: Studio Technology Theory', 'code': 'P615/4', 'paper_number': 4},
                    {'name': 'Historical and Critical', 'code': 'P615/5', 'paper_number': 5}
                ]
            },
            {
                'name': 'Music',
                'code': 'P620',
                'papers': [
                    {'name': 'Practical', 'code': 'P620/1', 'paper_number': 1},
                    {'name': 'Aural', 'code': 'P620/2', 'paper_number': 2},
                    {'name': 'Harmony & Composition', 'code': 'P620/3', 'paper_number': 3},
                    {'name': 'Literature', 'code': 'P620/4', 'paper_number': 4}
                ]
            },
            {
                'name': 'Clothing and Textiles',
                'code': 'P630',
                'papers': [
                    {'name': 'Clothing and Textiles', 'code': 'P630/1', 'paper_number': 1},
                    {'name': 'Clothing and Textiles Practical', 'code': 'P630/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Foods and Nutrition',
                'code': 'P640',
                'papers': [
                    {'name': 'Foods and Nutrition', 'code': 'P640/1', 'paper_number': 1},
                    {'name': 'Foods and Nutrition', 'code': 'P640/2', 'paper_number': 2},
                    {'name': 'Foods and Nutrition Practical', 'code': 'P640/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Geometrical & Mechanical Drawing',
                'code': 'P710',
                'papers': [
                    {'name': 'Geometrical & Mechanical Drawing', 'code': 'P710/1', 'paper_number': 1},
                    {'name': 'Geometrical & Mechanical Drawing', 'code': 'P710/2', 'paper_number': 2}
                ]
            },
            {
                'name': 'Geometrical & Building Drawing',
                'code': 'P720',
                'papers': [
                    {'name': 'Geometrical & Building Drawing', 'code': 'P720/1', 'paper_number': 1},
                    {'name': 'Geometrical & Building Drawing', 'code': 'P720/2', 'paper_number': 2},
                    {'name': 'Theory of Building Construction', 'code': 'P720/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Woodwork',
                'code': 'P730',
                'papers': [
                    {'name': 'Woodwork', 'code': 'P730/1', 'paper_number': 1},
                    {'name': 'Woodwork', 'code': 'P730/2', 'paper_number': 2},
                    {'name': 'Woodwork', 'code': 'P730/3', 'paper_number': 3}
                ]
            },
            {
                'name': 'Engineering Metalwork',
                'code': 'P740',
                'papers': [
                    {'name': 'Engineering Metalwork', 'code': 'P740/1', 'paper_number': 1},
                    {'name': 'Engineering Metalwork', 'code': 'P740/2', 'paper_number': 2}
                ]
            },
        ]
        
        created_count = 0
        updated_count = 0
        paper_count = 0
        
        for subject_data in subjects_data:
            # Try to get existing subject by name and level
            try:
                subject = Subject.objects.get(name=subject_data['name'], level='A')
                created = False
            except Subject.DoesNotExist:
                # If doesn't exist, create it
                subject = Subject.objects.create(
                    name=subject_data['name'],
                    code=subject_data['code'],
                    level='A',
                    has_papers=len(subject_data['papers']) > 1
                )
                created = True
            except Subject.MultipleObjectsReturned:
                # If multiple exist, take the first one
                subject = Subject.objects.filter(name=subject_data['name'], level='A').first()
                created = False
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created subject: {subject.name}'))
            else:
                # Update existing subject
                subject.code = subject_data['code']
                subject.level = 'A'
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
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Subjects created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Subjects updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Papers created/updated: {paper_count}'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('\nAll A-Level subjects and papers have been populated successfully!'))
