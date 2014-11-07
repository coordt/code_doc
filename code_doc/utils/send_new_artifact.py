# -*- coding: utf-8 -*-

# The intent of this module is to send a file to the code_doc server remotely, without using any of the Django related stuff
# and possibly nothing related to extra packages



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

  class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    
    
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
    self.cookies = cookielib.CookieJar()
    self.redirection_intercepter = PostMultipartWithSession.MyHTTPRedirectHandler("redir")

    self.opener = urllib2.build_opener(self.redirection_intercepter, urllib2.HTTPCookieProcessor(self.cookies))
    #self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookies))
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
      """
      fields is a sequence of (name, value) elements for regular form fields.
      files is a sequence of (name, filename, value) elements for data to be uploaded as files
      Return (content_type, body) ready for httplib.HTTP instance
      """
      BOUNDARY = mimetools.choose_boundary()
      
      buf = StringIO.StringIO()
      for (key, value) in fields.items():
        buf.write('--%s\r\n' % BOUNDARY)
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
        buf.write('--%s\r\n' % BOUNDARY)
        buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
        buf.write('Content-Type: %s\r\n' % contenttype)
        fd.seek(0)
        buf.write('\r\n' + fd.read() + '\r\n')      
        
      buf.write('--' + BOUNDARY + '--\r\n\r\n')
      
      body = buf.getvalue()
      content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
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
    
  def post_multipart(self, page, form_fields, form_files, avoid_redirections = True):
    """ Post form_fields and form_files to an http://host/page as multipart/form-data.
      
      :param form_fields: is a sequence of (name, value) elements for regular form form_fields.
      :param form_files: is a sequence of (name, filename, value) elements for data to be uploaded as form_files
      :returns: the server's response page.
    """
    server_url = "%s%s" % (self.host, page)
    
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
      return e
    


def get_csrf_token(content, cookies):
  """Returns the csrf token put (hidden) into a form"""
  token = None
  pos = content.find('csrfmiddlewaretoken')
  if pos > -1:
    for c in cookies: 
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


def post_multipart(host, page, form_fields, form_files, username = None, password = None):
    """
    Post form_fields and form_files to an http host as multipart/form-data.
    form_fields is a sequence of (name, value) elements for regular form form_fields.
    form_files is a sequence of (name, filename, value) elements for data to be uploaded as form_files
    Return the server's response page.
    """
    
    
    server_url = "%s%s" % (host, page)


    # cookie jar
    cookies = cookielib.CookieJar()
    
    
    # opener
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener(opener)


    # to check redirection
    #import httplib
    #conn = httplib.HTTPConnection(host.replace('http://', '') )
    #conn.request("GET", page)
    #r1 = conn.getresponse()
    #print 'Status', r1.status
    #print 'Reason', r1.reason
    #print 'Redirection location', r1.getheader('Location')
    
    
    
    # get for the cookie and opening a session
    request = urllib2.Request(server_url)
    response= opener.open(request)
    content = response.read()
        
    # csrf token needed for the login forms
    token = get_csrf_token(content, cookies)
    
    #print 'token', token
    
    login_data = dict(username=username, password=password, csrfmiddlewaretoken=token)
    request = urllib2.Request(response.geturl(), data=urllib.urlencode(login_data))
    response = opener.open(request)
    content = response.read()
    
    
    # new token for this form, after login redirection
    token = get_csrf_token(content, cookies)

    fields_with_token = dict(form_fields)
    if not token is None:
      fields_with_token['csrfmiddlewaretoken'] = token    

    content_type, body = encode_multipart_formdata(fields_with_token, form_files)
    headers = {'Content-Type': content_type, 'Content-Length': str(len(body))}
    request = urllib2.Request(response.geturl(), data=body, headers=headers)
    
    try:
      response = opener.open(request)      
      #output = response.read()
      return response
    except urllib2.HTTPError, e:
      print e
      print 'Code', e.code
      print 'Reason', e.reason
      return e
    
    
def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = mimetools.choose_boundary()
    
    buf = StringIO.StringIO()
    for (key, value) in fields.items():
      buf.write('--%s\r\n' % BOUNDARY)
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

      buf.write('--%s\r\n' % BOUNDARY)
      buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
      buf.write('Content-Type: %s\r\n' % contenttype)
      fd.seek(0)
      buf.write('\r\n' + fd.read() + '\r\n')      
      
    buf.write('--' + BOUNDARY + '--\r\n\r\n')
    
    body = buf.getvalue()
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


if __name__ == '__main__':
  fields = {}
  fields['description'] = "revision from client based application"
  
  files = []
  files.append(('artifactfile', r'D:\Personal\Dropbox\Maitre Mohr.docx'))
  
  ret = post_multipart('http://localhost:8000', 
                       page = '/code_doc/project/1/1/add', 
                       form_fields = fields, 
                       form_files = files,
                       username = 'User2',
                       password = 'user2')
  