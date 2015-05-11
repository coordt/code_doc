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


class RevisionTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.project = Project.objects.create(name='test_project')

        self.new_series = ProjectSeries.objects.create(series="12345",
                                                       project=self.project,
                                                       release_date=datetime.datetime.now())

        # Set up a 3 revisions that all are stored in the branch develop.
        # Revision 1 is only on master
        # Revision 2 and 3 are also referenced by the master branch
        self.revision1 = Revision.objects.create(revision='1',
                                                 project=self.project)
        self.revision2 = Revision.objects.create(revision='2',
                                                 project=self.project)
        self.revision3 = Revision.objects.create(revision='3',
                                                 project=self.project)

        self.branch_master = Branch.objects.create(name='master',
                                                   nr_of_revisions_kept=5)
        self.branch_develop = Branch.objects.create(name='master',
                                                    nr_of_revisions_kept=10)

        self.revision1.branches.add(self.branch_develop)
        self.revision2.branches.add(self.branch_develop, self.branch_master)
        self.revision3.branches.add(self.branch_develop, self.branch_master)

        # Test the numberof revisions for each branch
        self.assertTrue(self.branch_master.revisions.count() == 2)
        self.assertTrue(self.branch_develop.revisions.count() == 3)

        self.test_file = get_test_file()

    def test_artifact_revision_correspondence(self):
        """Tests, that Artifacts are correctly associated to Revisions"""
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
        """Tests, that we can promote an artifact to a new Revision (usually a stable revision).
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
        # Revision 3 should be deleted
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='3')

    def test_artifact_promotion_with_no_revision_deletion(self):
        """Tests, that we can promote an artifact to a new Revision (usually a stable revision).
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

        # The Artifact should be deleted as well now
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

    # @todo(Stephan): Fix this test
    def test_revision_deletion(self):
        """Tests, that the earliest revisions of a branch are deleted, when there are to many of them"""
        for i in xrange(4):
            new = Revision.objects.create(revision="TestRevision"+str(i), project=self.project)
            new.branches.add(self.branch_master)

        # The original revision from setUp should not have been destroyed yet,
        # so we should still have its artifact
        self.assertTrue(Artifact.objects.count() == 1)

        # Add too many revisions
        for i in xrange(10):
            new = Revision.objects.create(revision="TestRevision"+str(i + 4), project=self.project)
            new.branches.add(self.branch_master)

        # @todo(Stephan): remove hardcoded setting for the maximum amount of revision per branch
        self.assertTrue(self.branch_master.revisions.count() == self.branch_master.nr_of_revisions_kept)

        # Since the first revision (that included an artifact) has been deleted, the artifact also
        # should be deleted
        self.assertTrue(Artifact.objects.count() == 0)

    def test_artifact_deletion(self):
        """This test should check if the artifacts that correspond to a deleted revision are
           also correctly deleted, if no other revision points to them."""
        pass


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
