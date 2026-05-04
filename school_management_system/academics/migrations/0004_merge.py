from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_set_grade_level"),
        ("academics", "0003_set_grade_level"),
    ]

    operations = [
        # merge migration: no operations required, just unify the graph
    ]