# A pupil's photograph.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0004_student_details'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentPhoto',
            fields=[
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='registry.student')),
                ('school_id', models.UUIDField(db_index=True)),
                ('content_type', models.CharField(max_length=32)),
                ('data', models.BinaryField()),
                ('updated_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'registry_student_photo',
            },
        ),
    ]
