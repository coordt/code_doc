# this file tests the correct behaviour of the Users and Authors

from django.test import TestCase

from django.test import Client

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from code_doc.models import Project, ProjectSeries, Revision, Author, Artifact, get_deflation_directory

import datetime
import tempfile
import tarfile
import pdb
import os


class RevisionTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.first_user = User.objects.create_user(username='toto',
                                                   password='titi',
                                                   first_name='Toto',
                                                   last_name='Toto')
        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

        self.new_series = ProjectSeries.objects.create(series="12345", project=self.project,
                                                       release_date=datetime.datetime.now())

        self.revision = Revision.objects.create(branch="TestBranch")

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

            self.artifact = Artifact.objects.create(
                              project_series=self.new_series,
                              revision=self.revision,
                              md5hash='0',
                              artifactfile=test_file)

    def test_artifact_revision_correspondence(self):
        """Tests, that Artifacts are correctly associated to Revisions"""
        self.assertEqual(self.new_series.artifacts.count(), 1)

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

            new_artifact = Artifact.objects.create(
                              project_series=self.new_series,
                              revision=self.revision,
                              md5hash='1',
                              artifactfile=test_file)

            new_artifact1 = Artifact.objects.create(
                              project_series=self.new_series,
                              revision=self.revision,
                              md5hash='2',
                              artifactfile=test_file)

            new_artifact2 = Artifact.objects.create(
                              project_series=self.new_series,
                              revision=self.revision,
                              md5hash='3',
                              artifactfile=test_file)

        self.assertTrue(self.revision.artifacts.count() == 4)

        import shutil
        if(os.path.exists(get_deflation_directory(new_artifact1))):
            shutil.rmtree(get_deflation_directory(new_artifact1))

    def test_revision_deletion(self):
        """Tests, that the earliest revisions are deleted, when there are to many of them"""
        for i in xrange(4):
            Revision.objects.create(branch="TestBranch")

        # The original revision from setUp should not have been destroyed yet,
        # so we should still have its artifact
        self.assertTrue(Artifact.objects.count() == 1)

        # Add too many revisions
        for i in xrange(10):
            Revision.objects.create(branch="TestBranch")

        # @todo(Stephan): remove hardcoded setting for the maximum amount of revision per branch
        self.assertTrue(Revision.objects.filter(branch="TestBranch").count() == 5)

        # Since the first revision (that included an artifact) has been deleted, the artifact also
        # should be deleted
        self.assertTrue(Artifact.objects.count() == 0)

    def test_artifact_deletion(self):
        """This test should check if the artifacts that correspond to a deleted revision are
           also correctly deleted  """
        pass
