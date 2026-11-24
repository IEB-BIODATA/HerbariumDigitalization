from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0027_classname_deleted_division_deleted_family_deleted_and_more'),
    ]

    operations = [
        migrations.RunSQL("""
            DROP MATERIALIZED VIEW IF EXISTS synonymy_view;
        """),
        migrations.RunSQL("""
            DROP MATERIALIZED VIEW IF EXISTS catalog_view;
        """),
        migrations.RunSQL("""
            CREATE MATERIALIZED VIEW catalog_view AS
            SELECT species.id,
                   species.id_taxa,
                   species.unique_taxon_id,
                   species.taxon_id,
                   species.deleted,
                   kingdom.id      AS kingdom_id,
                   kingdom.name    AS kingdom,
                   division.id     AS division_id,
                   division.name   AS division,
                   classname.id    AS classname_id,
                   classname.name  AS classname,
                   "order".id      AS order_id,
                   "order".name    AS "order",
                   family.id       AS family_id,
                   family.name     AS family,
                   genus.id        AS genus_id,
                   genus.name      AS genus,
                   species.scientific_name,
                   species.scientific_name_full,
                   species.specific_epithet,
                   species.scientific_name_authorship,
                   species.subspecies,
                   species.ssp_authorship,
                   species.variety,
                   species.variety_authorship,
                   species.form,
                   species.form_authorship,
                   species.in_argentina,
                   species.in_bolivia,
                   species.in_peru,
                   status.name     AS status,
                   status.name_es  AS status_es,
                   status.name_en  AS status_en,
                   species.minimum_height,
                   species.maximum_height,
                   species.notes,
                   species.type_id,
                   species.determined,
                   species.id_taxa_origin,
                   species.created_at,
                   species.updated_at,
                   "user".username AS created_by
            FROM catalog_species species
                 JOIN auth_user "user" ON species.created_by_id = "user".id
                 JOIN catalog_genus genus ON species.genus_id = genus.id
                 JOIN catalog_family family ON genus.family_id = family.id
                 JOIN catalog_order "order" ON family.order_id = "order".id
                 JOIN catalog_classname classname ON "order".classname_id = classname.id
                 JOIN catalog_division division ON classname.division_id = division.id
                 JOIN catalog_kingdom kingdom ON division.kingdom_id = kingdom.id
                 LEFT JOIN catalog_status status ON species.status_id = status.id
            WHERE NOT species.deleted;
        """),
        migrations.RunSQL("""
            CREATE UNIQUE INDEX catalog_view_id_idx
                ON catalog_view (id);
        """),
        migrations.RunSQL("""
            CREATE MATERIALIZED VIEW synonymy_view AS
            SELECT synonymy.id,
                   species_id,
                   species.id_taxa,
                   species.scientific_name AS species_scientific_name,
                   synonymy.scientific_name,
                   synonymy.scientific_name_full,
                   synonymy.deleted,
                   synonymy.genus,
                   synonymy.specific_epithet,
                   synonymy.scientific_name_authorship,
                   synonymy.subspecies,
                   synonymy.ssp_authorship,
                   synonymy.variety,
                   synonymy.variety_authorship,
                   synonymy.form,
                   synonymy.form_authorship,
                   synonymy.created_at,
                   synonymy.updated_at,
                   "user".username          AS created_by
            FROM catalog_synonymy synonymy
                LEFT JOIN catalog_species species ON synonymy.species_id = species.id
                LEFT JOIN auth_user "user" ON synonymy.created_by_id = "user".id
            WHERE NOT synonymy.deleted;
        """),
        migrations.RunSQL("""
            CREATE UNIQUE INDEX synonymy_view_id_idx
                ON synonymy_view (id);
        """),
    ]
