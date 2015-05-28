""" These tests check the behavior of the Revision System.

    They make sure
    * that only the last N revisions are kept.
    * that when revisions are, those that were added first are deleted
    * that Artifacts can be promoted to different series.
    * that Artifacts are deleted when there is no more reference to them
"""

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
    """ Revision Test Case that tests the behavior of the Revision System"""
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

        self.test_file = RevisionTest.get_test_file()

    @staticmethod
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

    def test_set_up(self):
        """Tests the configuration after setting up the test"""
        # Test the number of revisions for each branch
        self.assertEqual(self.branch_master.revisions.count(), 2)
        self.assertEqual(self.branch_develop.revisions.count(), 3)

    def test_artifact_revision_correspondence(self):
        """Tests that Artifacts are correctly associated to Revisions"""
        self.assertEqual(self.new_series.artifacts.count(), 0)

        # Add 2 Artifacts to revision1
        art1 = Artifact.objects.create(project=self.project,
                                       revision=self.revision1,
                                       md5hash='1',
                                       artifactfile=self.test_file)
        art2 = Artifact.objects.create(project=self.project,
                                       revision=self.revision1,
                                       md5hash='2',
                                       artifactfile=self.test_file)
        # Add 1 Artifact to revision2
        art3 = Artifact.objects.create(project=self.project,
                                       revision=self.revision2,
                                       md5hash='3',
                                       artifactfile=self.test_file)
        art1.project_series = [self.new_series]
        art2.project_series = [self.new_series]
        art3.project_series = [self.new_series]

        self.assertEqual(self.revision1.artifacts.count(), 2)
        self.assertEqual(self.revision2.artifacts.count(), 1)
        self.assertEqual(self.revision3.artifacts.count(), 0)

    def test_artifact_promotion_no_revision_deletion(self):
        """Tests that we can promote an artifact to a new Series (usually a stable Series).
           This promotion brings the Revision of the Artifact to the new Series, but not all
           Artifacts of this Revision, only the one we promote.

           This case should cause no revision deletions
        """
        rev3_artifact = Artifact.objects.create(project=self.project,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)
        rev3_artifact.project_series = [self.new_series]
        stable_series = ProjectSeries.objects.create(series="stable",
                                                     project=self.project,
                                                     release_date=datetime.datetime.now())
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 1)

        # Promote the artifact to a different series
        rev3_artifact.promote_to_series(stable_series)

        # Both Series should now contain the Artifact.
        self.assertIn(rev3_artifact, self.new_series.artifacts.all())
        self.assertIn(rev3_artifact, stable_series.artifacts.all())

        # Both Series should contain the Revision.
        self.assertIn(self.revision3, self.new_series.get_all_revisions())
        self.assertIn(self.revision3, stable_series.get_all_revisions())

        # We can still get revision 1, 2 and 3
        try:
            Revision.objects.get(revision='1')
            Revision.objects.get(revision='2')
            Revision.objects.get(revision='3')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

    def test_artifact_promotion_by_assigning_no_revision_deletion(self):
        """Tests if we can promote an artifact to another Series by just setting the new Series,
           instead of going through the promote_to_series function.

           This case should cause no deletions of Revisions.
        """
        rev3_artifact = Artifact.objects.create(project=self.project,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)
        rev3_artifact.project_series = [self.new_series]
        stable_series = ProjectSeries.objects.create(series="stable",
                                                     project=self.project,
                                                     release_date=datetime.datetime.now())
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 1)

        # Promote the artifact to a different series
        rev3_artifact.project_series.add(stable_series)

        # Both Series should now contain the Artifact.
        self.assertIn(rev3_artifact, self.new_series.artifacts.all())
        self.assertIn(rev3_artifact, stable_series.artifacts.all())

        # Both Series should contain the Revision.
        self.assertIn(self.revision3, self.new_series.get_all_revisions())
        self.assertIn(self.revision3, stable_series.get_all_revisions())

        # We can still get revision 1, 2 and 3
        try:
            Revision.objects.get(revision='1')
            Revision.objects.get(revision='2')
            Revision.objects.get(revision='3')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

    def test_remove_series_from_artifact_with_resulting_revision_deletion(self):
        """Tests that we can remove an Series from an Artifact.
           The revision of the Artifact is not referenced by any more Series so
           it should be deleted.
        """
        rev3_artifact = Artifact.objects.create(project=self.project,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)
        rev3_artifact.project_series = [self.new_series.pk]
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 1)

        # Remove the Series from the Artifact
        rev3_artifact.project_series.remove(self.new_series)

        # Revision 3 should be deleted, because it is not referenced by any Series
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='3')

        # We can still get revision 1 and 2
        try:
            Revision.objects.get(revision='1')
            Revision.objects.get(revision='2')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

    def test_remove_artifact_from_series_with_resulting_revision_deletion(self):
        """Tests that we can remove an Artifact from a Series.
           The revision of the Artifact is not referenced by any more Series so
           it should be deleted.
        """
        rev3_artifact = Artifact.objects.create(project=self.project,
                                                revision=self.revision3,
                                                md5hash='4',
                                                artifactfile=self.test_file)
        rev3_artifact.project_series = [self.new_series.pk]
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 1)

        # Remove the artifact from the Series
        self.new_series.artifacts.remove(rev3_artifact)

        # Revision 3 should be deleted, because it is not referenced by any Series
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='3')

        # We can still get revision 1 and 2
        try:
            Revision.objects.get(revision='1')
            Revision.objects.get(revision='2')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

    # @todo(Stephan): Think about this test, is it covered by the new revision and series system?

    # def test_artifact_persistence_on_multiple_references(self):
    #     """Tests that an Artifact persists in the database if we remove a revision of a branch,
    #        that is still referenced by another branch.
    #     """
    #     Artifact.objects.create(project_series=self.new_series,
    #                             revision=self.revision2,
    #                             md5hash='6',
    #                             artifactfile=self.test_file)

    #     # We should be able to get this
    #     try:
    #         Artifact.objects.get(md5hash='6')
    #     except Artifact.DoesNotExist:
    #         self.fail("[Artifact.DoesNotExist] The Artifacts returned no object from the get query")
    #     except Artifact.MultipleObjectsReturned:
    #         self.fail("[Artifact.MultipleObjectsReturned] The Artifacts returned more than one object from the get query")
    #     except:
    #         self.fail("Unexpected Exception in get query")
    #         raise

    #     self.branch_develop.revisions.remove(self.revision2)

    #     try:
    #         Revision.objects.get(revision='2')
    #     except Revision.DoesNotExist:
    #         self.fail("[Revision.DoesNotExist] The Revisions returned no object from the get query")
    #     except Revision.MultipleObjectsReturned:
    #         self.fail("[Revision.MultipleObjectsReturned] The Revisions returned more than one object from the get query")
    #     except:
    #         self.fail("Unexpected Exception in get query")
    #         raise

    def test_artifact_and_revision_deletion_on_no_more_referencing_series(self):
        """Tests that an Artifact and it's Revision is deleted
           when there are no more Series that reference to it's Revision.
        """
        artifact = Artifact.objects.create(project=self.project,
                                           revision=self.revision1,
                                           md5hash='7',
                                           artifactfile=self.test_file)
        artifact.project_series = [self.new_series.pk]



        # We should be able to get the Artifact from the database
        try:
            Artifact.objects.get(md5hash='7')
        except Artifact.DoesNotExist:
            self.fail("[Artifact.DoesNotExist] The Artifacts returned no object from the get query")
        except Artifact.MultipleObjectsReturned:
            self.fail("[Artifact.MultipleObjectsReturned] The Artifacts returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

        artifact.project_series.remove(self.new_series)

        # The Revision and the Artifact should be deleted now
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='1')

        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='7')

    def test_artifact_deletion_on_revision_deletion(self):
        Artifact.objects.create(project=self.project,
                                revision=self.revision1,
                                md5hash='321',
                                artifactfile=self.test_file)
        Artifact.objects.create(project=self.project,
                                revision=self.revision1,
                                md5hash='322',
                                artifactfile=self.test_file)
        Artifact.objects.create(project=self.project,
                                revision=self.revision1,
                                md5hash='323',
                                artifactfile=self.test_file)
        Artifact.objects.create(project=self.project,
                                revision=self.revision1,
                                md5hash='324',
                                artifactfile=self.test_file)

        self.revision1.delete()

        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='1')
        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='321')
        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='322')
        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='323')
        with self.assertRaises(Artifact.DoesNotExist):
            Artifact.objects.get(md5hash='324')

    # @todo(Stephan):
    # These commented out tests need to be restructured once we can enforce
    # that only the latest N Revisions are kept.
    # This is not done right now

    # def test_branch_revision_limit(self):
    #     """Tests that the revision limit of a branch is respected.
    #     """
    #     n_revisions_on_master = self.branch_master.revisions.count()
    #     n_revisions_kept_on_master = self.branch_master.nr_of_revisions_kept

    #     # Add exactly the amount of Revisions that the master branch allows
    #     for i in xrange(n_revisions_kept_on_master - n_revisions_on_master):
    #         new_revision = Revision.objects.create(revision=str(Revision.objects.count() + i + 1),
    #                                                project=self.project)
    #         new_revision.branches.add(self.branch_master)

    #     self.assertEqual(self.branch_master.revisions.count(),
    #                      self.branch_master.nr_of_revisions_kept)

    #     # Add one more revision, the revision count of the branch should not go up
    #     new_revision = Revision.objects.create(revision='tooMuch', project=self.project)
    #     new_revision.branches.add(self.branch_master)

    #     self.assertEqual(self.branch_master.revisions.count(),
    #                      self.branch_master.nr_of_revisions_kept)

    # def test_change_branch_revision_limit(self):
    #     """Tests if we can change the number of Revisions a branch is
    #        allowed to have and immediately enforce this change.
    #     """
    #     self.branch_master.nr_of_revisions_kept = 1
    #     self.branch_master.save()

    #     self.assertEqual(self.branch_master.revisions.count(),
    #                      self.branch_master.nr_of_revisions_kept)

    # def test_remove_earliest_revision(self):
    #     """Tests that the earliest revision added for a branch is deleted if
    #        there are too many of them.
    #     """
    #     branch = Branch.objects.create(name='branch', nr_of_revisions_kept=3)

    #     revision1 = Revision.objects.create(revision='9991', project=self.project)
    #     revision2 = Revision.objects.create(revision='9992', project=self.project)
    #     revision3 = Revision.objects.create(revision='9993', project=self.project)
    #     revision4 = Revision.objects.create(revision='9994', project=self.project)

    #     branch.revisions.add(revision1, revision2, revision3)

    #     branch.revisions.add(revision4)

    #     self.assertEqual(branch.revisions.count(), 3)

    #     try:
    #         Revision.objects.get(revision='9992')
    #         Revision.objects.get(revision='9993')
    #         Revision.objects.get(revision='9994')
    #     except Revision.DoesNotExist:
    #         self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
    #     except Revision.MultipleObjectsReturned:
    #         self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
    #     except:
    #         self.fail("Unexpected Exception in get query")
    #         raise

    #     # Revision 9991 was the earliest Revision we created, so it should be removed.
    #     with self.assertRaises(Revision.DoesNotExist):
    #         Revision.objects.get(revision='9991')

    def test_revision_persistance_if_artifact_is_referenced_by_different_series(self):
        """Tests that the revision persists if an Artifact is removed from a Series, but still
           referenced by
        """
        art1 = Artifact.objects.create(project=self.project,
                                       revision=self.revision1,
                                       md5hash='111',
                                       artifactfile=self.test_file)
        art2 = Artifact.objects.create(project=self.project,
                                       revision=self.revision1,
                                       md5hash='112',
                                       artifactfile=self.test_file)

        other_series = ProjectSeries.objects.create(series="other",
                                                    project=self.project,
                                                    release_date=datetime.datetime.now())

        self.new_series.artifacts.add(art1, art2)

        art1.promote_to_series(other_series)
        # Artifact 1 is now referenced in both series, but we remove it from the second
        # series now. This should cause no deletions of revisions
        other_series.artifacts.remove(art1)

        try:
            Revision.objects.get(revision='1')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

        self.assertEqual(other_series.artifacts.count(), 0)
        self.assertEqual(self.new_series.artifacts.count(), 2)
