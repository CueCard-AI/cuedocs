import importlib
from typing import Optional, Tuple
from collections.abc import Iterable


def get_serializer_class_from_lazy_string(full_lazy_path: str):
    path_parts = full_lazy_path.split(".")
    class_name = path_parts.pop()
    path = ".".join(path_parts)
    serializer_class, error = import_serializer_class(path, class_name)

    if error and not path.endswith(".serializers"):
        serializer_class, error = import_serializer_class(
            path + ".serializers", class_name
        )

    if serializer_class:
        return serializer_class

    raise Exception(error)


def import_serializer_class( path: str, class_name: str
) -> Tuple[Optional[str], Optional[str]]:
    try:
        module = importlib.import_module(path)
    except ImportError:
        return (
            None,
            "No module found at path: %s when trying to import %s"
            % (path, class_name),
        )

    try:
        return getattr(module, class_name), None
    except AttributeError:
        return None, "No class %s class found in module %s" % (path, class_name)
    

def split_levels(fields):
    """
        Convert dot-notation such as ['a', 'a.b', 'a.d', 'c'] into
        current-level fields ['a', 'c'] and next-level fields
        {'a': ['b', 'd']}.
    """
    first_level_fields = []
    next_level_fields = {}

    if not fields:
        return first_level_fields, next_level_fields

    assert isinstance(
        fields, Iterable
    ), "`fields` must be iterable (e.g. list, tuple, or generator)"

    if isinstance(fields, str):
        fields = [a.strip() for a in fields.split(",") if a.strip()]
    for e in fields:
        if "." in e:
            first_level, next_level = e.split(".", 1)
            first_level_fields.append(first_level)
            next_level_fields.setdefault(first_level, []).append(next_level)
        else:
            first_level_fields.append(e)

    first_level_fields = list(set(first_level_fields))
    return first_level_fields, next_level_fields
    