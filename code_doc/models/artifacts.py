from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings

import os
import logging
import urllib

from .projects import Project, ProjectSeries
from .revisions import Revision

logger = logging.getLogger(__name__)


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

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

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
        help_text='the artifact file that will be stored on the server',
        max_length=1024)
    # the 1024 is important in production, otherwise the filenames get scrubbed

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
    def get_project_series(artifact):
        return artifact.project_series.all()

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

        # Make sure that the documentation_entry_file is blank if the artifact is not a documentation
        if not self.is_documentation:
            self.documentation_entry_file = None

        super(Artifact, self).save(*args, **kwargs)  # Call the "real" save() method.
