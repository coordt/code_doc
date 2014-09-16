from django.test import TestCase
from django.db import IntegrityError

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group

from django.core.urlresolvers import reverse


class ProjectRevisionsTest(TestCase):
  """Testing the project version functionality"""
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project_revisions_all'
    
    self.first_user             = User.objects.create_user(username='test_version_user', password='test_version_user')

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]  
  
  def test_project_revision_empty(self):
    """Tests if the project version is ok"""

    # test non existing project 
    response = self.client.get(reverse(self.path, args=[self.project.id + 1]))
    self.assertEqual(response.status_code, 404)
    
    # test existing project
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 0)
    
  def test_project_revision_create_new_no_public(self):
    """Test the creation of a new project version, with non public visibility"""
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now())    
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 0)
    self.assertEqual(len(response.context['versions']), len(response.context['last_update']))

  def test_project_revision_create_new_public(self):
    """Test the creation of a new project version, with public visibility"""
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now(), is_public=True)    
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 1)
    self.assertEqual(len(response.context['versions']), len(response.context['last_update']))
  
  
  def test_project_revision_addview(self):
    """Test the view access of an existing project"""
    
    response = self.client.login(username='test_version_user', password='test_version_user')
    self.assertTrue(response)
    response = self.client.get(reverse("project_revision_add", args=[self.project.id]))
    self.assertEqual(response.status_code, 200)

  def test_project_revision_addview_non_existing(self):
    """Test the view access of an non existing project"""
    
    response = self.client.login(username='test_version_user', password='test_version_user')
    self.assertTrue(response)    
    response = self.client.get(reverse("project_revision_add", args=[self.project.id+1]))
    
    # returns unauthorized to avoid the distinction between non existing project spoofing and the authorization. 
    self.assertEqual(response.status_code, 401)
     
  
  def test_project_revision_addview_restrictions(self):
    """Tests if the admins have the right to modify the project configuration, and the others don't"""
    
    # user2 is not admin of this project
    user2 = User.objects.create_user(username='user2', password='user2')
    response = self.client.login(username='user2', password='user2')
    self.assertTrue(response)
    response = self.client.get(reverse("project_revision_add", args=[self.project.id]))
    self.assertEqual(response.status_code, 401)
    
    
    
  def test_version_view_no_restricted_version(self):
    """Test permission on versions that has no restriction"""
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now(), is_public=True)    
    current_permission = 'code_doc.version_view'
    
    
    self.assertTrue(self.first_user.has_perm(current_permission, new_version))
    self.assertFalse(self.first_user.has_perm(current_permission))
    self.assertIn(current_permission, self.first_user.get_all_permissions(new_version))
    self.assertNotIn(current_permission, self.first_user.get_all_permissions())

    user2 = User.objects.create_user(username='user2', password='user2')
    self.assertTrue(user2.has_perm(current_permission, new_version))
    self.assertIn(current_permission, user2.get_all_permissions(new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions())    
    
    
  def test_version_view_with_restriction_on_version(self):
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now())
    new_version.view_users.add(self.first_user)
    current_permission = 'code_doc.version_view'
    
    self.assertTrue(self.first_user.has_perm(current_permission, new_version))
    self.assertFalse(self.first_user.has_perm(current_permission))
    self.assertIn(current_permission, self.first_user.get_all_permissions(new_version))
    self.assertNotIn(current_permission, self.first_user.get_all_permissions())

    user2 = User.objects.create_user(username='user2', password='user2')
    self.assertFalse(user2.has_perm(current_permission, new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions(new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions())   
    
    
  def test_version_view_with_restriction_on_version_through_groups(self):

    newgroup = Group.objects.create(name='group1')
    user2 = User.objects.create_user(username='user2', password='user2')
    user2.groups.add(newgroup)
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now())
    new_version.view_users.add(self.first_user)
    current_permission = 'code_doc.version_view'
    
    self.assertTrue(self.first_user.has_perm(current_permission, new_version))
    self.assertFalse(self.first_user.has_perm(current_permission))
    self.assertIn(current_permission, self.first_user.get_all_permissions(new_version))
    self.assertNotIn(current_permission, self.first_user.get_all_permissions())


    # user2 not yet in the group
    self.assertFalse(user2.has_perm(current_permission, new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions(new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions())   
    
    # user2 now in the group
    new_version.view_groups.add(newgroup)
    self.assertTrue(user2.has_perm(current_permission, new_version))
    self.assertIn(current_permission, user2.get_all_permissions(new_version))
    self.assertNotIn(current_permission, user2.get_all_permissions())   
          