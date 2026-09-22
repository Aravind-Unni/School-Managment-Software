# The fee plan and monthly amount a bus's pupils are billed under.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bus',
            name='fee_plan_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bus',
            name='monthly_fee_paise',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
