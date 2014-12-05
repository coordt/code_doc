# -*- coding: utf-8 -*-


__doc__ = """
The intent of this module is to send a filled form to the coffeepi server, without using any of the Django related stuff
and possibly no extra packages. The form may contain files. The main class is :class:`PostMultipartWithSession`.
"""



import httplib
import mimetypes
import mimetools
import urllib2
import cookielib
import os
import re
import urllib
import StringIO
import types



class PostMultipartWithSession(object):
  """Creates and maintains a session with a Django server, and allows to fill forms (any type of fields
  including files)

  This class is used in the project in order to send information to Django.
  """
    
  class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    """Small utility class allowing to follow redirections or not"""
    
    def __init__(self, instance_name = None, *args, **kwargs):
      self.instance_name = instance_name
      self.redirection_map = {}
      self.avoid_redirections = False
      
    
    def http_error_302(self, req, fp, code, msg, headers):
      
      if 0:
        print "\tRedirection intercepted", self.instance_name
        print "\tURL request", req.get_full_url()
        print "\tHeaders", headers.items()
        print "\tCode", code
        print "\tMessage", msg
        #print "\tFP", fp.read()
      
      redir = "Location" in headers 
      if redir:
        self.redirection_map[req.get_full_url()] = headers["Location"]
      
      if(self.avoid_redirections and redir):
        raise urllib2.HTTPError(
                  req.get_full_url(), 
                  401, 
                  "redirections disabled",
                  headers, None)
      
      return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
  
    http_error_301 = http_error_303 = http_error_307 = http_error_302    
  
  def __init__(self, host):
    """Initializes the current instance
    
    :param string host: the host to which we connect. It should include the fully qualified URL (eg. http://mycoffeepi:8081).
    """
    
    self.cookies = cookielib.CookieJar()
    self.redirection_intercepter = PostMultipartWithSession.MyHTTPRedirectHandler("redir")

    self.opener = urllib2.build_opener(self.redirection_intercepter, 
                                       urllib2.HTTPCookieProcessor(self.cookies))
    
    urllib2.install_opener(self.opener)
    self.host = host
    
    
    
  def get_redirection(self, initial_page):
    """Returns the redirection from one page to another if it exists, None otherwise"""
    
    value = self.redirection_intercepter.redirection_map.get(self.host + initial_page, None)
    if value is None:
      return value
    
    if value.find(self.host) == 0:
      value = value[len(self.host):]
    
    pos = value.find('?') 
    if pos > 0:
      value = value[:pos]
    
    return value
    
  def login(self, login_page = None, username = None, password = None):
    """Allow to log in to Django, and store the credentials into the current session"""
    
    self.redirection_intercepter.avoid_redirections = False
    request = urllib2.Request(self.host + login_page)
    response= self.opener.open(request)
    content = response.read()

    # csrf token needed for the login forms
    token = self._get_csrf_token(content)
    
    login_data = dict(username=username, 
                      password=password, 
                      csrfmiddlewaretoken=token)
    request = urllib2.Request(response.geturl(), data=urllib.urlencode(login_data))
    response = self.opener.open(request)
    #content = response.read()
    
    return response   
      
  def _get_csrf_token(self, content):
    """Returns the csrf token put (hidden) into a form"""
    token = None
    pos = content.find('csrfmiddlewaretoken')
    if pos > -1:
      for c in self.cookies: 
        if c.name == 'csrftoken':
          token = c.value
          break
      else:
        print 'Cookie not found'
        pos = content.find('value', pos)
        m = re.match('value=\'([\w\d]+?)\'', content[pos:])
        if not m is None:
          token = m.group(1)
  
    return token
  
  def _encode_multipart_formdata(self, fields, files):
      """Internal helper function for helping in the construction of form requests.
      
      :param iterable fields: sequence of tuples (name, value) elements for regular form fields.
      :param iterable files: sequence of tuples (name, filename, value) elements for data to be uploaded as files
      :returns: (content_type, body) ready for httplib.HTTP instance
      
      """
      
      
      mime_boundary = mimetools.choose_boundary()
      
      buf = StringIO.StringIO()
      for (key, value) in fields.items():
        buf.write('--%s\r\n' % mime_boundary)
        buf.write('Content-Disposition: form-data; name="%s"' % key)
        buf.write('\r\n\r\n' + value + '\r\n')
      for (key, filename_to_add_or_file_descriptor) in files:
        
        if(type(filename_to_add_or_file_descriptor) is types.StringType or type(filename_to_add_or_file_descriptor) is types.UnicodeType):  
          fd = open(filename_to_add_or_file_descriptor, 'rb')
          filename = os.path.basename(filename_to_add_or_file_descriptor)
          contenttype = mimetypes.guess_type(filename_to_add_or_file_descriptor)[0] or 'application/octet-stream'
        else:
          fd = filename_to_add_or_file_descriptor
          filename = filename_to_add_or_file_descriptor.name
          contenttype = 'application/octet-stream' # we cannot be more precise here
        buf.write('--%s\r\n' % mime_boundary)
        buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
        buf.write('Content-Type: %s\r\n' % contenttype)
        fd.seek(0)
        buf.write('\r\n' + fd.read() + '\r\n')      
        
      buf.write('--' + mime_boundary + '--\r\n\r\n')
      
      body = buf.getvalue()
      content_type = 'multipart/form-data; boundary=%s' % mime_boundary
      return content_type, body
    
  def get(self, page, avoid_redirections = False):
    
    self.redirection_intercepter.avoid_redirections = avoid_redirections
    server_url = "%s%s" % (self.host, page)
  
    request = urllib2.Request(server_url)
    try:
      response= self.opener.open(request)
    except urllib2.HTTPError, e:
      return e
    
    return response
    
  def post_multipart(self, page_url, form_fields, form_files, avoid_redirections = True):
    """ Post form_fields and form_files to an http://host/page_url as multipart/form-data.
      
      :param form_fields: is a sequence of (name, value) elements for regular form form_fields.
      :param form_files: is a sequence of (name, filename, value) elements for data to be uploaded as form_files
      :param avoid_redirections: True if the request does not follow any redirections (login redirection for instance)
      :returns: the server's response page_url.
    """
    server_url = "%s%s" % (self.host, page_url)
    
    # get for the cookie and opening a session
    request = urllib2.Request(server_url)
    self.redirection_intercepter.avoid_redirections = avoid_redirections
    try:
      response= self.opener.open(request)
    except urllib2.HTTPError, e:
      return e
    
    content = response.read()
    token = self._get_csrf_token(content)

    
    fields_with_token = dict(form_fields.items())
    if not token is None:
      fields_with_token['csrfmiddlewaretoken'] = token    

    content_type, body = self._encode_multipart_formdata(fields_with_token, form_files)
    
    headers = {'Content-Type': content_type, 'Content-Length': str(len(body))}
    
    # the url should be non-unicode object otherwise the library makes the assumption that data
    # is also unicode, which is not.
    
    if type(server_url) is types.UnicodeType:
      request_url = server_url.encode('ascii')
    else:
      request_url = server_url
    
    request = urllib2.Request(request_url, data=body, headers=headers)

    try:
      response = self.opener.open(request)
      return response
    except urllib2.HTTPError, e:
      print e
      print 'Code', e.code
      print 'Reason', e.reason
      raise


if __name__ == '__main__':
  current_directory = os.path.dirname(__file__)
  project_root_directory = os.path.abspath(os.path.join(current_directory, os.pardir, os.pardir, os.pardir))
  data_directory = os.path.join(project_root_directory, "data", "1.jpg")
  
  fields = {}
  fields['date'] = datetime.datetime.now()
  fields['content'] = "random text"
  
  files = []
  files.append(('image_name.jpg', open(data_directory)))
  
  my_post_object = PostMultipartWithSession('http://localhost:8000') 
  my_post_object.login('/login', # login page 
                       'User2',  # username
                       'user2')  # password
  my_post_object.post_multipart('/add/', 
                                fields, 
                                files, 
                                True)
