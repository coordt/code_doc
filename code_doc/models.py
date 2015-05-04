from django.db import models
import datetime
import os

# from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import AbstractUser, Group

from django.core.urlresolvers import reverse

from django.template.defaultfilters import slugify
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver


from django.conf import settings

import markdown
import tarfile
import tempfile
import logging
import urllib
import shutil
import functools

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
    # @todo(Stephan): Is it okay to remove the uniqueness assumption of the email?
    #                 Since the email of the users are copied over to the authors now,
    #                 the uniqueness is violated
    email = models.EmailField(max_length=50,
                              # unique=True,
                              db_index=True)
    home_page_url = models.CharField(max_length=250, blank=True)
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                       related_name='author',
                                       blank=True,
                                       null=True,
                                       help_text='The Django User, this Author is corresponding to.')
    image = models.ImageField(blank=True, null=True, upload_to=get_author_image_location)

    def __unicode__(self):
        return "%s %s (%s)" % (self.firstname, self.lastname, self.email)

    def has_user_author_edit_permission(self, user):
        if hasattr(user, 'author'):
            has_edit_permission = user.author == self
        else:
            has_edit_permission = False

        return has_edit_permission

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
                                         max_length=200, blank=True, null=True)
    description_mk = models.TextField('text in Markdown', max_length=2500, blank=True, null=True)
    icon = models.ImageField(blank=True, null=True, upload_to='project_icons/')
    slug = models.SlugField()

    authors = models.ManyToManyField(Author)

    # the administrators of the project, have the rights to edit the
    administrators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, null=True)

    home_page_url = models.CharField(max_length=250, null=True, blank=True)
    code_source_url = models.CharField(max_length=250, null=True, blank=True)
    copyright = models.ForeignKey(Copyright, null=True, blank=True)
    copyright_holder = models.ManyToManyField(CopyrightHolder, null=True, blank=True)

    topics = models.ManyToManyField(Topic, null=True, blank=True)

    def __unicode__(self):
        return "%s" % (self.name)

    class Meta:
        permissions = (
         ("project_view",          "Can see the project"),
         ("project_administrate",  "Can administrate the project"),
         ("project_series_add",   "Can add a series to the project"),
         ("project_artifact_add",  "Can add an artifact to the project"),
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

    def has_user_project_artifact_add_permission(self, user):
        """Returns true if the user is able to add series to the current project"""
        return self.has_user_project_administrate_permission(user)

    def get_number_of_files(self):
        """Returns the number of files archived for a project"""
        artifact_counts = [rev.artifacts.count() for rev in self.series.all()]
        return sum(artifact_counts) if len(artifact_counts) > 0 else 0

    def get_number_of_revisions(self):
        """Returns the number of revisions for a project"""
        return self.series.count()

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
                                      max_length=2500, blank=True, null=True)

    # the users and groups allowed to view the artifacts of the revision
    # and also this project series
    view_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, null=True,
                                        related_name='view_users')
    view_groups = models.ManyToManyField(Group, blank=True, null=True, related_name='view_groups')

    view_artifacts_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, null=True,
                                                  related_name='view_artifact_users')
    view_artifacts_groups = models.ManyToManyField(Group, blank=True, null=True,
                                                   related_name='view_artifact_groups')

    class Meta:
        unique_together = (("project", "series"), )
        permissions = (
          ("series_view",  "User of group has access to this revision"),
          ("series_edit",  "User can edit the content of this series"),
          # This is a refinement of series_view
          ("series_artifact_view",  "Access to the artifacts of this revision"),
        )

    def __unicode__(self):
        return "[%s @ %s] [%s]" % (self.project.name, self.series, self.release_date)

    def get_absolute_url(self):
        return reverse('project_revision', kwargs={'project_id': self.project.pk,
                                                   'series_id': self.pk})

    def has_user_series_view_permission(self, userobj):
        """Returns true if the user has view permission on this series, False otherwise"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            manage_permission_on_object(userobj, self.view_users, self.view_groups, False)

    def has_user_series_edit_permission(self, userobj):
        """Returns true if the user has view permission on this series, False otherwise"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            manage_permission_on_object(userobj, self.view_users, self.view_groups, False)

    def has_user_series_artifact_view_permission(self, userobj):
        """Returns True if the user can see the list of artifacts and the artifacts themselves for
           a specific series, False otherwise"""
        return self.is_public or \
            self.project.has_user_project_administrate_permission(userobj) or \
            (self.has_user_series_view_permission(userobj) and
             manage_permission_on_object(userobj, self.view_artifacts_users,
                                         self.view_artifacts_groups, False))


def get_artifact_location(instance, filename):
    """An helper function to specify the storage location of an uploaded file"""
    def is_int(elem):
        try:
            return True, int(elem)
        except ValueError, e:
            return False, 0

    media_relative_dir = os.path.join("artifacts",
                                      instance.project_series.project.name,
                                      instance.project_series.series)
    root_dir = os.path.join(settings.MEDIA_ROOT, media_relative_dir)

    if os.path.exists(root_dir):
        dir_content = [v[1] for v in map(is_int, os.listdir(root_dir)) if v[0]]
        dir_content.sort()
        last_element = (dir_content[-1] + 1) if len(dir_content) > 0 else 1
    else:
        last_element = 1

    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, media_relative_dir, str(last_element))):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, media_relative_dir, str(last_element)))

    return os.path.join(media_relative_dir, str(last_element), filename)


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
    project_series = models.ForeignKey(ProjectSeries, related_name="artifacts")
    md5hash = models.CharField(max_length=1024)  # md5 hash
    description = models.TextField('description of the artifact', max_length=1024)
    artifactfile = models.FileField(upload_to=get_artifact_location,
                                    help_text='the artifact file that will be stored on the server')
    is_documentation = models.BooleanField(default=False,
                                           help_text="Check if the artifact contains a documentation that should be processed by the server")
    documentation_entry_file = models.CharField(max_length=255, null=True, blank=True,
                                                help_text="the documentation entry file if the artifact is documentation type, relative to the root of the deflated package")
    upload_date = models.DateTimeField('Upload date', null=True, blank=True,
                                       help_text='Automatic field that indicates the file upload time')

    uploaded_by = models.CharField(max_length=50, help_text='User/agent uploading the file',
                                   null=True, blank=True)

    def get_absolute_url(self):
        return reverse('project_revision', kwargs={'project_id': self.project_series.project.pk,
                                                   'series_id': self.project_series.pk})

    def __unicode__(self):
        return "%s | %s | %s" % (self.project_series, self.artifactfile.name, self.md5hash)

    class Meta:
        # we allow only one version per project version
        # (we can however have the same file in several versions)
        unique_together = (("project_series", "md5hash"), )

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

    def save(self, *args, **kwargs):
        import hashlib
        m = hashlib.md5()
        if not self.md5hash:
            for chunk in self.artifactfile.chunks():
                m.update(chunk)
            self.md5hash = m.hexdigest()

        super(Artifact, self).save(*args, **kwargs)  # Call the "real" save() method.


def is_deflated(instance):
    """Returns true if the artifact instance should or have been deflated"""
    return instance.is_documentation and \
        os.path.splitext(instance.artifactfile.name)[1] in ['.tar', '.bz2', '.gz']


@receiver(post_save, sender=Artifact)
def callback_artifact_deflation_on_save(sender, instance, created, raw, **kwargs):
    """Callback received after an artifact has been saved in the database. In case of a documentation
    artifact, and in case the artifact is a zip/archive, we deflate it"""

    # logger.debug('[project artifact] post_save artifact %s', instance)

    # we do not perform any deflation in case of database populating action
    if raw:
        return

    # we do not perform any action in case of save failure
    if not created:
        return

    # deflate if documentation
    if is_deflated(instance):

        # I do not know if this one is needed in fact, it is if we are in the save method of
        # Artifact but from here the file should be fully accessible
        with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE) as f:
            for chunk in instance.artifactfile.chunks():
                f.write(chunk)
            f.seek(0)
            instance.artifactfile.close()

            deflate_directory = get_deflation_directory(instance)
            # logger.debug('[project artifact] deflating artifact %s to %s', instance, deflate_directory)
            tar = tarfile.open(fileobj=f)

            curdir = os.path.abspath(os.curdir)
            if(not os.path.exists(deflate_directory)):
                os.makedirs(deflate_directory)
            os.chdir(deflate_directory)
            tar.extractall()  # path = deflate_directory)
            os.chdir(curdir)

    pass


@receiver(pre_delete, sender=Artifact)
def callback_artifact_documentation_delete(sender, instance, using, **kwargs):
    """Callback received before an artifact has is being removed from the database. In case of
    a documentation artifact, and in case the artifact is a zip/archive, the deflated directory
    is removed."""
    # logger.debug('[project artifact] pre_delete artifact %s', instance)

    # deflate if documentation and archive
    if is_deflated(instance):
        deflate_directory = get_deflation_directory(instance)
        if(os.path.exists(deflate_directory)):
            # logger.debug('[project artifact] removing deflated artifact %s from %s', instance, deflate_directory)

            def on_error(instance, function, path, excinfo):
                logger.warning('[project artifact] error removing %s for instance %s',
                               path, instance)
                return

            shutil.rmtree(deflate_directory, False, functools.partial(on_error, instance=instance))

    # removing the file on post delete
    pass


@receiver(post_delete, sender=Artifact)
def callback_artifact_delete(sender, instance, using, **kwargs):
    # logger.debug('[project artifact] post_delete artifact %s', instance)
    storage, path = instance.artifactfile.storage, instance.artifactfile.path
    storage.delete(path)
    try:
        storage.delete(path)
    except WindowsError, e:
        logger.warning('[project artifact] error removing %s for instance %s', path, instance)
    # if(os.path.exists(instance.full_path_name())):
    #    os.remove(instance.full_path_name())
