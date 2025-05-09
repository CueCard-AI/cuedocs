import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from safedelete.models import SOFT_DELETE, SafeDeleteModel
from drf_helper.scope import ScopedManager, ScopingMixin 


class BaseModel(ScopingMixin, SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    id = models.UUIDField(
        verbose_name=_("id"),
        help_text=_("primary key for the record as UUID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False, help_text=_("date and time at which a record was created"),)
    updated_at = models.DateTimeField(auto_now=True, editable=False, help_text=_("date and time at which a record was last updated"),)

    objects=ScopedManager()
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Call `full_clean` before saving."""
        self.full_clean()
        super().save(*args, **kwargs)