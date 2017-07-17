from django.core.urlresolvers import reverse
from django.db import models
import logging

from .projects import Project

logger = logging.getLogger(__name__)


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

    def get_absolute_url(self):
        return reverse('project_revision', kwargs={'project_id': self.project.pk,
                                                   'revision_id': self.id})


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
