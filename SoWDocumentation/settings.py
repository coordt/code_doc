"""
Django settings for SoWDocumentation project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') + '/'
MEDIA_URL  = '/media/'

# path used to upload temporary files
USER_UPLOAD_TEMPORARY_STORAGE = os.path.join(BASE_DIR, 'temporary', 'django_application_code_doc')

if(not os.path.exists(USER_UPLOAD_TEMPORARY_STORAGE)):
  os.makedirs(USER_UPLOAD_TEMPORARY_STORAGE)


# location where the file logger logs
FILE_LOGGING_LOCATION = os.path.join(USER_UPLOAD_TEMPORARY_STORAGE, "code_doc.log")



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_nx*8lt4e9rkkqkbc+@l+w3k1rpe@)mpidyy%=8nyo%w259l-_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

# to be edited when in production mode
ALLOWED_HOSTS = ['code.is.localnet', '127.0.0.1', 'localhost']

ADMINS = (('Raffi Enficiaud', 'raffi.enficiaud@tuebingen.mpg.de'), )


LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# Email address that error messages come from.
SERVER_EMAIL = 'root@localhost'

# Default email address to use for various automated correspondence from
# the site managers.
DEFAULT_FROM_EMAIL = 'webmaster@code.is.localnet'

# Subject-line prefix for email messages send with django.core.mail.mail_admins
# or ...mail_managers.  Make sure to include the trailing space.
EMAIL_SUBJECT_PREFIX = '[CodeDoc] '


# Host for sending email.
EMAIL_HOST = 'localhost'

# Port for sending email.
EMAIL_PORT = 25

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'code_doc',

    'crowdrest',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',  # this one is missing by default
    'django.contrib.messages.context_processors.messages',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'code_doc.permissions.backend.CodedocPermissionBackend',

    # 'crowdrest.backend.CrowdRestBackend',
    )


# Crowdrest Settings

# Uncomment for setting up the Crowd - authentification application

AUTH_CROWD_ALWAYS_UPDATE_USER = True
AUTH_CROWD_ALWAYS_UPDATE_GROUPS = True
AUTH_CROWD_CREATE_GROUPS = True

AUTH_CROWD_STAFF_GROUP = 'jira-developers'
AUTH_CROWD_SUPERUSER_GROUP = 'jira-administrators'

# @todo: Configure the password for accessing CROWD
AUTH_CROWD_APPLICATION_USER = 'django-code-doc-test'
AUTH_CROWD_APPLICATION_PASSWORD = 'testcodedoc'

AUTH_CROWD_SERVER_REST_URI = 'http://seine.is.localnet:8095/crowd/rest/usermanagement/latest'
AUTH_CROWD_SERVER_TRUSTED_ROOT_CERTS_FILE = None


LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
      'verbose': {
          'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
      },
      'simple': {
          'format': '%(levelname)s %(message)s'
      },
  },
  'handlers': {
      'file': {
          'level': 'DEBUG',
          'class': 'logging.FileHandler',
          'filename': FILE_LOGGING_LOCATION,
      },

      'console': {
         'level': 'DEBUG',
         'class': 'logging.StreamHandler',
         'formatter': 'verbose'
      },
  },
  'loggers': {
      'code_doc.views': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      },
      'code_doc.admin': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      },
      'code_doc.templatetags.button_add_with_permission': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      },
      'code_doc.templatetags.markdown_filter': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      },
      'code_doc.models': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      },
      'code_doc.permissions': {
          'handlers': ['console'],
          'level': 'WARNING',
          'propagate': True,
      },
      'code_doc.signals': {
          'handlers': ['console'],
          'level': 'DEBUG',
          'propagate': True,
      }
  },
}

ROOT_URLCONF = 'SoWDocumentation.urls'

WSGI_APPLICATION = 'SoWDocumentation.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

#AUTH_USER_MODEL = 'code_doc.Author'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True




