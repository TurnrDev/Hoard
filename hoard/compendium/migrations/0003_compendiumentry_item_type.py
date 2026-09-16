from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("compendium", "0002_native_system_definitions"),
    ]

    operations = [
        migrations.AddField(
            model_name="compendiumentry",
            name="item_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunSQL(
            sql="""
                UPDATE compendium_compendiumentry
                SET item_type = COALESCE(
                    NULLIF(data ->> 'item_type', ''),
                    NULLIF(data -> 'stats' -> 'type' ->> 'value', ''),
                    NULLIF(data -> 'stats' -> 'item_type' ->> 'value', ''),
                    ''
                )
                WHERE kind IN ('item', 'weapon', 'armor')
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
