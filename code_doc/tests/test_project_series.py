from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse

import datetime

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..models.artifacts import Artifact
from ..forms.forms import ModalAddUserForm, ModalAddGroupForm


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
        """Test the view in case an artifact has no revision."""

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
        """Test the access to the ModalAddUserView."""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        url = reverse('project_series_add_user', args=[self.project.id, new_series.id])

        # Anonymous user (no permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # Logged-in user but without permission
        _ = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        response = self.client.login(username='user2', password='user2')
        self.assertTrue(response)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # Superuser, access granted
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_modal_add_group_view_access(self):
        """Test the access to the ModalAddGroupView."""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        url = reverse('project_series_add_group', args=[self.project.id, new_series.id])

        # Anonymous user (no permission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # Logged-in user but without permission
        _ = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        response = self.client.login(username='user2', password='user2')
        self.assertTrue(response)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # Superuser, access granted
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_modal_add_user_via_form(self):
        """Test posting forms to add user to view permissions."""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        # Log in as superuser and post forms
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        path = reverse('project_series_add_user', args=[self.project.id, new_series.id])

        # Create user
        dirk = User.objects.create_user(username='dirk',
                                        password='41',
                                        email="dirk@dirk.com")

        # Dirk should not have view permissions
        self.assertNotIn(dirk, new_series.view_users.all())

        # Forms
        form1 = ModalAddUserForm(self.project, new_series, data={})
        form2 = ModalAddUserForm(self.project, new_series, data={'username': 'fake_user'})
        form3 = ModalAddUserForm(self.project, new_series, data={'username': 'dirk'})

        # Form1 is empty
        self.assertFalse(form1.is_valid())
        response1 = self.client.post(path, form1.data)
        self.assertEqual(response1.status_code, 200)
        self.assertTemplateUsed(response1, 'code_doc/series/modal_add_user_form.html')
        self.assertFormError(response1, 'form', 'username',
                             'This field is required.')

        # Form2 is invalid: error
        self.assertFalse(form2.is_valid())
        response2 = self.client.post(path, form2.data)
        self.assertEqual(response2.status_code, 200)
        self.assertTemplateUsed(response2, 'code_doc/series/modal_add_user_form.html')
        self.assertFormError(response2, 'form', 'username',
                             'Username fake_user is not registered')

        # Form 3 is valid: redirect to edit page via success page.
        self.assertTrue(form3.is_valid())
        response3 = self.client.post(path, form3.data)
        self.assertEqual(response3.status_code, 200)
        self.assertTemplateUsed(response3, 'code_doc/series/modal_add_user_or_group_form_success.html')

        # Dirk should now have view permissions
        self.assertIn(dirk, new_series.view_users.all())

    def test_modal_add_group_via_form(self):
        """Test posting forms to add group to view permissions."""

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        # Log in as superuser and post forms
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)
        path = reverse('project_series_add_group', args=[self.project.id, new_series.id])

        # Create group
        test_group = Group.objects.create(name='test_group')

        # Test group should not have view permissions
        self.assertNotIn(test_group, new_series.view_groups.all())

        # Forms
        form1 = ModalAddGroupForm(self.project, new_series, data={})
        form2 = ModalAddGroupForm(self.project, new_series, data={'groupname': 'fake_group'})
        form3 = ModalAddGroupForm(self.project, new_series, data={'groupname': 'test_group'})

        # Form1 is empty: error
        self.assertFalse(form1.is_valid())
        response1 = self.client.post(path, form1.data)
        self.assertEqual(response1.status_code, 200)
        self.assertTemplateUsed(response1, 'code_doc/series/modal_add_group_form.html')
        self.assertFormError(response1, 'form', 'groupname',
                             'This field is required.')

        # Form2 is invalid: error
        self.assertFalse(form2.is_valid())
        response2 = self.client.post(path, form2.data)
        self.assertEqual(response2.status_code, 200)
        self.assertTemplateUsed(response2, 'code_doc/series/modal_add_group_form.html')
        self.assertFormError(response2, 'form', 'groupname',
                             'Group fake_group is not registered')

        # Form 3 is valid: redirect to edit page via success page.
        self.assertTrue(form3.is_valid())
        response3 = self.client.post(path, form3.data)
        self.assertEqual(response3.status_code, 200)
        self.assertTemplateUsed(response3, 'code_doc/series/modal_add_user_or_group_form_success.html')

        # Test group should now have view permissions
        self.assertIn(test_group, new_series.view_groups.all())

    def test_project_series_user_permissions_rendering(self):
        """Test the rendering of the user permissions."""

        from .tests import generate_random_string

        # Number of users to create
        num_xtra_users = 20
        for i in range(num_xtra_users):
            User.objects.create_user(username=generate_random_string(),
                                     password='password_' + str(i), email="user_%s@mail.com" % i)

        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Case 1: creating a series
        # We should see only the current user
        response = self.client.get(reverse("project_series_add", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        all_users = User.objects.all()
        perms = response.context['user_permissions']

        self.assertEqual(len(perms), 1)
        for user, checks in perms:
            self.assertEqual(user.username, self.first_user.username)
            for check in checks:
                self.assertTrue(check.data['selected'])
                self.assertTrue(check.data['attrs']['disabled'])

        # Case 2: editing a series
        # We should see all the users that have at least one permission
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
                if i % 4 == 1:
                    new_series.perms_users_artifacts_add.add(user)
                    new_series.perms_users_artifacts_del.add(user)

        response = self.client.get(reverse("project_series_edit", args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

        perms = response.context['user_permissions']
        rendered_users = zip(*perms)[0]

        # Database
        view_users = new_series.view_users.all()
        perm_art_add_users = new_series.perms_users_artifacts_add.all()
        perm_art_del_users = new_series.perms_users_artifacts_del.all()
        union_query = view_users.union(perm_art_add_users, perm_art_del_users)

        for user in all_users:
            if user in union_query:
                self.assertIn(user, rendered_users)
            else:
                self.assertNotIn(user, rendered_users)

        for user, checks in perms:
            for check in checks:

                # May be there is a better way to do this...
                name = check.data['name']
                status = check.data['selected']

                if name == 'view_users':
                    self.assertEqual(status, user in view_users)
                elif name == 'perms_users_artifacts_add':
                    self.assertEqual(status, user in perm_art_add_users)
                elif name == 'perms_users_artifacts_del':
                    self.assertEqual(status, user in perm_art_del_users)
                else:
                    self.fail('Unknown permission name %s' % name)

    def test_project_series_handle_user_permissions(self):
        """Test creating and modifying the user permissions."""

        # Log in as admin
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Create series
        url = reverse('project_series_add', args=[self.project.id])
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        # hidden field check
        self.assertEqual(response_get.context['form']['project'].value(),
                         self.project.id)

        release_date = [unicode(datetime.datetime.now().strftime("%Y-%m-%d"))]

        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        new_series = ProjectSeries.objects.all()[0]

        series_url = new_series.get_absolute_url()
        self.assertRedirects(response, series_url)

        # First user has all rights because he created the series
        self.assertIn(self.first_user, new_series.view_users.all())
        self.assertIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertIn(self.first_user, new_series.perms_users_artifacts_del.all())

        # From now on, we will modify the permissions
        url = reverse('project_series_edit', args=[self.project.id, new_series.id])
        url_redirect = series_url

        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        # checking back that the user appears when updating the form
        form = response_get.context['form']
        self.assertEqual([self.first_user.id], form['view_users'].value())
        self.assertEqual([self.first_user.id], form['perms_users_artifacts_add'].value())
        self.assertEqual([self.first_user.id], form['perms_users_artifacts_del'].value())
        self.assertEqual(response_get.context['form']['project'].value(),
                         self.project.id)

        # Removing view permissions for all users
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': response_get.context['series'].id,
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_users': [],
            'perms_users_artifacts_add': [self.first_user.id],
            'perms_users_artifacts_del': [self.first_user.id],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(self.first_user, new_series.view_users.all())
        self.assertIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertIn(self.first_user, new_series.perms_users_artifacts_del.all())

        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        # checking the coherence of the update view
        form = response_get.context['form']
        self.assertEqual([], form['view_users'].value())
        self.assertEqual([self.first_user.id], form['perms_users_artifacts_add'].value())
        self.assertEqual([self.first_user.id], form['perms_users_artifacts_del'].value())
        self.assertEqual(response_get.context['form']['project'].value(),
                         self.project.id)

        # Remove perms_users_artifacts_add
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': response_get.context['series'].id,
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_users': [],
            'perms_users_artifacts_add': [],
            'perms_users_artifacts_del': [self.first_user.id],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(self.first_user, new_series.view_users.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertIn(self.first_user, new_series.perms_users_artifacts_del.all())
        self.assertEqual(response_get.context['form']['project'].value(),
                         self.project.id)

        # checking the content of the returned form for editing (again)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        # checking the coherence of the update view
        form = response_get.context['form']
        self.assertEqual([], form['view_users'].value())
        self.assertEqual([], form['perms_users_artifacts_add'].value())
        self.assertEqual([self.first_user.id], form['perms_users_artifacts_del'].value())

        # Remove perms_users_artifacts_del
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': response_get.context['series'].id,
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_users': [],
            'perms_users_artifacts_add': [],
            'perms_users_artifacts_del': [],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(self.first_user, new_series.view_users.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_del.all())
        self.assertEqual(response_get.context['form']['project'].value(),
                         self.project.id)

        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        # checking the coherence of the update view
        form = response_get.context['form']
        self.assertEqual([], form['view_users'].value())
        self.assertEqual([], form['perms_users_artifacts_add'].value())
        self.assertEqual([], form['perms_users_artifacts_del'].value())

        # Let's try to give first_user back all his permissions
        # It won't work because the user is not among the available choices anymore
        # (one needs to add him through the modal)
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': response_get.context['series'].id,
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_users': [self.first_user.id],
            'perms_users_artifacts_add': [self.first_user.id],
            'perms_users_artifacts_del': [self.first_user.id],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        # Check form errors
        for m2m_field in ('view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del'):
            self.assertFormError(response, 'form', m2m_field,
                                 'Select a valid choice. %s is not one of the available choices.' % self.first_user.id)

        self.assertNotIn(self.first_user, new_series.view_users.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_del.all())

        # now does the checks with several users
        list_users = []  # self.first_user not part of it
        for i in range(10):
            user = User.objects.create_user(username='userXXX%d' % i,
                                            password='test_series_user',
                                            email="b%d@b.com" % i)
            list_users.append(user)

        # what we want now is to check that mixing things up with the permissions and several users
        # does consistent work on saving
        import random
        all_users_to_check = random.sample(list_users, 7)

        user_permissions = {}
        for index, user in enumerate(all_users_to_check):
            perm = ['view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del'][index % 3]  # to make sure we have one of each
            getattr(new_series, perm).add(user)
            user_permissions[user] = perm

        # now rendering the form
        # we should see all users
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        form = response_get.context['form']

        for perm in ('view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del'):
            list_users = [user for user, permission in user_permissions.items() if permission == perm]

            self.assertEqual([_.id for _ in sorted(list_users, key=lambda x: x.username)],
                             form[perm].value())

        for user in list_users + [self.first_user]:
            if user in all_users_to_check:
                self.assertContains(response_get, user.username, 1)
            else:
                if user is self.first_user:
                    self.assertContains(response_get, user.username, 1)  # login button only
                else:
                    self.assertContains(response_get, user.username, 0)

        # we should see the correct permissions for all of the users
        sorted_users = sorted(all_users_to_check, key=lambda x: x.username)
        for user in all_users_to_check:
            index = sorted_users.index(user)

            for perm in ['view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del']:
                if getattr(new_series, perm).filter(id=user.id).count() == 1:
                    checked = 'checked'
                else:
                    checked = ''
                self.assertContains(
                    response_get,
                    '<input type="checkbox" name="{permission}" value="{userid}" {checked} id="id_{permission}_{index}" />'.format(
                        permission=perm,
                        index=index,
                        userid=user.id,
                        checked=checked
                    ),
                    count=1,
                    html=True
                )

        # now we are rotating some permissions and checking that things are correct at save time
        users_artifact_add = [_ for _ in all_users_to_check if user_permissions[_] == 'perms_users_artifacts_add']
        users_view = [_ for _ in all_users_to_check if user_permissions[_] == 'view_users']
        user1, user2 = random.choice(users_artifact_add), random.choice(users_view)

        form = response_get.context['form']
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': response_get.context['series'].id,
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_users': form['view_users'].value() + [user1.id],
            'perms_users_artifacts_add': form['perms_users_artifacts_add'].value() + [user2.id],
            'perms_users_artifacts_del': form['perms_users_artifacts_del'].value(),

        }
        # cannot handle the ids directly
        if 0:
            for user in all_users_to_check:
                index = sorted_users.index(user)
                for perm in ['view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del']:
                    data['id_{perm}_{index}'.format(perm=perm, index=index)] = True

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        response_get = self.client.get(url)
        print response_get

        # all previous users should be here
        for user in list_users + [self.first_user]:
            if user in all_users_to_check:
                self.assertContains(response_get, user.username, 1)
            else:
                if user is self.first_user:
                    self.assertContains(response_get, user.username, 1)  # login button only
                else:
                    self.assertContains(response_get, user.username, 0)

        #
        self.assertNotIn(self.first_user, new_series.view_users.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_add.all())
        self.assertNotIn(self.first_user, new_series.perms_users_artifacts_del.all())
        self.assertIn(user1, new_series.view_users.all())
        self.assertIn(user2, new_series.view_users.all())
        self.assertIn(user1, new_series.perms_users_artifacts_add.all())
        self.assertIn(user2, new_series.perms_users_artifacts_add.all())
        self.assertNotIn(user1, new_series.perms_users_artifacts_del.all())
        self.assertNotIn(user2, new_series.perms_users_artifacts_del.all())

    def test_project_series_group_permissions_rendering(self):
        """Test the rendering of the grouop permissions."""

        from .tests import generate_random_string

        # Number of groups to create
        num_xtra_groups = 20
        for i in range(num_xtra_groups):
            Group.objects.create(name=generate_random_string())

        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Case 1: creating a series
        # We should not see any group
        response = self.client.get(reverse("project_series_add", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        perms = response.context['group_permissions']
        self.assertEqual(len(perms), 0)

        # Case 2: editing a series
        # We should see all the groups that have at least one permission
        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())

        all_groups = Group.objects.all()

        for i, group in enumerate(all_groups):
            if i % 2 == 0:
                new_series.view_groups.add(group)

                if i % 4 == 0:
                    new_series.perms_groups_artifacts_add.add(group)
                else:
                    new_series.perms_groups_artifacts_del.add(group)
            else:
                if i % 4 == 1:
                    new_series.perms_groups_artifacts_add.add(group)
                    new_series.perms_groups_artifacts_del.add(group)

        response = self.client.get(reverse("project_series_edit", args=[self.project.id, new_series.id]))
        self.assertEqual(response.status_code, 200)

        perms = response.context['group_permissions']
        rendered_groups = zip(*perms)[0]

        # Database
        view_groups = new_series.view_groups.all()
        perm_art_add_groups = new_series.perms_groups_artifacts_add.all()
        perm_art_del_groups = new_series.perms_groups_artifacts_del.all()
        union_query = view_groups.union(perm_art_add_groups, perm_art_del_groups)

        for group in all_groups:
            if group in union_query:
                self.assertIn(group, rendered_groups)
            else:
                self.assertNotIn(group, rendered_groups)

        for group, checks in perms:
            for check in checks:

                # May be there is a better way to do this...
                name = check.data['name']
                status = check.data['selected']

                if name == 'view_groups':
                    self.assertEqual(status, group in view_groups)
                elif name == 'perms_groups_artifacts_add':
                    self.assertEqual(status, group in perm_art_add_groups)
                elif name == 'perms_groups_artifacts_del':
                    self.assertEqual(status, group in perm_art_del_groups)
                else:
                    self.fail('Unknown permission name %s' % name)

    def test_project_series_handle_group_permissions(self):
        """Test creating and modifying the group permissions."""

        # Log in as admin
        response = self.client.login(username='test_series_user', password='test_series_user')
        self.assertTrue(response)

        # Create series
        url = reverse('project_series_add', args=[self.project.id])
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

        release_date = [unicode(datetime.datetime.now().strftime("%Y-%m-%d"))]

        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date,
        }

        response = self.client.post(url, data)
        new_series = ProjectSeries.objects.all()[0]

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_series', args=[self.project.id, new_series.id]))

        # Create group and give it all permissions
        test_group = Group.objects.create(name='test_group')
        new_series.view_groups.add(test_group)
        new_series.perms_groups_artifacts_add.add(test_group)
        new_series.perms_groups_artifacts_del.add(test_group)

        # Group should have all permissions now
        self.assertIn(test_group, new_series.view_groups.all())
        self.assertIn(test_group, new_series.perms_groups_artifacts_add.all())
        self.assertIn(test_group, new_series.perms_groups_artifacts_del.all())

        # From now on, we will modify the permissions
        url = reverse('project_series_edit', args=[self.project.id, new_series.id])
        url_redirect = reverse('project_series', args=[self.project.id, new_series.id])

        # Removing view permissions
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_groups': [],
            'perms_groups_artifacts_add': [test_group.id],
            'perms_groups_artifacts_del': [test_group.id],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(test_group, new_series.view_groups.all())
        self.assertIn(test_group, new_series.perms_groups_artifacts_add.all())
        self.assertIn(test_group, new_series.perms_groups_artifacts_del.all())

        # Remove perms_groups_artifacts_add
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_groups': [],
            'perms_groups_artifacts_add': [],
            'perms_groups_artifacts_del': [test_group.id],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(test_group, new_series.view_groups.all())
        self.assertNotIn(test_group, new_series.perms_groups_artifacts_add.all())
        self.assertIn(test_group, new_series.perms_groups_artifacts_del.all())

        # Remove perms_groups_artifacts_add
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_groups': [],
            'perms_groups_artifacts_add': [],
            'perms_groups_artifacts_del': [],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url_redirect)

        self.assertNotIn(test_group, new_series.view_groups.all())
        self.assertNotIn(test_group, new_series.perms_groups_artifacts_add.all())
        self.assertNotIn(test_group, new_series.perms_groups_artifacts_del.all())

        # Let's try to give the group back all his permissions
        # It won't work because it is not among the available choices anymore (one needs to add it through the modal)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)
        data = {
            'csrf_token': response_get.context['csrf_token'],
            'series': 'New series',
            'project': response_get.context['project'].id,
            'release_date': release_date,
            'view_groups': [test_group.id],
            'perms_groups_artifacts_add': [test_group.id],
            'perms_groups_artifacts_del': [test_group.id],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        # Check form errors
        for m2m_field in ('view_groups', 'perms_groups_artifacts_add', 'perms_groups_artifacts_del'):
            self.assertFormError(response, 'form', m2m_field,
                                 'Select a valid choice. %s is not one of the available choices.' % test_group.id)

