from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse

import datetime

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..models.artifacts import Artifact
from ..forms.forms import ModalAddUserForm


class ProjectSeriesTest(TestCase):
    """Testing the project series functionality"""
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project_series_all'

        self.first_user = User.objects.create_user(username='test_series_user',
                                                   password='test_series_user',
                                                   email="b@b.com")

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

    def test_project_series_empty(self):
        """Tests if the project series is ok"""

        # test non existing project
        response = self.client.get(reverse(self.path, args=[self.project.id + 1]))
        self.assertEqual(response.status_code, 404)

        # test existing project
        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 0)

    def test_project_series_create_new_no_public(self):
        """Test the creation of a new project series, with non public visibility"""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 0)
        self.assertEqual(len(response.context['series']), len(response.context['last_update']))

    def test_project_series_create_new_public(self):
        """Test the creation of a new project series, with public visibility"""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now(),
                                                  is_public=True)
        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['series']), 1)
        self.assertEqual(len(response.context['series']), len(response.context['last_update']))

    def test_project_series_addview(self):
        """Test the view access of an existing project"""

        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        response = self.client.get(reverse("project_series_add", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

    def test_project_series_addview_non_existing(self):
        """Test the view access of an non existing project"""

        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        response = self.client.get(reverse("project_series_add", args=[self.project.id + 1]))

        # returns unauthorized to avoid the distinction between non existing project
        # spoofing and the authorization.
        self.assertEqual(response.status_code, 401)

    def test_project_series_addview_restrictions(self):
        """Tests if the admins have the right to modify the project configuration,
            and the others don't"""

        # user2 is not admin of this project
        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        response = self.client.login(username='user2', password='user2')
        self.assertTrue(response)
        response = self.client.get(reverse("project_series_add", args=[self.project.id]))
        self.assertEqual(response.status_code, 401)

    def test_series_view_no_restricted_series(self):
        """Test permission on series that has no restriction"""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now(),
                                                  is_public=True)
        current_permission = 'code_doc.series_view'

        self.assertTrue(self.first_user.has_perm(current_permission, new_series))
        self.assertFalse(self.first_user.has_perm(current_permission))
        self.assertIn(current_permission, self.first_user.get_all_permissions(new_series))
        self.assertNotIn(current_permission, self.first_user.get_all_permissions())

        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        self.assertTrue(user2.has_perm(current_permission, new_series))
        self.assertIn(current_permission, user2.get_all_permissions(new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions())

    def test_series_view_with_restriction_on_series(self):

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        new_series.view_users.add(self.first_user)
        current_permission = 'code_doc.series_view'

        self.assertTrue(self.first_user.has_perm(current_permission, new_series))
        self.assertFalse(self.first_user.has_perm(current_permission))
        self.assertIn(current_permission, self.first_user.get_all_permissions(new_series))
        self.assertNotIn(current_permission, self.first_user.get_all_permissions())

        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        self.assertFalse(user2.has_perm(current_permission, new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions(new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions())

    def test_series_view_with_restriction_on_series_through_groups(self):

        newgroup = Group.objects.create(name='group1')
        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        user2.groups.add(newgroup)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        new_series.view_users.add(self.first_user)
        current_permission = 'code_doc.series_view'

        self.assertTrue(self.first_user.has_perm(current_permission, new_series))
        self.assertFalse(self.first_user.has_perm(current_permission))
        self.assertIn(current_permission, self.first_user.get_all_permissions(new_series))
        self.assertNotIn(current_permission, self.first_user.get_all_permissions())

        # user2 not yet in the group
        self.assertFalse(user2.has_perm(current_permission, new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions(new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions())

        # user2 now in the group
        new_series.view_groups.add(newgroup)
        self.assertTrue(user2.has_perm(current_permission, new_series))
        self.assertIn(current_permission, user2.get_all_permissions(new_series))
        self.assertNotIn(current_permission, user2.get_all_permissions())

    def test_series_views_with_artifact_without_revision(self):
        """ Test the view in case an artifact has no revision. """

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now(),
                                                  is_public=True)

        art = Artifact.objects.create(project=self.project,
                                      md5hash='1',
                                      artifactfile='mais_oui!')

        art.project_series = [new_series]

        # Test the series details page (one artifact with no revision)
        response = self.client.get(reverse('project_series', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['artifacts']), 1)
        self.assertEqual(len(response.context['revisions']), 1)
        self.assertIsNone(response.context['revisions'][0])

    def test_modal_add_user_view_access(self):
        """ Test the access to the ModalAddUserView. """

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        # Anybody has access to the form, but permission will be required to add a user
        response = self.client.get(reverse('project_series_add_user', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

    def test_modal_add_user_post_forms(self):
        """ Test posting forms. """

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        form1 = ModalAddUserForm(self.project, new_series, data={})
        form2 = ModalAddUserForm(self.project, new_series, data={'username': 'dirk'})
        form3 = ModalAddUserForm(self.project, new_series, data={'username': self.first_user.username})

        # Check the validity of the forms
        self.assertFalse(form1.is_valid())
        self.assertFalse(form2.is_valid())
        self.assertTrue(form3.is_valid())

        path = reverse('project_series_add_user', args=[self.project.id, new_series.id])

        response1 = self.client.post(path, form1.data, follow=True)
        response2 = self.client.post(path, form2.data, follow=True)
        response3 = self.client.post(path, form3.data, follow=True)

        # Responses 1 and 2: the form is not valid, so no redirect
        self.assertEqual(len(response1.redirect_chain), 0)
        self.assertEqual(len(response2.redirect_chain), 0)

        # Response 3: the form is valid, but the user does not have the permissions
        last_url, status_code = response3.redirect_chain[-1]
        self.assertEqual(status_code, 302)
        self.assertIn(reverse('login'), last_url)

        # Now log in as super user
        response = self.client.login(username=self.first_user.username, password='test_series_user')
        self.assertTrue(response)

        # Create second user
        self.second_user = User.objects.create_user(username='dirk',
                                                    password='41',
                                                    email="dirk@dirk.com")

        # Form 2 should now be valid
        # Need to clean before asking for validity
        form2.full_clean()
        self.assertTrue(form2.is_valid())

        # Post
        response4 = self.client.post(path, form2.data, follow=True)

        # We should be back to the series_edit view
        last_url, status_code = response4.redirect_chain[-1]
        self.assertEqual(status_code, 302)
        self.assertEqual(last_url, reverse('project_series_edit', args=[self.project.id, new_series.id]))

        # Second user should now have view permission
        self.assertEqual(type(new_series.view_users.get(username=self.second_user.username)), User)
