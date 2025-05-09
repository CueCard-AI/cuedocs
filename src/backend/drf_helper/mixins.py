from django.conf import settings
from django.db import models
import inflection
from rest_framework.exceptions import ParseError
from drf_helper.utils import get_serializer_class_from_lazy_string


def get_included_resources(request, serializer=None):
    """Build a list of included resources."""
    include_resources_param = request.query_params.get("include")
    if include_resources_param:
        return include_resources_param.split(",")


class IncludedResourcesValidationMixin:
    """
    A serializer mixin that adds validation of `include` query parameter to
    support compound documents.

    Specification: https://jsonapi.org/format/#document-compound-documents)
    """

    def __init__(self, *args, **kwargs):
        context = kwargs.get("context")
        request = context.get("request") if context else None
        view = context.get("view") if context else None

        def validate_path(field_options, field_path, path):
            if isinstance(field_options, tuple):
                serializer_class = field_options[0]
            else:
                serializer_class = field_options
            if type(serializer_class) == str:
                serializer_class = get_serializer_class_from_lazy_string(
                    serializer_class
                )
            serializers = getattr(serializer_class, "included_serializers", None)
            if serializers is None:
                raise ParseError("This endpoint does not support the include parameter")
            this_field_name = inflection.underscore(field_path[0])
            this_included_serializer = serializers.get(this_field_name)
            if this_included_serializer is None:
                raise ParseError(
                    "This endpoint does not support the include parameter for path {}".format(
                        path
                    )
                )
            if len(field_path) > 1:
                new_included_field_path = field_path[1:]
                # We go down one level in the path
                validate_path(this_included_serializer, new_included_field_path, path)

        if request and view:
            # comment - added below line
            included_resources = get_included_resources(request)
            if included_resources is not None:
                for included_field_name in included_resources:
                    included_field_name = included_field_name.replace(' ', '')
                    included_field_path = included_field_name.split(".")
                    if "related_field" in view.kwargs:
                        this_serializer_class = view.get_related_serializer_class()
                    else:
                        this_serializer_class = view.get_serializer_class()
                    # lets validate the current path
                    validate_path(
                        this_serializer_class, included_field_path, included_field_name
                    )

        super().__init__(*args, **kwargs)


class CreatedByModelMixin(models.Model):
    """
    Add created_by property to models
    """
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name = "%(class)s_created_by")

    class Meta:
        abstract = True


class CreatedByModelViewSetMixin:
    """
    Populate created_by property from reqest.user
    """

    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id if not self.request.user.is_anonymous else None)