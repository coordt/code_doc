from django.db import models
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.conf import settings

import logging

from .models import Topic, Copyright, CopyrightHolder, manage_permission_on_object
from .authors import Author

logger = logging.getLogger(__name__)


class Project(models.Model):
    """A project, may contain several authors"""

    name = models.CharField(max_length=50, unique=True)
    short_description = models.TextField(
        "short description of the project (200 chars)",
        max_length=200,
        blank=True,
        null=True,
    )
    description_mk = models.TextField(
        "text in Markdown", max_length=2500, blank=True, null=True
    )
    icon = models.ImageField(blank=True, null=True, upload_to="project_icons/")
    slug = models.SlugField()

    #: Authors of the project
    authors = models.ManyToManyField(Author)

    # the administrators of the project, have the rights to edit the project
    administrators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    #: Home page of the project
    home_page_url = models.CharField(max_length=250, null=True, blank=True)

    #: Copyright/license of the project
    copyright = models.ForeignKey(Copyright, null=True, blank=True)

    #: Copyright holders of the project
    copyright_holder = models.ManyToManyField(CopyrightHolder, blank=True)

    #: Topics covered by the project
    topics = models.ManyToManyField(Topic, blank=True)

    nb_revisions_to_keep = models.IntegerField(
        "default number of revisions to keep", default=None, blank=True, null=True
    )

    def __str__(self):
        return "%s" % (self.name)

    def get_absolute_url(self):
        return reverse("project", kwargs={"project_id": self.pk})

    class Meta:
        permissions = (
            ("project_view", "User/group can see the project"),
            ("project_administrate", "User/group administrates the project"),
            ("project_series_add", "User/group can add a series to the project"),
            (
                "project_series_delete",
                "User/group can delete a series from the project",
            ),
            ("project_artifact_add", "Can add an artifact to the project"),  # to remove
        )

    def has_user_project_administrate_permission(self, user):
        """Returns true if the user is able to administrate a project"""
        return user.is_superuser or user in self.administrators.all()

    def has_user_project_view_permission(self, user):
        """Returns true if the user is able to view the project"""
        return True

    def has_user_project_series_add_permission(self, user):
        """Returns true if the user is able to add series to the current project"""
        return self.has_user_project_administrate_permission(user)

    def has_user_project_series_delete_permission(self, user):
        """Returns true if the user is able to add series to the current project"""
        return self.has_user_project_administrate_permission(user)

    def has_user_project_artifact_add_permission(self, user):
        """Returns true if the user is able to add series to the current project"""
        return self.has_user_project_administrate_permission(user)

    def get_number_of_files(self):
        """Returns the number of files archived for a project"""
        artifact_counts = [rev.artifacts.count() for rev in self.series.all()]
        return sum(artifact_counts) if len(artifact_counts) > 0 else 0

    def get_number_of_series(self):
        """Returns the number of series for a project"""
        return self.series.count()

    def get_number_of_revisions(self):
        """Returns the number of revisions for a project"""
        return self.revisions.count()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Project, self).save(*args, **kwargs)  # Call the "real" save() method.


class ProjectRepository(models.Model):
    """Represents a project repository"""

    #: The project
    project = models.ForeignKey(Project, related_name="repositories")

    #: The related repository
    code_source_url = models.CharField(max_length=500, null=False, blank=False)

    class Meta:
        unique_together = (("project", "code_source_url"),)
        verbose_name_plural = "Project repositories"

    def get_absolute_url(self):
        return reverse("project", kwargs={"project_id": self.project.id})

    def __str__(self):
        return "[%s] %s" % (self.project.name, self.code_source_url)


class ProjectSeries(models.Model):
    """A series of a project comes with several artifacts"""

    #: The project reference
    project = models.ForeignKey(Project, related_name="series")

    #: The series name
    series = models.CharField(max_length=500)  # can be a hash

    #: Release date
    release_date = models.DateField("Release date")

    #: Indicates if a series is publicly accessible
    is_public = models.BooleanField(default=False)

    #: Description of this series
    description_mk = models.TextField(
        "Description in Markdown format", max_length=2500, blank=True, null=True
    )

    nb_revisions_to_keep = models.IntegerField(
        "default number of revisions to keep. Overrides the " "projects default",
        default=None,
        blank=True,
        null=True,
    )

    # the users and groups allowed to view the artifacts of the revision
    # and also this project series
    view_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="view_users"
    )
    view_groups = models.ManyToManyField(Group, blank=True, related_name="view_groups")

    perms_users_artifacts_add = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="perms_users_artifacts_add"
    )
    perms_groups_artifacts_add = models.ManyToManyField(
        Group, blank=True, related_name="perms_groups_artifacts_add"
    )

    perms_users_artifacts_del = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="perms_users_artifacts_del"
    )
    perms_groups_artifacts_del = models.ManyToManyField(
        Group, blank=True, related_name="perms_groups_artifacts_del"
    )

    class Meta:
        verbose_name_plural = "Project series"
        unique_together = (("project", "series"),)
        permissions = (
            ("series_view", "User/group has access to this series and its content"),
            ("series_edit", "User/group can edit the definition of this series"),
            ("series_artifact_add", "User/group is allowed to add an artifact"),
            ("series_artifact_delete", "User/group is allowed to delete an artifact"),
        )

    def __str__(self):
        return "[%s @ %s] [%s]" % (self.project.name, self.series, self.release_date)

    def get_absolute_url(self):
        return reverse(
            "project_series",
            kwargs={"project_id": self.project.pk, "series_id": self.pk},
        )

    def has_user_series_view_permission(self, userobj):
        """Returns true if the user has view permission on this series, False otherwise"""
        return (
            self.is_public
            or self.project.has_user_project_administrate_permission(userobj)
            or self.has_user_series_edit_permission(userobj)
            or self.has_user_series_artifact_add_permission(userobj)
            or manage_permission_on_object(
                userobj, self.view_users, self.view_groups, False
            )
        )

    def has_user_series_edit_permission(self, userobj):
        """Returns true if the user has edit permission on this series, False otherwise

        The edit permission if not granted if the user has the artifact add role. However, since the
        redirection to the artifact add is the session edition form, the associated view should
        also check for this permission.
        """
        return self.project.has_user_project_administrate_permission(userobj)

    def has_user_series_artifact_add_permission(self, userobj):
        """Returns True if the user can add an artifact to the serie"""
        return self.project.has_user_project_administrate_permission(
            userobj
        ) or manage_permission_on_object(
            userobj,
            self.perms_users_artifacts_add,
            self.perms_groups_artifacts_add,
            False,
        )

    def has_user_series_artifact_delete_permission(self, userobj):
        """Returns True if the user can remove an artifact from the serie"""
        return self.project.has_user_project_administrate_permission(
            userobj
        ) or manage_permission_on_object(
            userobj,
            self.perms_users_artifacts_del,
            self.perms_groups_artifacts_del,
            False,
        )

    def get_all_revisions(self):
        from code_doc.models.artifacts import Artifact

        return list(set(map(Artifact.get_revision, self.artifacts.all())))
