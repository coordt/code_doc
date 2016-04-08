
import os
from .default import *


# cannot be this directory since this is a symbolic link to the previous
# instance
# CODEDOC_ROOT_LOCATION = '/www/code_doc/current/'
CODEDOC_ROOT_LOCATION = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(CODEDOC_ROOT_LOCATION, 'static') + '/'
MEDIA_ROOT = os.path.join(CODEDOC_ROOT_LOCATION, 'media') + '/'

# path used to upload temporary files, maybe a proper /tmp dir for production?
USER_UPLOAD_TEMPORARY_STORAGE = os.path.join(CODEDOC_ROOT_LOCATION, 'temporary_upload')
FILE_LOGGING_LOCATION = os.path.join(CODEDOC_ROOT_LOCATION, 'logs', "%s.log" % SITE_NAME)

if(not os.path.exists(USER_UPLOAD_TEMPORARY_STORAGE)):
    os.makedirs(USER_UPLOAD_TEMPORARY_STORAGE)

if(not os.path.exists(os.path.dirname(FILE_LOGGING_LOCATION))):
    os.makedirs(os.path.dirname(FILE_LOGGING_LOCATION))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_nx*8lt4e9rkkqkbc+@l+w3k1rpe@)mpidyy%=8nyo%w259l-_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['code.is.localnet', '127.0.0.1', 'localhost']
ADMINS = (('Raffi Enficiaud', 'raffi.enficiaud@tuebingen.mpg.de'),)

# the ppl receiving notifications for broken links if BrokenLinkEmailsMiddleware is active
MANAGERS = (('Raffi Enficiaud', 'raffi.enficiaud@tuebingen.mpg.de'),)


# ###### EMAIL
#
#

# production backend

if 0:
    # no email support
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

    # The email address that error messages come from, such as those sent to ADMINS and MANAGERS.
    SERVER_EMAIL = 'is-noreply@tuebingen.mpg.de'

    # Default email address to use for various automated correspondence from
    # the site managers.
    DEFAULT_FROM_EMAIL = 'is-noreply@tuebingen.mpg.de'

    # Subject-line prefix for email messages send with django.core.mail.mail_admins
    # or ...mail_managers.  Make sure to include the trailing space.
    # NB.: not for end users
    EMAIL_SUBJECT_PREFIX = '[CodeDoc] '

    # Host for sending email.
    EMAIL_HOST = 'mailhost.tuebingen.mpg.de'

    # Port for sending email.
    EMAIL_PORT = 25

    # Optional SMTP authentication information for EMAIL_HOST.
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS = True


# fix logging thinggy (need to rewrite)
LOGGING['handlers']['file']['filename'] = FILE_LOGGING_LOCATION


print "MEDIA_ROOT set to production", MEDIA_ROOT
print "STATIC_ROOT set to production", STATIC_ROOT


# CROWD REST Settings
INSTALLED_APPS += ('crowdrest',)
AUTHENTICATION_BACKENDS += ('crowdrest.backend.CrowdRestBackend',)

# Uncomment for setting up the Crowd - authentification application
AUTH_CROWD_ALWAYS_UPDATE_USER = True
AUTH_CROWD_ALWAYS_UPDATE_GROUPS = True
AUTH_CROWD_CREATE_GROUPS = True

AUTH_CROWD_STAFF_GROUP = 'jira-developers'
AUTH_CROWD_SUPERUSER_GROUP = 'jira-administrators'

# @todo: Configure the password for accessing CROWD
AUTH_CROWD_APPLICATION_USER = 'code-doc-crowd.mpi.is'
AUTH_CROWD_APPLICATION_PASSWORD = 'code-doc.deployed'

AUTH_CROWD_SERVER_REST_URI = 'http://localhost:8095/crowd/rest/usermanagement/latest'
AUTH_CROWD_SERVER_TRUSTED_ROOT_CERTS_FILE = None
