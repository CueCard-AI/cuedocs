from rest_framework.serializers import ModelSerializer, Serializer
from drf_helper.utils import split_levels, get_serializer_class_from_lazy_string
from drf_helper.settings import (
    NESTED_INCLUDES, 
    WILDCARD_VALUES,
    FIELDS_PARAM,
    OMIT_PARAM,
)
from drf_helper.mixins import IncludedResourcesValidationMixin
from rest_framework.fields import CharField
from django.db.models import ForeignKey
from typing import List
import json
import copy


class DynamicSerializer(ModelSerializer):
    
    def __init__(self, *args, **kwargs):
    # Don't pass the 'fields' arg up to the superclass
        request = kwargs.get('context', {}).get('request')
        value = request.GET.get('aggregate', '') if request else None
        if value:
            json_value = json.loads(value)
            fields = [] if json_value is not None else None
            fk_fields = []
            for field,annotation in json_value['annotation'].items():
                if isinstance(self.Meta.model._meta.get_field(field), ForeignKey):
                    fields.append(field+'_id')
                    fk_fields.append({field+'_id':CharField()})
                else:
                    fields.append(field)

            super(DynamicSerializer, self).__init__(*args, **kwargs)
            if fields is not None:
                allowed = set(fields)
                existing = set(self.fields)
                for field_name in existing - allowed:
                    self.fields.pop(field_name)
            for fk_field in fk_fields:
                self.fields.update(fk_field)
        
        super(DynamicSerializer, self).__init__(*args, **kwargs)


class BaseSerializer(IncludedResourcesValidationMixin, ModelSerializer):
    included_serializers = {}

    def __init__(self, *args, **kwargs):
        include = list(kwargs.pop(NESTED_INCLUDES, []))
        fields = list(kwargs.pop(FIELDS_PARAM, []))
        omit = list(kwargs.pop(OMIT_PARAM, []))
        parent = kwargs.pop("parent", None)

        super(BaseSerializer, self).__init__(*args, **kwargs)
        
        self.parent = parent
        self.expanded_fields = [] 
        self._fields_rep_applied = False

        self._field_options_base = {
            "include": include,
            "fields": fields,
            "omit": omit,
        }
        self._field_options_rep_only = {
            "include": (
                self._get_permitted_expands_from_query_param(NESTED_INCLUDES)
                if not include
                else []
            ),
            "fields": (self._get_query_param_value(FIELDS_PARAM) if not fields else []),
            "omit": (self._get_query_param_value(OMIT_PARAM) if not omit else []),
        }
        self._field_options_all = {
            "include": self._field_options_base["include"]
            + self._field_options_rep_only["include"],
            "fields": self._field_options_base["fields"]
            + self._field_options_rep_only["fields"],
            "omit": self._field_options_base["omit"]
            + self._field_options_rep_only["omit"],
        }

    def to_representation(self, instance):
        if not self._fields_rep_applied:
            self.apply_flex_fields(self.fields, self._field_options_rep_only)
            self._fields_rep_applied = True
        return super().to_representation(instance)


    def get_fields(self):
        fields = super().get_fields()
        self.apply_flex_fields(fields, self._field_options_base)
        return fields

    def apply_flex_fields(self, fields, field_options):
        include_fields, next_include_fields = split_levels(field_options["include"])
        sparse_fields, next_sparse_fields = split_levels(field_options["fields"])
        omit_fields, next_omit_fields = split_levels(field_options["omit"])

        for field_name in self._get_fields_names_to_remove(
            fields, omit_fields, sparse_fields, next_omit_fields
        ):
            fields.pop(field_name)

        for name in self._get_expanded_field_names(
            include_fields, omit_fields, sparse_fields, next_omit_fields
        ):
            self.expanded_fields.append(name)

            fields[name] = self._make_nested_included_field_serializer(
                name, next_include_fields, next_sparse_fields, next_omit_fields
            )

        return fields
    

    def _get_fields_names_to_remove(
        self,
        current_fields: List[str],
        omit_fields: List[str],
        sparse_fields: List[str],
        next_level_omits: List[str],
    ) -> List[str]:
        """
        Remove fields that are found in omit list, and if sparse names
        are passed, remove any fields not found in that list.
        """
        sparse = len(sparse_fields) > 0
        to_remove = []

        if not sparse and len(omit_fields) == 0:
            return to_remove

        for field_name in current_fields:
            should_exist = self._should_field_exist(
                field_name, omit_fields, sparse_fields, next_level_omits
            )

            if not should_exist:
                to_remove.append(field_name)

        return to_remove

    def _should_field_exist(
        self,
        field_name: str,
        omit_fields: List[str],
        sparse_fields: List[str],
        next_level_omits: List[str],
    ) -> bool:
        """
        Next level omits take form of:
        {
            'this_level_field': [field_to_omit_at_next_level]
        }
        We don't want to prematurely omit a field, eg "omit=house.rooms.kitchen"
        should not omit the entire house or all the rooms, just the kitchen.
        """
        if field_name in omit_fields and field_name not in next_level_omits:
            return False
        elif self._contains_wildcard_value(sparse_fields):
            return True
        elif len(sparse_fields) > 0 and field_name not in sparse_fields:
            return False
        else:
            return True

    def _get_expanded_field_names(
        self,
        included_fields: List[str],
        omit_fields: List[str],
        sparse_fields: List[str],
        next_level_omits: List[str],
    ) -> List[str]:
        if len(included_fields) == 0:
            return []

        if self._contains_wildcard_value(included_fields):
            included_fields = self._included_serializers.keys()

        accumulated_names = []

        for name in included_fields:
            if name not in self._included_serializers:
                continue

            if not self._should_field_exist(
                name, omit_fields, sparse_fields, next_level_omits
            ):
                continue

            accumulated_names.append(name)

        return accumulated_names

    @property
    def _included_serializers(self) -> dict:
        """It's more consistent with DRF to declare the expandable fields
        on the Meta class, however we need to support both places
        for legacy reasons."""
        if hasattr(self, "Meta") and hasattr(self.Meta, "included_serializers"):
            return self.Meta.included_serializers

        return self.included_serializers

    def _make_nested_included_field_serializer(
        self, include, nested_includes, nested_fields, nested_omit
    ):
        """
        Returns an instance of the dynamically created nested serializer.
        """
        field_options = self._included_serializers[include]

        if isinstance(field_options, tuple):
            serializer_class = field_options[0]
            settings = copy.deepcopy(field_options[1]) if len(field_options) > 1 else {}
        else:
            serializer_class = field_options
            settings = {}

        if type(serializer_class) == str:
            serializer_class = get_serializer_class_from_lazy_string(
                serializer_class
            )

        if issubclass(serializer_class, Serializer):
            settings["context"] = self.context

        if issubclass(serializer_class, BaseSerializer):
            settings["parent"] = self

            if include in nested_includes:
                settings[NESTED_INCLUDES] = nested_includes[include]
            if include in nested_fields:
                settings[FIELDS_PARAM] = nested_fields[include]
            if include in nested_omit:
                settings[OMIT_PARAM] = nested_omit[include]

        return serializer_class(**settings)

    def _get_query_param_value(self, field: str) -> List[str]:
        """
        Only allowed to examine query params if it's the root serializer.
        """
        if self.parent:
            return []

        if not hasattr(self, "context") or not self.context.get("request"):
            return []

        values = self.context["request"].query_params.get(field,'').replace(' ','')

        if not values:
            values = self.context["request"].query_params.getlist("{}[]".format(field))

        if isinstance(values, str ):
            return values.split(",")

        return values or []
    

    def _get_permitted_expands_from_query_param(self, expand_param: str) -> List[str]:
        """
        If a list of permitted_expands has been passed to context,
        make sure that the "expand" fields from the query params
        comply.
        """
        expand = self._get_query_param_value(expand_param)

        if "permitted_expands" in self.context:
            permitted_expands = self.context["permitted_expands"]

            if self._contains_wildcard_value(expand):
                return permitted_expands
            else:
                return list(set(expand) & set(permitted_expands))

        return expand

    def _contains_wildcard_value(self, expand_values: List[str]) -> bool:
        if WILDCARD_VALUES is None:
            return False
        intersecting_values = list(set(expand_values) & set(WILDCARD_VALUES))
        return len(intersecting_values) > 0