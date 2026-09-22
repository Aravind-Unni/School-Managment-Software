# Admission-register details on the student record.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0003_school_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='details',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
