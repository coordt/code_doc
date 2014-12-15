# -*- coding: utf-8 -*-


__doc__ = """
The intent of this module is to send "artifacts" to a code_doc server, without using any of the Django related stuff
and possibly no extra packages. This is done by

* loging into the code_doc server using credentials and storing the cookies associated to this session
* filling a form that contains the details of the artifact to send
* sending the content

The main class is :class:`PostMultipartWithSession` and the entry point when used as a script is the :func:`main`. 
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
import logging



logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging




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
    
    # the referer is needed by NGinx in order to not be considered as a robot/spambot/malicious software
    request.add_header('Referer', self.host + login_page)

    try:
      response = self.opener.open(request)
    except urllib2.HTTPError, e:
      logger.error("""[login] an error occurred during login:\n
                      \tError code: %d\n
                      \tError reason: %s\n
                      \tError details %s""", e.code, e.reason, e.fp.read())
      
      raise
    
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
        logger.info('[csrf] cookie not found from the content')
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
        string_file = fd.read()
        
        buf.write('\r\n' + string_file + '\r\n')      
        
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
    # again (as for login) the referer is needed by NGinx
    request.add_header('Referer', self.host + page_url)

    try:
      response = self.opener.open(request)
      return response
    except urllib2.HTTPError, e:
      logger.error("""[post] an error occurred during posting of the form to %s:\n
                      \tError code: %d\n
                      \tError reason: %s\n
                      \tError details %s""",
                      self.host + page_url, 
                      e.code, e.reason, e.fp.read())      
      raise



def main():
  import argparse
  import hashlib
  import json
  import datetime
  
  
  description = """code_doc upload script:
  
  This utility sends a file to a code_doc instance. It logs onto a code_doc instance with the 
  provided credentials, gets the id of the project and version that are given from the command line
  and sends the file to this specific version. 
  
  """
  
  epilog = ""
  
  parser = argparse.ArgumentParser(prog = 'code_doc-archival', 
                                   description = description,
                                   epilog = epilog)

  group = parser.add_argument_group('artifact')
  

  group.add_argument('-f', '--file', 
                      dest='inputfile', 
                      action='store',
                      required=True,
                      nargs=1,
                      type=argparse.FileType('rb'),
                      help="""The file that should be sent to the server.""")

  group.add_argument('--project',
                      dest = 'project',
                      required=True,
                      help = """The name of the project concerned by this upload""")

  group.add_argument('--artifact_version',
                      dest = 'version',
                      required=True,
                      help = """The name of the version concerned by this upload""")

  group.add_argument('--is_doc',
                      dest = 'is_doc',
                      action="store_true",
                      help = """Indicates that the file is an archive containing a documentation that should be deflated on the
                      server side. Additionally, the `doc_entry` parameter should be set.""")

  group.add_argument('--doc_entry',
                      dest = 'doc_entry',
                      default = None,
                      help = """Indicates the file that is used as the documentation main entry point.""")

  group.add_argument('--artifact_description',
                      dest = 'description',
                      action='store',
                      help = """Describes the artifact.""")


  group = parser.add_argument_group('server')

  group.add_argument('-s', '--code_doc_url', 
                      dest='url', 
                      metavar='URL',
                      action='store',
                      default='http://localhost:8000',
                      help="""CodeDoc (Django) server to which the results will be send. The URL should contain 
                              the http scheme, the dns name and the port (default: "http://localhost:8000")""")

  group.add_argument('--username',
                      dest = 'username',
                      required=True,
                      help = """The username used for updating the results (the user should exist on the Django instance is should be
                             allowed to add results)""")

  group.add_argument('--password',
                      dest = 'password',
                      required=True,
                      help = """The password of the provided user on the Django instance""")



  args = parser.parse_args()

  args.inputfile = args.inputfile[0]

  if args.inputfile.closed:
    logger.error("[configuration] the provided file cannot be accessed")
    raise Exception("[configuration] cannot open the artifact file")

  if args.is_doc and args.doc_entry is None:
    logger.error("[configuration] the entry point should be provided for documentation artifacts")
    raise Exception("[configuration] cannot open the artifact file")
    

  instance = PostMultipartWithSession(args.url)
  
  
  # logging with the provided credentials
  logger.debug("[log in] Logging to the server")
  instance.login(login_page = "/accounts/login/", 
                 username = args.username,
                 password = args.password)


  # getting the location (id of the project and version) to which the upload should be done
  logger.debug("[meta] Retrieving the project and versions IDs")  
  post_url = '/api/%s/%s/' % (args.project, args.version)
  
  try:
    response = instance.get(post_url)
  except Exception, e:
    logger.error("[login] an exception was raised while trying to login to the server %r", e)
    raise

  try:    
    res = response.read()
    dic_ids = json.loads(res)
    project_id = int(dic_ids['project_id'])
    version_id = int(dic_ids['version_id'])
  except Exception, e:
    logger.error("""[meta] an error occurred during the retrieval of the projects informations from %s:\n
                      \tError details %s""",
                      self.host + post_url, 
                      e)     
  

  ##### sending the artifact
  # preparing the form
  fields = {}
  fields['description'] = args.description if not args.description is None else 'uploaded by a robot'
  fields['is_documentation'] = "True" if args.is_doc else "False"
  fields['documentation_entry_file'] = args.doc_entry if not args.doc_entry is None else ''
  fields['upload_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  
  files = []
  files.append(('artifactfile', args.inputfile))
      
  
  post_url = '/artifacts/%d/%d/add' % (project_id, version_id)

  
  # sending    
  logger.debug("[transfer] Sending artifact")
  response = instance.post_multipart( 
          post_url, 
          fields, 
          files,
          avoid_redirections = False)

  if(response.code != 200):
    logger.error("[transfer] an error was returned by the server during the transfer of the file, return code is %d", ret.code)
    raise Exception("[transfer] an error was returned by the server during the transfer of the file")

  
  #### checking artifact properly stored
  logger.debug("[integrity] Checking artifact") 
  
  post_url = '/artifacts/api/%d/%d' % (project_id, version_id)
  response = instance.get(post_url) 
  if(response.code != 200):
    logger.error("[transfer] an error was returned by the server while querying for artifacts, return code is %d", ret.code)
    raise Exception("[transfer] an error was returned by the server during the transfer of the file")
  
  
  args.inputfile.seek(0)
  hash_file = hashlib.md5(args.inputfile.read()).hexdigest().upper()
  
  dic_ids = json.loads(response.read())
  artifacts = dic_ids['artifacts']
  for art_id, art in artifacts.items():
    if(art['md5'].upper() == hash_file):
      logger.info("[integrity] artifact successfully stored on the server")
      break
  else:
    logger.error("[integrity] the artifact cannot be found on the server")
    raise Exception("[integrity] the artifact cannot be found on the server")




if __name__ == '__main__':
  import sys
  
  try:
    main()
    sys.exit(0)
  except Exception, e:
    print e
    logger.error("[ERROR] The artifact was not pushed to the server: %s", e)
    sys.exit(2)
  

