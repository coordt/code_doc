from django.test import LiveServerTestCase
from django.test import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from code_doc.models import Project, Author, ProjectVersion
from code_doc.utils.send_new_artifact import PostMultipartWithSession

import tempfile
import datetime
import os
import json

class ProjectLiveSendArtifactTest(LiveServerTestCase):
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
    
    self.version                = ProjectVersion.objects.create(version="12345", project = self.project, release_date = datetime.datetime.now())
    

  def test_send_new_file_new_api(self):
    """In this test, we know in advance the login url"""
    self.assertEqual(len(self.version.artifacts.all()), 0)
    with tempfile.NamedTemporaryFile() as f:

      f.write('GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
      f.seek(0)
      
      fields = {}
      fields['description'] = "revision from client based application"
  
      files = []
      
      # see remarks in test test_send_new_file
      files.append(('artifactfile', f))
      
      instance = PostMultipartWithSession(host=self.live_server_url)
      
      post_url = '/project/%d/%d/add' % (self.project.id, self.version.id)
      
      instance.login(login_page = "/accounts/login/", 
                     username = self.first_user.username,
                     password = 'test_version_user')
      
      f.seek(0)
      ret = instance.post_multipart( 
              post_url, 
              fields, 
              files,
              avoid_redirections = False)


      self.assertEqual(len(self.version.artifacts.all()), 1)
      artifact = self.version.artifacts.all()[0]
      self.assertEqual(artifact.filename(), os.path.basename(f.name))
      
      import hashlib
      f.seek(0)
      self.assertEqual(artifact.md5hash, hashlib.md5(f.read()).hexdigest())
      
      self.assertEqual(ret.code, 200)
      
      
  def test_get_redirection(self):
    """Tests if the redirection is ok"""
    instance = PostMultipartWithSession(host=self.live_server_url)
    
    post_url = '/s/%s/%s/' % (self.project.name, self.version.version)
    response = instance.get(post_url)
    redir = instance.get_redirection(post_url)
    self.assertEqual(redir, reverse('project_revision', args=[self.project.id, self.version.id]))


  def test_get_json_for_project_id(self):
    """Tests if the json mapping the name of project/version to ids is ok"""
    
    instance = PostMultipartWithSession(host=self.live_server_url)
    instance.login(login_page = "/accounts/login/", 
                     username = self.first_user.username,
                     password = 'test_version_user')
    
    post_url = '/api/%s/%s/' % (self.project.name, self.version.version)
    response = instance.get(post_url)
    
    dic_ids = json.loads(response.read())
    self.assertEquals(dic_ids['project_id'], self.project.id)
    self.assertEquals(dic_ids['version_id'], self.version.id)



