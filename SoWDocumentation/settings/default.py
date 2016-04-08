"""
Django settings for SoWDocumentation project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

SITE_NAME = 'CODEDOC'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') + '/'
MEDIA_URL = '/media/'

# path used to upload temporary files
USER_UPLOAD_TEMPORARY_STORAGE = os.path.join(BASE_DIR, 'temporary')
FILE_LOGGING_LOCATION = os.path.join(USER_UPLOAD_TEMPORARY_STORAGE, "%s.log" % SITE_NAME)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_nx*8lt4e9rkkqkbc+@l+w3k1rpe@)mpidyy%=8nyo%w259l-_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

# to be edited when in production mode
ALLOWED_HOSTS = ['code.is.localnet', '127.0.0.1', 'localhost']

ADMINS = (('Raffi Enficiaud', 'raffi.enficiaud@tuebingen.mpg.de'),)

# the ppl receiving notifications for broken links if BrokenLinkEmailsMiddleware is active
MANAGERS = (('Raffi Enficiaud', 'raffi.enficiaud@tuebingen.mpg.de'),)


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
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

if 0:
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        # - if False, needs an absolute location for the template folder and does not look
        #   for other applications' folder content
        # - if True, relies on the order given by INSTALLED_APPS
        # see https://docs.djangoproject.com/es/1.9/ref/templates/api/#template-loaders
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'code_doc.permissions.backend.CodedocPermissionBackend',
)

ROOT_URLCONF = 'SoWDocumentation.urls'
WSGI_APPLICATION = 'SoWDocumentation.wsgi.application'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '*** [%(levelname)s] %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '[%(levelname)s] %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': FILE_LOGGING_LOCATION,
        },

        'console': {
            'level': 'INFO',
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
        },
        'code_doc.migrations': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

ROOT_URLCONF = 'SoWDocumentation.urls'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# AUTH_USER_MODEL = 'code_doc.Author'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True
