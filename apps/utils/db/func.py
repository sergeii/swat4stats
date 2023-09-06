from functools import reduce

from django.contrib.postgres.search import SearchVector
from django.db.models import Expression, F, Func, TextField, Value


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
    norm_whitespace = (r"\s+", " ", "g")
    norm_camelcase = (r"([a-z])([A-Z])", r"\1 \2", "g")
    norm_digits = (r"\d+", "", "g")
    norm_alnum = (r"\W+", " ", "g")

    rules: list[tuple[tuple[str, str, str], ...]] = [
        # replace camel case with spaces,
        # so that "JohnDoe" becomes "John Doe"
        (norm_camelcase,),
        (
            # remove all digits,
            # so that "JohnDoe123" becomes "JohnDoe",
            norm_digits,
        ),
        (
            # replace all non-letter characters with spaces,
            # so that "John-Doe" becomes "John Doe"
            norm_alnum,
            norm_whitespace,
        ),
        (
            # finally, apply all rules above in a single pass,
            # so that "Super.JohnDoe.123" becomes "Super John Doe"
            norm_camelcase,
            norm_digits,
            norm_alnum,
            norm_whitespace,
        ),
    ]

    expressions = [
        reduce(lambda expr, rule: RegexpReplace(expr, *rule), rule, names_expr) for rule in rules
    ]

    return SearchVector(*expressions, config=config, weight=weight)
