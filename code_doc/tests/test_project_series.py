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

        # Anonymous user (no permission)
        response = self.client.get(reverse('project_series_add_user', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 401)

        # Logged-in user but without permission
        _ = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        response = self.client.login(username='user2', password='user2')
        self.assertTrue(response)
        response = self.client.get(reverse('project_series_add_user', args=[self.project.id, new_series.id]), follow=True)
        self.assertEqual(response.status_code, 401)

        # Superuser, access granted
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        response = self.client.get(reverse('project_series_add_user', args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

    def test_modal_add_user_post_forms(self):
        """ Test posting forms. """

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        # Log in as superuser and post forms
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        path = reverse('project_series_add_user', args=[self.project.id, new_series.id])

        # Forms
        form1 = ModalAddUserForm(self.project, new_series, data={})
        form2 = ModalAddUserForm(self.project, new_series, data={'username': 'dirk'})
        form3 = ModalAddUserForm(self.project, new_series, data={'username': 'test_series_user'})

        # Form1 is empty
        self.assertFalse(form1.is_valid())
        response1 = self.client.post(path, form1.data)
        self.assertEqual(response1.status_code, 200)
        self.assertTemplateUsed(response1, 'code_doc/series/modal_add_user_form.html')

        # Form2 is invalid: error thrown
        self.assertFalse(form2.is_valid())
        response2 = self.client.post(path, form2.data)
        self.assertEqual(response2.status_code, 200)
        self.assertTemplateUsed(response2, 'code_doc/series/modal_add_user_form.html')
        self.assertContains(response2, 'Username dirk is not registered')

        # Form 3 is valid: redirect to edit page via success page.
        self.assertTrue(form3.is_valid())
        response3 = self.client.post(path, form3.data)
        self.assertEqual(response3.status_code, 200)
        self.assertTemplateUsed(response3, 'code_doc/series/modal_add_user_form_success.html')

    def test_add_user_with_view_permission(self):
        """ Test giving view permission to a new user. """

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        # Log in as superuser and post forms
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        path = reverse('project_series_add_user', args=[self.project.id, new_series.id])

        # Create second user
        self.second_user = User.objects.create_user(username='dirk',
                                                    password='41',
                                                    email="dirk@dirk.com")
        # Form should now be valid
        form = ModalAddUserForm(self.project, new_series, data={'username': 'dirk'})
        self.assertTrue(form.is_valid())

        # Post form
        response = self.client.post(path, form.data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Dirk should now have view permission
        self.assertTrue(new_series.has_user_series_view_permission(self.second_user))

    def test_project_series_permissions_rendering(self):
        """ Test the rendering of the user permissions. """

        from .tests import generate_random_string

        # Number of users to create
        num_xtra_users = 20
        for i in range(num_xtra_users):
            User.objects.create_user(username=generate_random_string(),
                                     password='password_' + str(i), email="%s@mail.com" % i)

        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Case 1: creating a series
        # We should see all users, with all permissions unchecked
        response = self.client.get(reverse("project_series_add", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        all_users = User.objects.all()
        perms = response.context['user_permissions']

        self.assertEqual(len(perms), num_xtra_users + 1)
        for _, user, checks in perms:
            self.assertIn(user, all_users)
            for check in checks:
                self.assertFalse(check.data['selected'])

        # Case 2: editing a series
        # We should see only the users with view permissions, with the appropriate checkboxes checked
        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        for i, user in enumerate(all_users):
            if i % 2 == 0:
                new_series.view_users.add(user)

                if i % 4 == 0:
                    new_series.perms_users_artifacts_add.add(user)
                else:
                    new_series.perms_users_artifacts_del.add(user)
            else:

                # Even if we add artifact permissions to some users, they should not appear
                if (i - 1) % 4 == 0:
                    new_series.perms_users_artifacts_add.add(user)
                    new_series.perms_users_artifacts_del.add(user)

        response = self.client.get(reverse("project_series_edit", args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

        perms = response.context['user_permissions']
        view_users = zip(*perms)[1]

        for user in all_users:
            if not new_series.has_user_series_view_permission(user):
                self.assertNotIn(user, view_users)
            else:
                self.assertIn(user, view_users)

        for _, user, checks in perms:
            for check in checks:

                # May be there is a better way to do this...
                name = check.data['name']
                status = check.data['selected']

                if name == 'view_users':
                    self.assertEqual(status, new_series.has_user_series_view_permission(user))
                elif name == 'perms_users_artifacts_add':
                    self.assertEqual(status, new_series.has_user_series_artifact_add_permission(user))
                elif name == 'perms_users_artifacts_del':
                    self.assertEqual(status, new_series.has_user_series_artifact_delete_permission(user))
                else:
                    self.fail('Unknown permission name %s' % name)

    def test_project_series_handle_user_permissions(self):
        """Test creating and modifying the user permissions."""

        # Log in as admin
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Create second user
        self.second_user = User.objects.create_user(username='dirk',
                                                    password='41',
                                                    email="dirk@dirk.com")
        all_users = User.objects.all()
        all_users_ids = [user.pk for user in all_users]

        # Create series and give permissions to both users
        url = reverse('project_series_add', args=[self.project.id])
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        data = {}
        data['csrf_token'] = response_get.context['csrf_token']
        data['series'] = 'New series'
        data['release_date'] = [unicode(datetime.datetime.now().strftime("%Y-%m-%d"))]
        data['view_users'] = all_users_ids

        response = self.client.post(url, data, follow=True)
        new_series = ProjectSeries.objects.get(id=response.context['series'].id)

        self.assertEqual(response.status_code, 200)  # 200 instead of 302 because we use follow = True to get the series id
        self.assertRedirects(response, reverse('project_series', args=[self.project.id, new_series.id]))

        # First user has all rights because he created the series
        self.assertTrue(new_series.has_user_series_view_permission(self.first_user))
        self.assertTrue(new_series.has_user_series_artifact_add_permission(self.first_user))
        self.assertTrue(new_series.has_user_series_artifact_delete_permission(self.first_user))

        # Second user is only granted view permission
        self.assertTrue(new_series.has_user_series_view_permission(self.second_user))
        self.assertFalse(new_series.has_user_series_artifact_add_permission(self.second_user))
        self.assertFalse(new_series.has_user_series_artifact_delete_permission(self.second_user))

        # From now on, we will modify the permissions
        url = reverse('project_series_edit', args=[self.project.id, new_series.id])

        # Add perms_users_artifacts_add
        data['perms_users_artifacts_add'] = all_users_ids

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_series', args=[self.project.id, new_series.id]))

        self.assertTrue(new_series.has_user_series_view_permission(self.second_user))
        self.assertTrue(new_series.has_user_series_artifact_add_permission(self.second_user))
        self.assertFalse(new_series.has_user_series_artifact_delete_permission(self.second_user))

        # Add perms_users_artifacts_del
        data['perms_users_artifacts_del'] = all_users_ids

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_series', args=[self.project.id, new_series.id]))

        self.assertTrue(new_series.has_user_series_view_permission(self.second_user))
        self.assertTrue(new_series.has_user_series_artifact_add_permission(self.second_user))
        self.assertTrue(new_series.has_user_series_artifact_delete_permission(self.second_user))

        # Remove all permissions to both users:
        #    - first_user will keep everything as he created the series
        #    - second_user will lose everything
        data['view_users'] = []
        data['perms_users_artifacts_del'] = []
        data['perms_users_artifacts_add'] = []

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_series', args=[self.project.id, new_series.id]))

        self.assertFalse(new_series.has_user_series_view_permission(self.second_user))
        self.assertFalse(new_series.has_user_series_artifact_add_permission(self.second_user))
        self.assertFalse(new_series.has_user_series_artifact_delete_permission(self.second_user))

        self.assertTrue(new_series.has_user_series_view_permission(self.first_user))
        self.assertTrue(new_series.has_user_series_artifact_add_permission(self.first_user))
        self.assertTrue(new_series.has_user_series_artifact_delete_permission(self.first_user))
        self.assertFalse(self.first_user.is_superuser)
