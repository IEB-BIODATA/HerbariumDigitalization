# Generated by Django 4.2.6 on 2024-03-19 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_alter_classname_options_alter_commonname_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='binnacle',
            name='description',
            field=models.CharField(blank=True, help_text='descripción', max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='binnacle',
            name='description_en',
            field=models.CharField(blank=True, help_text='descripción', max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='binnacle',
            name='description_es',
            field=models.CharField(blank=True, help_text='descripción', max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='binnacle',
            name='note',
            field=models.CharField(blank=True, help_text='descripción', null=True),
        ),
        migrations.AlterField(
            model_name='binnacle',
            name='note_en',
            field=models.CharField(blank=True, help_text='descripción', null=True),
        ),
        migrations.AlterField(
            model_name='binnacle',
            name='note_es',
            field=models.CharField(blank=True, help_text='descripción', null=True),
        ),
    ]
