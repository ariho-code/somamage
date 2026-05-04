# Generated manually to fix schema mismatch
from django.db import migrations, models
from datetime import date


def convert_years_to_dates(apps, schema_editor):
    """Convert start_year and end_year to start_date and end_date"""
    AcademicYear = apps.get_model('core', 'AcademicYear')
    for year in AcademicYear.objects.all():
        updates = {}
        # Convert year integers to dates (January 1st for start, December 31st for end)
        if hasattr(year, 'start_year') and year.start_year:
            updates['start_date'] = date(year.start_year, 1, 1)
        if hasattr(year, 'end_year') and year.end_year:
            updates['end_date'] = date(year.end_year, 12, 31)
        # Generate name if missing
        if not year.name or year.name == '':
            if hasattr(year, 'start_year') and hasattr(year, 'end_year') and year.start_year and year.end_year:
                updates['name'] = f"{year.start_year}-{year.end_year}"
            else:
                updates['name'] = "Academic Year"
        if updates:
            AcademicYear.objects.filter(pk=year.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Add new fields as nullable first
        migrations.AddField(
            model_name='academicyear',
            name='name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='academicyear',
            name='start_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='academicyear',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),
        # Migrate data
        migrations.RunPython(convert_years_to_dates, migrations.RunPython.noop),
        # Make fields non-nullable
        migrations.AlterField(
            model_name='academicyear',
            name='start_date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='academicyear',
            name='end_date',
            field=models.DateField(),
        ),
        # Remove old fields
        migrations.RemoveField(
            model_name='academicyear',
            name='start_year',
        ),
        migrations.RemoveField(
            model_name='academicyear',
            name='end_year',
        ),
        # Update Term model if needed
        migrations.AlterField(
            model_name='term',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='term',
            name='start_date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='term',
            name='end_date',
            field=models.DateField(),
        ),
    ]

