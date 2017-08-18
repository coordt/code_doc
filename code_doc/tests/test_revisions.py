""" These tests check the behavior of the Revision System.

    They make sure
    * that only the last N revisions are kept.
    * that when revisions are, those that were added first are deleted
    * that Artifacts can be promoted to different series.
    * that Artifacts are deleted when there is no more reference to them
"""

from django.test import TestCase
from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from ..models.projects import Project, ProjectSeries
from ..models.artifacts import Artifact
from ..models.revisions import Revision, Branch

import datetime
import tempfile
import tarfile
import os


# logger for this file
import logging
logger = logging.getLogger(__name__)


class RevisionTest(TestCase):
    """Tests for revisions, their association with artifacts, branches, projects and their proper cleanup"""
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
                                                   nb_revisions_to_keep=4)
        self.branch_develop = Branch.objects.create(name='develop',
                                                    nb_revisions_to_keep=8)

        self.revision1.branches.add(self.branch_develop)
        self.revision2.branches.add(self.branch_develop, self.branch_master)
        self.revision3.branches.add(self.branch_develop, self.branch_master)

        self.test_file = RevisionTest.get_test_file()

    def tearDown(self):
        # removing the test file
        # in memory
        pass

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

    def test_cannot_add_artifact_to_serie_from_another_project(self):
        """Tests that artifacts can be promoted to series belonging to the same project"""

        from django.db import IntegrityError
        from django.db import transaction

        art1 = Artifact.objects.create(project=self.project,
                                       revision=self.revision1,
                                       md5hash='1',
                                       artifactfile=self.test_file)

        project2 = Project.objects.create(name='project2')

        series_p2 = ProjectSeries.objects.create(series="12345",
                                                 project=project2,
                                                 release_date=datetime.datetime.now())

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                art1.promote_to_series(series_p2)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                art1.project_series.add(series_p2)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                series_p2.artifacts.add(art1)

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
        rev3_artifact1 = Artifact.objects.create(project=self.project,
                                                 revision=self.revision3,
                                                 md5hash='4',
                                                 artifactfile=self.test_file)
        rev3_artifact2 = Artifact.objects.create(project=self.project,
                                                 revision=self.revision3,
                                                 md5hash='5',
                                                 artifactfile=self.test_file)
        rev3_artifact1.project_series = [self.new_series]
        rev3_artifact2.project_series = [self.new_series]
        stable_series = ProjectSeries.objects.create(series="stable",
                                                     project=self.project,
                                                     release_date=datetime.datetime.now())
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 2)

        # Promote the artifact to a different series
        rev3_artifact1.promote_to_series(stable_series)

        # Both Series should now contain the promoted artifact.
        self.assertIn(rev3_artifact1, self.new_series.artifacts.all())
        self.assertIn(rev3_artifact1, stable_series.artifacts.all())

        # only one of the series should contain the non promoted artifact
        self.assertIn(rev3_artifact2, self.new_series.artifacts.all())
        self.assertNotIn(rev3_artifact2, stable_series.artifacts.all())

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
        # Revision 3 now contains one Artifact
        self.assertEqual(self.revision3.artifacts.count(), 1)

        # adding artifact to serie
        rev3_artifact.project_series = [self.new_series]

        # remove artifact from series
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
        rev3_artifact.project_series = [self.new_series]
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
        artifact.project_series = [self.new_series]

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

    def test_no_remove_earliest_revision_if_no_limit(self):
        """Tests that the earliest revision added for a branch is deleted if
           there are too many of them.

           In this case the revisions do not belong to any branch
        """

        now = datetime.datetime.now()
        nb_revs = 4
        revisions = []
        artifacts = []
        for i in range(nb_revs):
            rev = Revision.objects.create(revision="%s" % (i + 9000),
                                          project=self.project,
                                          commit_time=now + datetime.timedelta(seconds=-i))

            art = Artifact.objects.create(project=self.project,
                                          revision=rev,
                                          md5hash='%s' % i,
                                          artifactfile=self.test_file)

            artifacts.append(art)
            revisions.append(rev)

            self.new_series.artifacts.add(art)

        try:
            for i in range(nb_revs):
                self.assertIsNotNone(Revision.objects.get(revision='%s' % (i + 9000)))
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

    def test_remove_earliest_revision_no_branch(self):
        """Tests that the earliest revision added for a branch is deleted if
           there are too many of them.

           In this case the revisions do not belong to any branch
        """

        now = datetime.datetime.now()
        nb_revs = 4
        revisions = []
        artifacts = []

        # setting up the limit
        self.new_series.nb_revisions_to_keep = 2
        self.new_series.save()  # save is needed

        for i in range(nb_revs):
            rev = Revision.objects.create(revision="%s" % (i + 9000),
                                          project=self.project,
                                          commit_time=now + datetime.timedelta(seconds=i))

            art = Artifact.objects.create(project=self.project,
                                          revision=rev,
                                          md5hash='%s' % i,
                                          artifactfile=self.test_file)

            artifacts.append(art)
            revisions.append(rev)

            self.new_series.artifacts.add(art)

        # print self.new_series.artifacts.all()
        # self.assertEqual(Revision.objects.prefetch_related('artifacts__serie').count(), 2)

        self.assertEqual(self.new_series.artifacts.count(), 2)

        # there should be a better way to manipulate this expression
        # self.assertEqual(Revision.objects.filter(artifacts__serie=self.new_series).all().distinct().count(), 2)
        self.assertSetEqual(set([art.revision for art in self.new_series.artifacts.all()]),
                            set([Revision.objects.get(revision='9002'),
                                 Revision.objects.get(revision='9003')]))

        try:
            for i in range(nb_revs)[2:]:
                self.assertIsNotNone(Revision.objects.get(revision='%s' % (i + 9000)))
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except Exception, e:
            self.fail("Unexpected Exception in get query %s" % e)
            raise

        # those revisions are the oldest, and should have been removed
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='9000')
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='9001')

    def test_remove_earliest_revision_no_branch_several_artifacts(self):
        """Tests that the earliest revision added for a branch is deleted if
           there are too many of them.

           Some revisions may contain several artifacts.
        """

        now = datetime.datetime.now()
        nb_revs = 4
        revisions = []
        artifacts = []

        # setting up the limit
        self.new_series.nb_revisions_to_keep = 2
        self.new_series.save()  # save is needed

        for i in range(nb_revs):
            rev = Revision.objects.create(revision="%s" % (i + 9000),
                                          project=self.project,
                                          commit_time=now + datetime.timedelta(seconds=i))

            art = Artifact.objects.create(project=self.project,
                                          revision=rev,
                                          md5hash='%s' % i,
                                          artifactfile=self.test_file)

            artifacts.append(art)

            if (i % 2) == 0:
                art = Artifact.objects.create(project=self.project,
                                              revision=rev,
                                              md5hash='x%s' % i,
                                              artifactfile=self.test_file)

                artifacts.append(art)

            revisions.append(rev)

        for art in artifacts:
            self.new_series.artifacts.add(art)

        # print self.new_series.artifacts.all()
        # self.assertEqual(Revision.objects.prefetch_related('artifacts__serie').count(), 2)

        self.assertEqual(self.new_series.artifacts.count(), 3)

        try:
            for i in range(nb_revs)[2:]:
                self.assertIsNotNone(Revision.objects.get(revision='%s' % (i + 9000)))
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except Exception, e:
            self.fail("Unexpected Exception in get query %s" % e)
            raise

        # those revisions are the oldest, and should have been removed
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='9000')
        with self.assertRaises(Revision.DoesNotExist):
            Revision.objects.get(revision='9001')

        # there should be a better way to manipulate this expression
        # self.assertEqual(Revision.objects.filter(artifacts__serie=self.new_series).all().distinct().count(), 2)
        self.assertSetEqual(set([art.revision for art in self.new_series.artifacts.all()]),
                            set([Revision.objects.get(revision='9002'),
                                 Revision.objects.get(revision='9003')]))

    def test_remove_earliest_revision_no_branch_several_artifacts_several_series(self):
        """Tests that the earliest revision added for a branch is deleted if
           there are too many of them.

           Some all_revisions may contain several all_artifacts, some all_artifacts may be part
           of several series.
        """

        s2 = ProjectSeries.objects.create(series="123456",
                                          project=self.project,
                                          release_date=datetime.datetime.now())

        now = datetime.datetime.now()
        nb_revs = 4
        all_revisions = []
        all_artifacts = []

        # setting up the limit
        self.new_series.nb_revisions_to_keep = 2
        self.new_series.save()  # save is needed

        for i in range(nb_revs):
            rev = Revision.objects.create(revision="%s" % (i + 9000),
                                          project=self.project,
                                          commit_time=now + datetime.timedelta(seconds=i))

            art = Artifact.objects.create(project=self.project,
                                          revision=rev,
                                          md5hash='%s' % i,
                                          artifactfile=self.test_file)

            all_artifacts.append(art)

            if (i % 2) == 0:
                art = Artifact.objects.create(project=self.project,
                                              revision=rev,
                                              md5hash='x%s' % i,
                                              artifactfile=self.test_file)

                all_artifacts.append(art)

            all_revisions.append(rev)

        # no limit on s2
        for art in all_artifacts:
            s2.artifacts.add(art)

        # limit on self.new_series
        for art in all_artifacts:
            self.new_series.artifacts.add(art)

        # print self.new_series.all_artifacts.all()
        # self.assertEqual(Revision.objects.prefetch_related('artifacts__serie').count(), 2)

        self.assertEqual(s2.artifacts.count(), 6)
        self.assertEqual(self.new_series.artifacts.count(), 3)

        # in this test, no revision has been removed

        # those revisions are the oldest, and should have been removed
        self.assertIsNotNone(Revision.objects.get(revision='9000'))
        self.assertIsNotNone(Revision.objects.get(revision='9001'))

        # there should be a better way to manipulate this expression
        # self.assertEqual(Revision.objects.filter(artifacts__serie=self.new_series).all().distinct().count(), 2)
        self.assertSetEqual(set([art.revision for art in self.new_series.artifacts.all()]),
                            set([Revision.objects.get(revision='9002'),
                                 Revision.objects.get(revision='9003')]))
        self.assertSetEqual(set([art.revision for art in s2.artifacts.all()]),
                            set(all_revisions))

    def create_several_artifacts(self):
        from django.utils.timezone import now as now_
        now = now_()

        if not hasattr(self, 'nb_revs'):
            self.nb_revs = 4

        all_artifacts = []
        for i in range(self.nb_revs):
            art = Artifact.objects.create(project=self.project,
                                          md5hash='%s' % i,
                                          artifactfile=self.test_file,
                                          upload_date=now + datetime.timedelta(seconds=i))

            all_artifacts.append((art, art.md5hash))

            if (i % 2) == 0:
                art = Artifact.objects.create(project=self.project,
                                              md5hash='x%s' % i,
                                              artifactfile=self.test_file,
                                              upload_date=now + datetime.timedelta(seconds=i + 100))

                all_artifacts.append((art, art.md5hash))

        return all_artifacts

    def create_several_revisions(self):
        from django.utils.timezone import now as now_
        now = now_()
        all_revisions = []

        if not hasattr(self, 'nb_revs'):
            self.nb_revs = 4

        for i in range(self.nb_revs):
            rev = Revision.objects.create(revision="%s" % (i + 9000),
                                          project=self.project,
                                          commit_time=now + datetime.timedelta(seconds=i))

            all_revisions.append(rev)

        return all_revisions

    def test_remove_oldest_artifacts_without_revision(self):
        """Tests that the earliest artifacts added for a series are removed if
           there are too many of them.

           The artifacts do not have any revision, they are a revision on their own.
           Since the pruning is based on the date of the artifact, a grouping by
           time is performed: if two artifacts have the same creation date, they are
           considered as one unique artifact as well.
        """

        self.nb_revs = 6
        all_artifacts = self.create_several_artifacts()

        # setting up the limit
        self.new_series.nb_revisions_to_keep = 3
        self.new_series.save()  # save is needed

        for art in all_artifacts:
            self.new_series.artifacts.add(art[0])

        self.assertEqual(self.new_series.artifacts.count(), 3)

        # all the ones with an x are the newests
        kept_artifacts_index = [1, 4, 7]
        try:
            for k in kept_artifacts_index:
                self.assertIsNotNone(Artifact.objects.get(md5hash=all_artifacts[k][1]))
        except Artifact.DoesNotExist, e:
            self.fail("[Artifact.DoesNotExist] One of the Artifacts returned no object from the get query %s" % e)
        except Artifact.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except Exception, e:
            self.fail("Unexpected Exception in get query %s" % e)
            raise

        for k, art in enumerate(all_artifacts):
            if k in kept_artifacts_index:
                continue
            with self.assertRaises(Artifact.DoesNotExist):
                Artifact.objects.get(md5hash=art[1])

#     @skip('to fix')
#     def test_remove_earliest_revision_with_branch(self):
#         """Tests that the earliest revision added for a branch is deleted if
#            there are too many of them.
#
#            In this case the all_revisions do not belong to any branch
#         """
#         branch = Branch.objects.create(name='branch', nb_revisions_to_keep=3)
#
#         revision1 = Revision.objects.create(revision='9991', project=self.project)
#         revision2 = Revision.objects.create(revision='9992', project=self.project)
#         revision3 = Revision.objects.create(revision='9993', project=self.project)
#         revision4 = Revision.objects.create(revision='9994', project=self.project)
#
#         branch.all_revisions.add(revision1, revision2, revision3)
#
#         branch.all_revisions.add(revision4)
#
#         self.assertEqual(branch.all_revisions.count(), 3)
#
#         try:
#             Revision.objects.get(revision='9992')
#             Revision.objects.get(revision='9993')
#             Revision.objects.get(revision='9994')
#         except Revision.DoesNotExist:
#             self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
#         except Revision.MultipleObjectsReturned:
#             self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
#         except:
#             self.fail("Unexpected Exception in get query")
#             raise
#
#         # Revision 9991 was the earliest Revision we created, so it should be removed.
#         with self.assertRaises(Revision.DoesNotExist):
#             Revision.objects.get(revision='9991')

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
        self.new_series.artifacts.remove(art1)

        try:
            Revision.objects.get(revision='1')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except:
            self.fail("Unexpected Exception in get query")
            raise

        self.assertEqual(other_series.artifacts.count(), 1)
        self.assertEqual(self.new_series.artifacts.count(), 1)


class RevisionViewTest(TestCase):
    """ Tests for the revision view. """

    def setUp(self):
        self.client = Client()

        # URL name
        self.path = 'project_revision'

        # Create user
        self.first_user = User.objects.create_user(username='test_revision_user',
                                                   password='test_revision_user',
                                                   email="b@b.com")

        # Create project
        self.project = Project.objects.create(name='test_project')

        # Test file
        self.test_file = RevisionTest.get_test_file()

        # Admin
        self.project.administrators = [self.first_user]

    def test_project_revision_view_no_restricted_series(self):
        """ Test permission on series that has no restriction """

        # Series
        new_series = ProjectSeries.objects.create(series="1234",
                                                  project=self.project,
                                                  release_date=datetime.datetime.now(),
                                                  is_public=True)

        # Revisions
        revision = Revision.objects.create(revision='revision',
                                           project=self.project)

        # Artifact
        art1 = Artifact.objects.create(project=self.project,
                                       revision=revision,
                                       md5hash='1',
                                       artifactfile=self.test_file)
        art1.project_series = [new_series]

        # Check response from revision page (we should see one revision and one artifact)
        response = self.client.get(reverse(self.path, args=[self.project.id, revision.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 1)
        self.assertEqual(len(response.context['artifacts']), 1)

        # Check that we can go to the series view
        response = self.client.get(reverse('project_series', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

    def test_project_revision_view_with_restrictions_on_series(self):
        """ Test permission on series that has restrictions """

        # Series
        new_series = ProjectSeries.objects.create(series="1234",
                                                  project=self.project,
                                                  release_date=datetime.datetime.now())

        # Revisions
        revision = Revision.objects.create(revision='revision',
                                           project=self.project)

        # Artifact
        art1 = Artifact.objects.create(project=self.project,
                                       revision=revision,
                                       md5hash='1',
                                       artifactfile=self.test_file)
        art1.project_series = [new_series]

        # Check response from revision page if we have no permission
        _ = User.objects.create_user(username='weak_user', password='weak_user', email="w@w.fr")
        response = self.client.login(username='weak_user', password='weak_user')
        self.assertTrue(response)
        response = self.client.get(reverse(self.path, args=[self.project.id, revision.id]))
        self.assertEqual(response.status_code, 401)

        # Check that we cannot go to the series view
        response = self.client.get(reverse('project_series', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 401)

        # Check response from revision page if we are admin
        response = self.client.login(username='test_revision_user', password='test_revision_user')
        self.assertTrue(response)
        response = self.client.get(reverse(self.path, args=[self.project.id, revision.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 1)
        self.assertEqual(len(response.context['artifacts']), 1)

        # Check that we can go to the series view
        response = self.client.get(reverse('project_series', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

    def test_project_revision_view_empty_access(self):
        """ Test if the project revision is ok. """

        # Set up empty revision
        empty_revision = Revision.objects.create(revision='empty_revision', project=self.project)

        # Test non existing revision
        response = self.client.get(reverse(self.path, args=[self.project.id, empty_revision.id + 41]))
        self.assertEqual(response.status_code, 401)

        # Test existing revision but to wrong project
        response = self.client.get(reverse(self.path, args=[self.project.id + 41, empty_revision.id]))
        self.assertEqual(response.status_code, 401)

        # Test existing revision from anonymous user
        response = self.client.get(reverse(self.path, args=[self.project.id, empty_revision.id]))
        self.assertEqual(response.status_code, 302)  # redirect

        # Test existing revision from admin user
        response = self.client.login(username='test_revision_user', password='test_revision_user')
        self.assertTrue(response)
        response = self.client.get(reverse(self.path, args=[self.project.id, empty_revision.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 0)
        self.assertEqual(len(response.context['artifacts']), 0)

    def test_project_revision_context(self):
        """ Test the context data of a revision. """

        # Set up two series
        # For the moment, let's make the series public. We will deal with restrictions later...
        self.series1 = ProjectSeries.objects.create(series="series1",
                                                    project=self.project,
                                                    release_date=datetime.datetime.now(),
                                                    is_public=True)
        self.series2 = ProjectSeries.objects.create(series="series2",
                                                    project=self.project,
                                                    release_date=datetime.datetime.now(),
                                                    is_public=True)

        # Set up public revision
        self.revision = Revision.objects.create(revision='revision', project=self.project)

        # Add 3 Artifacts to revision
        self.art1 = Artifact.objects.create(project=self.project,
                                            revision=self.revision,
                                            md5hash='1',
                                            artifactfile=self.test_file)
        self.art2 = Artifact.objects.create(project=self.project,
                                            revision=self.revision,
                                            md5hash='2',
                                            artifactfile=self.test_file)
        self.art3 = Artifact.objects.create(project=self.project,
                                            revision=self.revision,
                                            md5hash='3',
                                            artifactfile=self.test_file)

        # These three artifacts belong to different series
        self.art1.project_series = [self.series1]
        self.art2.project_series = [self.series2]
        self.art3.project_series = [self.series2]

        # Test the revision
        response = self.client.get(reverse(self.path, args=[self.project.id, self.revision.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['project'], self.project)
        self.assertEqual(len(response.context['series']), 2)
        self.assertEqual(len(response.context['artifacts']), 3)

        # Check that artifacts and series names are there
        self.assertContains(response, self.art1.filename())
        self.assertContains(response, self.art2.filename())
        self.assertContains(response, self.art3.filename())

        self.assertContains(response, self.series1.series)
        self.assertContains(response, self.series2.series)
