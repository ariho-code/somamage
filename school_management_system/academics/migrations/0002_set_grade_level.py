from django.db import migrations

def set_grade_level(apps, schema_editor):
    Grade = apps.get_model("academics", "Grade")
    import re

    sixth_tokens = (
        "sixth", "s6", "s 6", "6th", "senior 6", "form 6", "upper sixth", "lower sixth",
        "upper sixth", "lower sixth", "upper-sixth", "lower-sixth", "a-level", "alevel", "a level"
    )

    for g in Grade.objects.all():
        name = (g.name or "").lower()
        level = "O"  # default
        # explicit token match
        if any(tok in name for tok in sixth_tokens):
            level = "A"
        else:
            # fallback: if there's a number >= 6 in the name treat as A-Level
            m = re.search(r"(\d+)", name)
            if m:
                try:
                    if int(m.group(1)) >= 6:
                        level = "A"
                except Exception:
                    pass
        if g.level != level:
            g.level = level
            g.save(update_fields=["level"])

def unset_grade_level(apps, schema_editor):
    Grade = apps.get_model("academics", "Grade")
    # reverse: reset all to default 'O'
    for g in Grade.objects.all():
        if g.level != "O":
            g.level = "O"
            g.save(update_fields=["level"])

class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(set_grade_level, reverse_code=unset_grade_level),
    ]