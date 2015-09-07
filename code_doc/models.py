from django.db import models

# from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.conf import settings

import datetime
import os
import logging
import urllib

# logger for this file
logger = logging.getLogger(__name__)


def get_author_image_location(instance, filename):

    if (instance.firstname is not "") and (instance.lastname is not ""):
        author_name = instance.firstname + instance.lastname
    else:
        author_name = 'default'

    media_relative_dir = os.path.join('author_images',
                                      author_name)

    root_dir = os.path.join(settings.MEDIA_ROOT, media_relative_dir)

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    return os.path.join(media_relative_dir, filename)


class Author(models.Model):
    """An author, may appear in several projects, and is not someone that is
    allowed to login (not a user of Django)."""
    lastname = models.CharField(max_length=50)
    firstname = models.CharField(max_length=50)
    gravatar_email = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=50,
                              unique=True,
                              db_index=True)
    home_page_url = models.CharField(max_length=250, blank=True)
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                       related_name='author',
                                       blank=True,
                                       null=True,
                                       help_text='The Django User, this Author is corresponding to.')
    image = models.ImageField(blank=True, null=True, upload_to=get_author_image_location)

    class Meta:
        permissions = (
            ("author_edit", "Can edit the Author's details"),
        )

    def __unicode__(self):
        return "%s %s (%s)" % (self.firstname, self.lastname, self.email)

    def has_user_author_edit_permission(self, user):
        """In order for a Django User to be allowed to edit the details of an Author,
           he has to be a superuser or be the User, this Author is linked to.
        """
        return user.is_superuser or (hasattr(user, 'author') and (user.author == self))

    def get_absolute_url(self):
        return reverse('author', kwargs={'author_id': self.pk})


class CopyrightHolder(models.Model):
    """The entity that holds the copyright over a product"""
    name = models.CharField(max_length=50)
    year = models.IntegerField(default=datetime.datetime.now().year)

    def __unicode__(self):
        return "%s (%d)" % (self.name, self.year)


class Copyright(models.Model):
    """The copyright type (BSD + version, MIT + version etc)"""
    name = models.CharField(max_length=50)
    content = models.TextField(max_length=2500)
    url = models.CharField(max_length=50)

    def __unicode__(self):
        return "%s @ %s" % (self.name, self.url)


class Topic(models.Model):
    """A topic associated to a project"""
    name = models.CharField(max_length=20)
    description_mk = models.TextField('Description in Markdown format',
                                      max_length=200, blank=True, null=True)

    def __unicode__(self):
        return "%s" % (self.name)


def manage_permission_on_object(userobj, user_permissions, group_permissions,
                                default=None):
    """If (in order)

    * userobj is a superuser, then true
    * userobj is not active, then default. If default is None, then True
    * no credentials set in the groups user_permissions / group_permissions,
      the default. If default is None, then True.
    * userobj in user_permissions, then True
    * userobj in one of the groups in group_permissions, the True
    * otherwise False

    """
    if userobj.is_superuser:
        return True

    if not userobj.is_active:
        return default if default is not None else True

    # no permission has been set, so no restriction by default
    if user_permissions.count() == 0 and group_permissions.count() == 0:
        return default if default is not None else True

    if user_permissions.filter(id=userobj.id).count() > 0:
        return True

    return group_permissions.filter(id__in=[g.id for g in userobj.groups.all()]).count() > 0


class Project(models.Model):
    """A project, may contain several authors"""
    name = models.CharField(max_length=50, unique=True)
    short_description = models.TextField('short description of the project (200 chars)',
                                         max_length=200,
                                         blank=True,
                                         null=True)
    description_mk = models.TextField('text in Markdown', max_length=2500, blank=True, null=True)
    icon = models.ImageField(blank=True, null=True, upload_to='project_icons/')
    slug = models.SlugField()

    authors = models.ManyToManyField(Author)

    # the administrators of the project, have the rights to edit the
    administrators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    home_page_url = models.CharField(max_length=250, null=True, blank=True)
    code_source_url = models.CharField(max_length=250, null=True, blank=True)
    copyright = models.ForeignKey(Copyright, null=True, blank=True)
    copyright_holder = models.ManyToManyField(CopyrightHolder, blank=True)

    topics = models.ManyToManyField(Topic, blank=True)

    nb_revisions_to_keep = models.IntegerField("default number of revisions to keep",
                                               default=None,
                                               blank=True,
                                               null=True)

    def __unicode__(self):
        return "%s" % (self.name)

    class Meta:
        permissions = (
            ("project_view", "User/group can see the project"),
            ("project_administrate", "User/group administrates the project"),
            ("project_series_add", "User/group can add a series to the project"),
            ("project_series_delete", "User/group can delete a series from the project"),
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


class ProjectSeries(models.Model):
    """A series of a project comes with several artifacts"""
    project = models.ForeignKey(Project, related_name="series")
    series = models.CharField(max_length=500)  # can be a hash
    release_date = models.DateField('Release date')
    is_public = models.BooleanField(default=False)
    description_mk = models.TextField('Description in Markdown format',
                                      max_length=2500,
                                      blank=True,
                                      null=True)

    nb_revisions_to_keep = models.IntegerField("default number of revisions to keep. Overrides the "
                                               "projects default",
                                               default=None,
                                               blank=True,
                                               null=True)

    # the users and groups allowed to view the artifacts of the revision
    # and also this project series
    view_users = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                        blank=True,
                                        related_name='view_users')
    view_groups = models.ManyToManyField(Group,
                                         blank=True,
                                         related_name='view_groups')

    perms_users_artifacts_add = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                                       blank=True,
                                                       related_name='perms_users_artifacts_add')
    perms_groups_artifacts_add = models.ManyToManyField(Group,
                                                        blank=True,
                                                        related_name='perms_groups_artifacts_add')

    perms_users_artifacts_del = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                                       blank=True,
                                                       related_name='perms_users_artifacts_del')
    perms_groups_artifacts_del = models.ManyToManyField(Group,
                                                        blank=True,
                                                        related_name='perms_groups_artifacts_del')

    class Meta:
        unique_together = (("project", "series"),)
        permissions = (
            ("series_view", "User/group has access to this serie and its content"),
            ("series_edit", "User/group can edit the definition of this series"),
            ("series_artifact_add", "User/group is allowed to add an artifact"),
            ("series_artifact_delete", "User/group is allowed to delete an artifact"),
        )

    def __unicode__(self):
        return "[%s @ %s] [%s]" % (self.project.name, self.series, self.release_date)

    def get_absolute_url(self):
        return reverse('project_series', kwargs={'project_id': self.project.pk,
                                                 'series_id': self.pk})

    def has_user_series_view_permission(self, userobj):
        """Returns true if the user has view permission on this series, False otherwise"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            self.has_user_series_edit_permission(userobj) or \
            manage_permission_on_object(userobj, self.view_users, self.view_groups, False)

    def has_user_series_edit_permission(self, userobj):
        """Returns true if the user has edit permission on this series, False otherwise"""
        return self.is_public or \
            self.has_user_series_artifact_add_permission(userobj) or \
            self.project.has_user_project_administrate_permission(userobj) or \
            manage_permission_on_object(userobj, self.view_users, self.view_groups, False)

    def has_user_series_artifact_add_permission(self, userobj):
        """Returns True if the user can add an artifact to the serie"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            self.has_user_series_artifact_delete_permission(userobj) or \
            manage_permission_on_object(userobj,
                                        self.perms_users_artifacts_add,
                                        self.perms_groups_artifacts_add, False)

    def has_user_series_artifact_delete_permission(self, userobj):
        """Returns True if the user can remove an artifact from the serie"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            manage_permission_on_object(userobj,
                                        self.perms_users_artifacts_del,
                                        self.perms_groups_artifacts_del, False)

    def get_all_revisions(self):
        return list(set(map(Artifact.get_revision, self.artifacts.all())))


class Revision(models.Model):
    """A Revision is a collection of artifacts, that were produced by the same
       state of the Project's code."""
    revision = models.CharField(max_length=200)  # can be anything
    project = models.ForeignKey(Project, related_name='revisions')
    commit_time = models.DateTimeField('Time of creation',
                                       auto_now_add=True,
                                       help_text='Automatic field that is set when this revision is created')

    def __unicode__(self):
        return "[%s] %s" % (self.project.name, self.revision)

    class Meta:
        get_latest_by = 'commit_time'
        unique_together = (('project', 'revision'))

    def get_all_referencing_series(self):
        list_of_series = []
        for artifact in self.artifacts.all():
            list_of_series += artifact.project_series.all()
        return list(set(list_of_series))


class Branch(models.Model):
    """A Branch is referenced by a Revision in order to group Revisions by the branch it was
       created from.

       It stores how many Revisions we allow this Branch to have."""
    name = models.CharField(max_length=100)
    nb_revisions_to_keep = models.IntegerField("default number of revisions to keep. Overrides the "
                                               "projects and series default",
                                               default=None,
                                               blank=True,
                                               null=True)
    revisions = models.ManyToManyField(Revision, related_name='branches')


def get_artifact_location(instance, filename):
    """An helper function to specify the storage location of an uploaded file"""
    def is_int(elem):
        try:
            return True, int(elem)
        except ValueError:
            return False, 0

    media_relative_dir = os.path.join("artifacts",
                                      instance.project.name,
                                      instance.md5hash)
    root_dir = os.path.join(settings.MEDIA_ROOT, media_relative_dir)

    if 0:
        if os.path.exists(root_dir):
            dir_content = [v[1] for v in map(is_int, os.listdir(root_dir)) if v[0]]
            dir_content.sort()
            last_element = (dir_content[-1] + 1) if len(dir_content) > 0 else 1
        else:
            last_element = 1

    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, media_relative_dir)):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, media_relative_dir))

    return os.path.join(media_relative_dir, filename)


def get_deflation_directory(instance, without_media_root=False):
    """Returns the location where the artifact is getting deflated"""

    if without_media_root:
        deflate_directory = os.path.join(os.path.split(instance.artifactfile.name)[0], 'deflate')
    else:
        deflate_directory = os.path.join(settings.MEDIA_ROOT,
                                         os.path.split(instance.artifactfile.name)[0],
                                         'deflate')
    return deflate_directory


class Artifact(models.Model):
    """An artifact is a downloadable file"""
    project = models.ForeignKey(
        Project,
        related_name='artifacts')

    project_series = models.ManyToManyField(
        ProjectSeries,
        related_name='artifacts')

    revision = models.ForeignKey(
        Revision,
        related_name='artifacts',
        null=True,
        blank=True)

    md5hash = models.CharField(max_length=1024)  # md5 hash

    description = models.TextField(
        'description of the artifact',
        max_length=1024,
        blank=True,
        null=True)

    artifactfile = models.FileField(
        upload_to=get_artifact_location,
        help_text='the artifact file that will be stored on the server')

    is_documentation = models.BooleanField(
        default=False,
        help_text="Check if the artifact contains a documentation that should be processed by the server")

    documentation_entry_file = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="the documentation entry file if the artifact is documentation type, relative to the root of the deflated package")

    upload_date = models.DateTimeField(
        'Upload date',
        null=True,
        blank=True,
        help_text='Automatic field that indicates the file upload time')

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    blank=True,
                                    null=True,
                                    help_text='User/agent uploading the file')

    def get_absolute_url(self):
        return reverse('project_series',
                       kwargs={'project_id': self.revision.project.pk,
                               'series_id': self.project_series.all()[0].pk})

    def __unicode__(self):
        return "%s | %s | %s" % (self.revision, self.artifactfile.name, self.md5hash)

    class Meta:
        # we allow only one version per project
        # (we can however have the same file in several Series)
        unique_together = (("project", "md5hash"),)
        pass

    def filename(self):
        return os.path.basename(self.artifactfile.name)

    def full_path_name(self):
        """Returns the full path of the artifact on the disk

        .. warning::
        This should not work for other type of archival process
        that the one on the local file system"""
        return os.path.abspath(os.path.join(settings.MEDIA_ROOT, self.artifactfile.name))

    def get_documentation_url(self):
        """Returns the entry point of the documentation, relative to the media_root"""
        deflate_directory = get_deflation_directory(self, without_media_root=True)
        return urllib.pathname2url(os.path.join(deflate_directory, self.documentation_entry_file))

    @staticmethod
    def get_revision(artifact):
        return artifact.revision

    @staticmethod
    def md5_equals(md5_1, md5_2):
        return md5_1.upper() == md5_2.upper()

    def promote_to_series(self, new_series):
        """Adds a new series to the list of series, this artifact belongs to"""
        self.project_series.add(new_series)

    def save(self, *args, **kwargs):
        # @note(Stephan):
        # We use the m2m_changed Signal of the Artifact in order to check that
        # if we add a ProjectSeries to the Artifact, this new ProjectSeries
        # belongs to the same Project the Artifact does

        # Compute md5 hash if not given
        if not self.md5hash:
            import hashlib
            m = hashlib.md5()
            for chunk in self.artifactfile.chunks():
                m.update(chunk)
            self.md5hash = m.hexdigest()

        super(Artifact, self).save(*args, **kwargs)  # Call the "real" save() method.
