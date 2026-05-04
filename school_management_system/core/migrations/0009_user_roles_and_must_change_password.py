from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_aiconversation'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='must_change_password',
            field=models.BooleanField(default=False, help_text='Force password change on next login'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('platform_owner', 'Platform Owner'),
                    ('superadmin', 'Super Admin'),
                    ('school_admin', 'School Admin'),
                    ('headteacher', 'Headteacher'),
                    ('director_of_studies', 'Director of Studies'),
                    ('teacher', 'Teacher'),
                    ('bursar', 'Bursar'),
                    ('parent', 'Parent'),
                    ('student', 'Student'),
                ],
                default='parent',
                max_length=20,
            ),
        ),
    ]
