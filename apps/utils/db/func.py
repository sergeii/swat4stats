from django.contrib.postgres.search import SearchVector
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


def normalized_names_search_vector(
    names_expr: Expression | F, config: str, weight: str
) -> SearchVector:
    return SearchVector(
        RegexpReplace(
            RegexpReplace(
                # replace camel case with spaces,
                # so that "JohnDoe" becomes "John Doe"
                names_expr,
                r"([a-z])([A-Z])",
                r"\1 \2",
                "g",
            ),
            # remove all digits,
            # so that "John Doe 123" becomes "John Doe"
            r"\d+",
            "",
            "g",
        ),
        config=config,
        weight=weight,
    )
