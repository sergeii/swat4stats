# Generated by Django 4.1.7 on 2023-07-24 17:09

from django.contrib.postgres.search import SearchVectorField
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0005_alias_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="alias",
            name="search",
            field=SearchVectorField(help_text="TSV field for full text search.", null=True),
        ),
        migrations.RunSQL(
            r"""
            CREATE OR REPLACE FUNCTION update_or_create_alias_reindex_search()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search :=
                    setweight(to_tsvector('simple', new.name), 'A')
                    || ' ' ||
                    setweight(to_tsvector('simple',
                        regexp_replace(
                            regexp_replace(new.name, '([a-z])([A-Z])', '\1 \2', 'g'),
                            '\d+',
                            ''
                        )
                    ), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER update_or_create_alias_reindex_search BEFORE INSERT OR UPDATE OF name
            ON tracker_alias FOR EACH ROW EXECUTE FUNCTION update_or_create_alias_reindex_search();
        """
        ),
    ]
