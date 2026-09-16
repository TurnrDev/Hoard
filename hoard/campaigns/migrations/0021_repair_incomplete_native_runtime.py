from django.db import migrations


def table_columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )

    return {column.name for column in description}


def repair_incomplete_native_runtime(apps, schema_editor):
    """Complete databases that applied migration 0020 while it was in development."""
    Campaign = apps.get_model("campaigns", "Campaign")
    Character = apps.get_model("campaigns", "Character")
    CharacterNativeEvent = apps.get_model("campaigns", "CharacterNativeEvent")

    missing_fields = (
        (Campaign, "native_system_id"),
        (Campaign, "native_system_source"),
        (Character, "native_system_source"),
    )

    for model, field_name in missing_fields:
        field = model._meta.get_field(field_name)
        columns = table_columns(schema_editor, model._meta.db_table)

        if field.column not in columns:
            schema_editor.add_field(model, field)

    existing_tables = set(schema_editor.connection.introspection.table_names())

    if CharacterNativeEvent._meta.db_table not in existing_tables:
        schema_editor.create_model(CharacterNativeEvent)


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0020_character_native_runtime"),
    ]

    operations = [
        migrations.RunPython(
            repair_incomplete_native_runtime,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
