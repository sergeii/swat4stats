from django.db.migrations.operations.base import Operation


class CreateEnumType(Operation):
    reversible = True

    def __init__(self, name, members):
        self.name = name
        self.members = members

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        db_type = schema_editor.quote_name(self.name)
        enum_values = ', '.join(f"'{member}'" for member in self.members)
        schema_editor.execute(f'CREATE TYPE {db_type} AS ENUM ({enum_values})')

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        db_type = schema_editor.quote_name(self.name)
        schema_editor.execute(f'DROP TYPE {db_type}')

    def describe(self):
        return f'Creates enum type {self.name}'
