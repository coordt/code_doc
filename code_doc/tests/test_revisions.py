# this file tests the correct behaviour of the Users and Authors

from django.test import TestCase

from django.test import Client

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from code_doc.models import Project, ProjectSeries, Revision, Author, Artifact, get_deflation_directory, Branch

import datetime
import tempfile
import tarfile
import pdb
import os


# logger for this file
import logging
logger = logging.getLogger(__name__)


class RevisionTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.project = Project.objects.create(name='test_project')

        self.new_series = ProjectSeries.objects.create(series="12345",
                                                       project=self.project,
                                                       release_date=datetime.datetime.now())

        # Set up a 3 revisions that all are stored in the branch develop.
        # Revision 1 is only on develop
        # Revision 2 and 3 are on develop and also referenced by the master branch
        # The Master branch stores 4 revisions, the develop branch keeps 8
        self.revision1 = Revision.objects.create(revision='1',
                                                 project=self.project)
        self.revision2 = Revision.objects.create(revision='2',
                                                 project=self.project)
        self.revision3 = Revision.objects.create(revision='3',
                                                 project=self.project)

        self.branch_master = Branch.objects.create(name='master',
                                                   nr_of_revisions_kept=4)
        self.branch_develop = Branch.objects.create(name='develop',
                                                    nr_of_revisions_kept=8)

        self.revision1.branches.add(self.branch_develop)
        self.revision2.branches.add(self.branch_develop, self.branch_master)
        self.revision3.branches.add(self.branch_develop, self.branch_master)

        # Test the numberof revisions for each branch
        self.assertTrue(self.branch_master.revisions.count() == 2)
        self.assertTrue(self.branch_develop.revisions.count() == 3)

        self.test_file = get_test_file()

    def test_artifact_revision_correspondence(self):
        """Tests that Artifacts are correctly associated to Revisions"""
        self.assertEqual(self.new_series.artifacts.count(), 0)

        # Add 2 Artifacts to revision1
        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision1,
                                md5hash='1',
                                artifactfile=self.test_file)

        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision1,
                                md5hash='2',
                                artifactfile=self.test_file)

        # Add 1 Artifact to revision2
        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision2,
                                md5hash='3',
                                artifactfile=self.test_file)

        # We added 4 Artifacts to the revision
        self.assertTrue(self.revision1.artifacts.count() == 2)
        self.assertTrue(self.revision2.artifacts.count() == 1)
        self.assertTrue(self.revision3.artifacts.count() == 0)

    def test_artifact_promotion_with_resulting_revision_deletion(self):
        """Tests that we can promote an artifact to a new Revision (usually a stable revision).
           The prior revision does _not_ contain any more artifacts, so it should be deleted.
        """
        rev3_artifact = Artifact.objects.create(project_series=self.new_series,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)
        # Revision 3 now contains one Artifact
        self.assertTrue(self.revision3.artifacts.count() == 1)

        # Promote the artifact to a different revision
        rev3_artifact.promote_to_revision(self.revision1)

        self.assertTrue(self.revision1.artifacts.count() == 1)

        # We can still get revision 1 and 2
        Revision.objects.get(revision='1')
        Revision.objects.get(revision='2')
        # Revision 3 should be deleted because it has no more artifacts
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='3')

    def test_artifact_promotion_with_no_revision_deletion(self):
        """Tests that we can promote an artifact to a new Revision (usually a stable revision).
           The prior revision still contains artifacts after the promotion and so should _not_
           be deleted.
        """
        rev3_artifact = Artifact.objects.create(project_series=self.new_series,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)

        # Add second Artifact to revision 3
        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision3,
                                md5hash='5',
                                artifactfile=self.test_file)

        # Revision 3 now contains one Artifact
        self.assertTrue(self.revision3.artifacts.count() == 2)

        # Promote the artifact to a different revision
        rev3_artifact.promote_to_revision(self.revision1)

        self.assertTrue(self.revision1.artifacts.count() == 1)
        self.assertTrue(self.revision3.artifacts.count() == 1)

        # We can still get revision 1, 2 and 3
        Revision.objects.get(revision='1')
        Revision.objects.get(revision='2')
        Revision.objects.get(revision='3')

    def test_artifact_persistence_on_multiple_references(self):
        """Tests that an Artifact persists in the database if we remove a revision of a branch,
           that is still referenced by another branch.
        """
        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision2,
                                md5hash='6',
                                artifactfile=self.test_file)

        # We should be able to get this
        Artifact.objects.get(md5hash='6')

        self.branch_develop.revisions.remove(self.revision2)

        # These should still be there
        Artifact.objects.get(md5hash='6')
        Revision.objects.get(revision='2')

    def test_artifact_deletion_on_no_more_references(self):
        """Tests that an Artifact is deleted when there are no more revisions reference to it.
        """
        Artifact.objects.create(project_series=self.new_series,
                                revision=self.revision1,
                                md5hash='7',
                                artifactfile=self.test_file)

        # We should be able to get this
        Artifact.objects.get(md5hash='7')

        self.branch_develop.revisions.remove(self.revision1)

        # The Artifact should be deleted as well now
        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='7')

        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='1')

    def test_branch_revision_limit(self):
        """Tests that the revision limit of a branch is respected.
        """
        n_revisions_on_master = self.branch_master.revisions.count()
        n_revisions_kept_on_master = self.branch_master.nr_of_revisions_kept

        # Add exactly the amount of Revisions that the master branch allows
        for i in xrange(n_revisions_kept_on_master - n_revisions_on_master):
            new_revision = Revision.objects.create(revision=str(Revision.objects.count() + i + 1),
                                                   project=self.project)
            new_revision.branches.add(self.branch_master)

        self.assertTrue(self.branch_master.revisions.count() ==
                        self.branch_master.nr_of_revisions_kept)

        # Add one more revision, the revision count of the branch should not go up
        new_revision = Revision.objects.create(revision='tooMuch', project=self.project)
        new_revision.branches.add(self.branch_master)

        self.assertTrue(self.branch_master.revisions.count() ==
                        self.branch_master.nr_of_revisions_kept)

    def test_change_branch_revision_limit(self):
        """Tests if we can change the number of Revisions a branch is
           allowed to have and immediately enforce this change.
        """
        self.branch_master.nr_of_revisions_kept = 1
        self.branch_master.save()

        self.assertTrue(self.branch_master.revisions.count() ==
                        self.branch_master.nr_of_revisions_kept)

    def test_remove_earliest_revision(self):
        """Tests that the earliest revision added to a branch is deleted if
           there are too many of them.
        """
        branch = Branch.objects.create(name='branch', nr_of_revisions_kept=3)

        revision1 = Revision.objects.create(revision='9991', project=self.project)
        revision2 = Revision.objects.create(revision='9992', project=self.project)
        revision3 = Revision.objects.create(revision='9993', project=self.project)
        revision4 = Revision.objects.create(revision='9994', project=self.project)

        branch.revisions.add(revision1, revision2, revision3)

        branch.revisions.add(revision4)

        self.assertTrue(branch.revisions.count() == 3)

        Revision.objects.get(revision='9992')
        Revision.objects.get(revision='9993')
        Revision.objects.get(revision='9994')

        # Revision 9991 was the earliest Revision we created, so it should be removed
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='9991')


def get_test_file():
    """Gets a test file that can be used to create an artifact"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE,
                                     suffix='.tar.bz2') as f:
        # create a temporary tar object
        tar = tarfile.open(fileobj=f, mode='w:bz2')

        from inspect import getsourcefile
        source_file = getsourcefile(lambda _: None)

        tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
        tar.close()

        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())

    return test_file
