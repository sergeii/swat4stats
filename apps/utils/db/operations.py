from django.db.migrations.operations.base import Operation


class CreateEnumType(Operation):
    reversible = True

    def __init__(self, name, members):
        self.name = name
        self.members = members

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute('CREATE TYPE %s AS ENUM (%s)' % (schema_editor.quote_name(self.name),
                                                               ', '.join("'%s'" % member for member in self.members)))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute('DROP TYPE %s' % schema_editor.quote_name(self.name))

    def describe(self):
        return 'Creates enum type %s' % self.name
