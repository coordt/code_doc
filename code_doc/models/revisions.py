from django.core.urlresolvers import reverse
from django.db import models

import logging

from .projects import Project

logger = logging.getLogger(__name__)


class Revision(models.Model):
    """A Revision is a collection of artifacts, that were produced by the same
       state of the Project's code."""

    revision = models.CharField(max_length=200)  # can be anything
    project = models.ForeignKey(Project, related_name="revisions")
    commit_time = models.DateTimeField(
        "Time of creation",
        auto_now_add=True,
        help_text="Automatic field that is set when this revision is created",
    )

    def __str__(self):
        return "[%s] %s" % (self.project.name, self.revision)

    def get_all_referencing_series(self):
        list_of_series = []
        for artifact in self.artifacts.all():
            list_of_series += artifact.project_series.all()
        return list(set(list_of_series))

    def get_absolute_url(self):
        return reverse(
            "project_revision",
            kwargs={"project_id": self.project.pk, "revision_id": self.id},
        )

    class Meta:
        verbose_name_plural = "Project revision"
        get_latest_by = "commit_time"
        unique_together = ("project", "revision")
        permissions = (
            ("revision_view", "User/group has access to this revision and its content"),
        )

    def has_user_revision_view_permission(self, userobj):
        """Returns true if the user has view permission on this revision, False otherwise"""

        # Access to one of the series grants access to the revision
        series_access = False
        for series in self.get_all_referencing_series():
            if series.has_user_series_view_permission(userobj):
                series_access = True
                break

        return series_access or self.project.has_user_project_administrate_permission(
            userobj
        )


class Branch(models.Model):
    """A Branch is referenced by a Revision in order to group Revisions by the branch it was
       created from.

       It stores how many Revisions we allow this Branch to have."""

    name = models.CharField(max_length=100)
    nb_revisions_to_keep = models.IntegerField(
        "default number of revisions to keep. Overrides the "
        "projects and series default",
        default=None,
        blank=True,
        null=True,
    )
    revisions = models.ManyToManyField(Revision, related_name="branches")
