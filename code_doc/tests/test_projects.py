from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError

from ..models.projects import Project, ProjectSeries, ProjectRepository
from ..models.authors import Author
from ..models.artifacts import Artifact
from ..models.revisions import Revision

import datetime


class ProjectTest(TestCase):
    """Tests on the project objects"""
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project'

        self.first_user = User.objects.create_user(username='toto')

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

    def test_project_details(self):
        """Tests the project detail view"""
        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['authors']), len(self.project.authors.all()))

        # non existing project
        response = self.client.get(reverse(self.path, args=[self.project.id + 1]))
        self.assertEqual(response.status_code, 404)

    def test_project_administrator(self):
        """Tests if the admins only have the right to modify the project configuration"""

        # user2 is not admin
        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")

        self.assertFalse(self.project.has_user_project_series_add_permission(user2))
        self.assertTrue(self.project.has_user_project_series_add_permission(self.first_user))

    def test_project_get_number_of_series(self):
        """Number of revisions tests"""
        self.assertEqual(self.project.get_number_of_series(), 0)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        self.assertEqual(self.project.get_number_of_series(), 1)

    def test_project_get_number_of_revisions(self):
        self.assertEqual(self.project.get_number_of_revisions(), 0)
        revision = Revision.objects.create(revision='1', project=self.project)

        self.assertEqual(self.project.get_number_of_revisions(), 1)

    def test_project_get_number_of_files(self):
        """Number of files tests"""

        self.assertEqual(self.project.get_number_of_files(), 0)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        revision = Revision.objects.create(revision='1', project=self.project)

        new_artifact = Artifact.objects.create(project=self.project, revision=revision, md5hash='0')
        new_artifact.project_series.add(new_series)

        self.assertEqual(self.project.get_number_of_files(), 1)

        new_artifact2 = Artifact.objects.create(project=self.project, revision=revision, md5hash='1')
        new_artifact2.project_series.add(new_series)

        self.assertEqual(self.project.get_number_of_files(), 2)

    def test_project_get_repositories(self):
        """Checks that the details of the repositories appear on the project detail page"""
        project2 = Project.objects.create(name='test_project2')
        project2.authors = [self.author1]
        project2.administrators = [self.first_user]

        repository = "https://somewhere.gitlab"
        ProjectRepository.objects.create(project=project2,
                                         code_source_url=repository)
        ProjectRepository.objects.create(project=project2,
                                         code_source_url=repository + "2")

        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, repository)

        response = self.client.get(reverse(self.path, args=[project2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, repository, 2)


class ProjectViewTest(TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project'

        self.first_user = User.objects.create_user(username='test', password='test')

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

    def test_link_last_artifact_doc(self):
        """Number of files tests"""

        from django.utils import timezone

        self.assertEqual(self.project.get_number_of_files(), 0)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        revision = Revision.objects.create(revision='1', project=self.project)

        rev1 = timezone.now()
        artifact0 = Artifact.objects.create(project=self.project, revision=revision, md5hash='0',
                                            is_documentation=True,
                                            upload_date=rev1 - datetime.timedelta(hours=1),
                                            artifactfile=__file__,
                                            documentation_entry_file='truc.html')
        artifact0.project_series.add(new_series)

        artifact1 = Artifact.objects.create(project=self.project, revision=revision, md5hash='1',
                                            artifactfile=__file__,
                                            upload_date=rev1)
        artifact1.project_series.add(new_series)

        artifact2 = Artifact.objects.create(project=self.project, revision=revision, md5hash='2',
                                            is_documentation=True,
                                            upload_date=rev1,
                                            artifactfile=__file__,
                                            documentation_entry_file='bidule.html')
        artifact2.project_series.add(new_series)

        self.assertTrue(self.client.login(username='test', password='test'))

        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, artifact2.get_documentation_url(), 1)
        self.assertNotContains(response, artifact0.get_documentation_url())
        self.assertNotContains(response, artifact1.filename())


class ProjectRepositoryTest(TestCase):

    def test_repository_unique_constraint(self):
        """Checks the uniqueness constraints on the repository URLs"""
        project = Project.objects.create(name='test_project')
        repository = "https://somewhere.gitlab"
        ProjectRepository.objects.create(project=project,
                                         code_source_url=repository)

        from django.db import transaction

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProjectRepository.objects.create(project=project,
                                                 code_source_url=repository)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProjectRepository.objects.create(project=project,
                                                 code_source_url="    " + repository)
