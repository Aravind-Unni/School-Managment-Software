# A title for each assessment, and the "exam" kind for term examinations.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessment',
            name='title',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AlterField(
            model_name='assessment',
            name='type',
            field=models.CharField(choices=[('assignment', 'assignment'), ('written_test', 'written_test'), ('practical', 'practical'), ('project', 'project'), ('exam', 'exam')], max_length=32),
        ),
    ]
