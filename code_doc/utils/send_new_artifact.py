# -*- coding: utf-8 -*-

# The intent of this module is to send a file to the code_doc server remotely, without using any of the Django related stuff
# and possibly nothing related to extra packages



import httplib, mimetypes, mimetools, urllib2, cookielib
import os
import stat
import re
import urllib
import contextlib
import StringIO

def get_csrf_token(content, cookies):
  token = None
  pos = content.find('csrfmiddlewaretoken')
  if pos > -1:
    for c in cookies: 
      print c.name
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


def post_multipart(host, selector, page, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    server_url = "http://%s:%s%s" % (host, selector, page)
    username = 'User2'
    password = 'user2'


    # cookie jar
    cookies = cookielib.CookieJar()
    opener_cookie = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    
    
    # password authentication
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, server_url, username, password)
    authentication_handler = urllib2.HTTPBasicAuthHandler(password_manager)
    opener_basic_auth = urllib2.build_opener(authentication_handler)
    
    
    # opener
    opener = opener_cookie
    urllib2.install_opener(opener)
    
    
    
    # get for the cookie and opening a session
    request = urllib2.Request(server_url)
    response= opener.open(request)
    content = response.read()
    
    print 'URL is', response.geturl()
    print 'Status is', response.getcode()
    #print 'Content is', content
    
    print 'Cookies', cookies
    
    
    # csrf token needed for the login forms
    token = get_csrf_token(content, cookies)
    
    print 'token', token
    
    login_data = dict(username=username, password=password, csrfmiddlewaretoken=token)
    request = urllib2.Request(response.geturl(), data=urllib.urlencode(login_data))
    response = opener.open(request)
    content = response.read()
    
    
    print 'URL is', response.geturl()
    print 'Status is', response.getcode()
    print 'Content (login) is', content
        
        
    
    # new token for this form, after login redirection
    token = get_csrf_token(content, cookies)
    print 'token 2', token

    fields_with_token = dict(fields)
    if not token is None:
      fields_with_token['csrfmiddlewaretoken'] = token    

    content_type, body = encode_multipart_formdata(fields_with_token, files)

    headers = {'Content-Type': content_type,
               'Content-Length': str(len(body))}
        
    
    print 'body, headers'
    print headers
    print body[:1000]
    
    request = urllib2.Request(response.geturl(), data=body, headers=headers)
        
    try:
      response = opener.open(request)
      
      output = response.read()
      print 'output'
      print output
      return output
    except urllib2.HTTPError, e:
      print e
      print 'Code', e.code
      print 'Reason', e.reason
      return 'Errors'
    
    
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
    for (key, filename_to_add) in files:
      fd = open(filename_to_add, 'rb')
      filename = os.path.basename(filename_to_add)
      contenttype = mimetypes.guess_type(filename_to_add)[0] or 'application/octet-stream'
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
  
  ret = post_multipart('localhost', 8000, '/code_doc/project/1/1/add', fields, files)
  print ret