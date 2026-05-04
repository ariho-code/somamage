# Manually created migration to safely delete models and update fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_merge'),
    ]

    operations = [
        # First add the level field to Grade
        migrations.AddField(
            model_name='grade',
            name='level',
            field=models.CharField(choices=[('O', 'O-Level'), ('A', 'A-Level')], default='O', max_length=1),
        ),
        # Delete models - Django will handle foreign key constraints
        migrations.DeleteModel(
            name='Exam',
        ),
        migrations.DeleteModel(
            name='GradeScale',
        ),
        migrations.DeleteModel(
            name='StudentMark',
        ),
        # Remove school field from Subject (if it exists)
        migrations.RemoveField(
            model_name='subject',
            name='school',
        ),
    ]

