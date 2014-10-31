from django.test import TestCase
from django.db import IntegrityError



# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion, Artifact
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.files import File

from django.core.urlresolvers import reverse

from django.conf import settings

import tempfile
import tarfile
import os
import datetime


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

  def test_version_uniqueness(self):
    with self.assertRaises(IntegrityError):
      new_version = ProjectVersion.objects.create(version="12345", project = self.project, release_date = datetime.datetime.now())
    
  def test_project_revision_artifact_wrong(self):
    """Test if giving the wrong version yields the proper error""" 
    response = self.client.get(reverse(self.path, args=[self.project.id, self.new_version.version + 'x']))
    self.assertEqual(response.status_code, 404)
  
  def test_project_revision_artifact(self):
    """Test the creation of a new project version and its artifacts"""
    response = self.client.get(reverse(self.path, args=[self.project.id, self.new_version.version]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['artifacts']), 0)
    
  def test_send_new_artifact_no_login(self):
    """This test should redirect to the login page: we cannot upload a file without a proper login"""
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
    """This test should indicate that no login means redirection"""
    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)
    self.assertEqual(response.status_code, 302) # redirection status

  def test_send_new_artifact_with_login(self):
    """Testing the upload capabilities. The returned hash should be ok"""
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)
    
    self.assertEqual(self.new_version.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)

    import hashlib
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, hashlib.md5(self.imgfile.getvalue()).hexdigest())
    self.assertEqual(self.new_version.artifacts.count(), 1)
    
  def test_send_new_artifact_with_login_twice(self):
    """Sending the same file twice should not create a new file"""
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    self.assertEqual(self.new_version.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_version.version])
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)
    
    import hashlib
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, hashlib.md5(self.imgfile.getvalue()).hexdigest())
    
    self.assertEqual(self.new_version.artifacts.count(), 1)    
    
    # warning, the input file here should be reseted to its origin 
    self.imgfile.seek(0)
    
    # second send should not create a new one for a specific revision
    response = self.client.post(initial_path, 
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)
    
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, hashlib.md5(self.imgfile.getvalue()).hexdigest())
    self.assertEqual(self.new_version.artifacts.count(), 1)    


  def test_create_documentation_artifact(self):
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE, suffix='.tar.bz2') as f:
      # create a temporary tar object
      tar = tarfile.open(fileobj=f, mode='w:bz2')
      
      from inspect import getsourcefile
      source_file = getsourcefile(lambda _: None)
      
      tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
      tar.close()
      
      f.seek(0)
      test_file = SimpleUploadedFile('filename.tar.bz2', f.read())
      
      
      new_artifact = Artifact.objects.create(
                        project_version=self.new_version,
                        md5hash = '1',
                        description = 'test artifact',
                        is_documentation = True,
                        documentation_entry_file = os.path.basename(__file__),
                        artifactfile = test_file)
      
      new_artifact.save()