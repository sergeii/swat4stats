from django.db.models import Func, TextField, Expression, Value, F


class ArrayToString(Func):
    function = "ARRAY_TO_STRING"

    def __init__(self, expr: Expression | F | str, delimiter: str):
        super().__init__(expr, Value(delimiter), output_field=TextField())


class RegexpReplace(Func):
    function = "REGEXP_REPLACE"

    def __init__(self, expr: Expression | F | str, pattern: str, replacement: str, flags: str):
        super().__init__(
            expr, Value(pattern), Value(replacement), Value(flags), output_field=TextField()
        )
