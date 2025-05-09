from django.conf import settings
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRF_HELPER_SETTINGS = getattr(settings, "DRF_HELPER_SETTINGS", {})
FIELDS_PARAM = DRF_HELPER_SETTINGS.get("FIELDS_PARAM", "fields")
NESTED_INCLUDES = DRF_HELPER_SETTINGS.get("NESTED_INCLUDES", "include")
OMIT_PARAM = DRF_HELPER_SETTINGS.get("OMIT_PARAM", "omit")


if "WILDCARD_INCLUDE_VALUES" in DRF_HELPER_SETTINGS:
    WILDCARD_VALUES = DRF_HELPER_SETTINGS["WILDCARD_INCLUDE_VALUES"]
elif "WILDCARD_VALUES" in DRF_HELPER_SETTINGS:
    WILDCARD_VALUES = DRF_HELPER_SETTINGS["WILDCARD_VALUES"]
else:
    WILDCARD_VALUES = ["~all", "*"]

assert isinstance(NESTED_INCLUDES, str), "'NESTED_INCLUDES' should be a string"


if type(WILDCARD_VALUES) not in (list, None):
    raise ValueError("'WILDCARD_EXPAND_VALUES' should be a list of strings or None")