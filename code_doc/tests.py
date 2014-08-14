from django.test import TestCase
from django.db import IntegrityError

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse

class ProjectTest(TestCase):
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project'
    
    self.first_user             = User.objects.create(username='toto')

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]
    

  def test_project_details(self):
    """Tests the project detail view"""
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['authors']), len(self.project.authors.all()))

    # non existing project
    response = self.client.get(reverse(self.path, args=[self.project.id+1]))
    self.assertEqual(response.status_code, 404)



class ProjectVersionTest(TestCase):
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project_version'
    
    self.first_user             = User.objects.create(username='toto')

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]  
  
  def test_project_version_empty(self):
    """Tests if the project version is ok"""

    # test non existing project 
    response = self.client.get(reverse(self.path, args=[self.project.id + 1]))
    self.assertEqual(response.status_code, 404)
    
    # test existing project
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 0)
    
  def test_project_version_create_new(self):
    """Test the creation of a new project version"""
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now())    
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 1)
    
class ProjectVersionArtifactTest(TestCase):
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project_artifacts'
    
    self.first_user             = User.objects.create_user(username='toto', password='titi')#, is_active=True)

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]
    
    self.new_version            = ProjectVersion.objects.create(version="12345", project = self.project, release_date = datetime.datetime.now())
    
    import StringIO
    self.imgfile      = StringIO.StringIO('GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    self.imgfile.name = 'test_img_file.gif'

  def test_uniqueness(self):
    with self.assertRaises(IntegrityError):
      new_version = ProjectVersion.objects.create(version="12345", project = self.project, release_date = datetime.datetime.now())
    
  def test_project_version_artifact_wrong(self):
    """Test if giving the wrong version yields the proper error""" 
    response = self.client.get(reverse(self.path, args=[self.project.id, self.new_version.version + 'x']))
    self.assertEqual(response.status_code, 404)
  
  def test_project_version_artifact(self):
    """Test the creation of a new project version and its artifacts"""
    response = self.client.get(reverse(self.path, args=[self.project.id, self.new_version.version]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['artifacts']), 0)
    
  def test_send_new_artifact_no_login(self):
    
    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=True)

    #print response
    #print response.redirect_chain
    self.assertEqual(response.status_code, 200)
    self.assertRedirects(response, reverse('login') + '?next=' + initial_path)
    #with open('wishlist.doc') as fp:
    #  self.client.post(self.path, {'name': 'fred', 'attachment': fp})


  def test_send_new_artifact_no_login_no_follow(self):
    

    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)
    self.assertEqual(response.status_code, 302) # redirection status

  def test_send_new_artifact_with_login(self):
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)

    import hashlib
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, hashlib.md5(self.imgfile.getvalue()).hexdigest())
    
