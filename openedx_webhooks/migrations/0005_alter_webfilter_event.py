# Generated by Django 3.2.19 on 2023-08-07 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_webhooks', '0004_auto_20230613_1033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='webfilter',
            name='event',
            field=models.CharField(choices=[], default='', help_text='Event type', max_length=50),
        ),
    ]
