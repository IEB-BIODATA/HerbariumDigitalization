from django.db import migrations


def populate_taxa_num_id(apps, schema_editor):
    # List of models to update
    models_to_update = [
        'Kingdom',
        'Division',
        'ClassName',
        'Order',
        'Family',
        'Genus',
        'Species',
        'Synonymy'
    ]

    for model_name in models_to_update:
        model = apps.get_model('catalog', model_name)
        for instance in model.objects.all():
            # Use the get_global_id() function to populate taxa_num_id
            schema_editor.execute(
                f"UPDATE {model._meta.db_table} SET taxa_num_id = get_taxa_id() WHERE id = %s",
                [instance.id]
            )
            # Assuming you want to populate another field based on taxa_num_id
            schema_editor.execute(
                f"""
                UPDATE {model._meta.db_table}
                SET taxa_id = CONCAT('https://catalogoplantas.udec.cl/taxa/', taxa_num_id)
                WHERE id = %s
                """,
                [instance.id]
            )


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0009_auto_20240531_1152'),
    ]

    operations = [
        migrations.RunPython(populate_taxa_num_id),
    ]
