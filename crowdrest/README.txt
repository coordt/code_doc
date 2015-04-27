This package was taken from:
https://github.com/pfalcon/django-crowd-rest-backend


This section describes the changes we made to the application:

We removed the "models.py" file and all references to it.
It added a "is_crowd_user" flag to the Django User Model, which implied an extra migration of Django's Models (in django.contrib.auth.User).
Since however this flag was not used anywhere, we decided to get rid of it in order to not be forced to have this extra migration


The application has a dependency on "urllib2", but it is part of python2.7, so it should not be a problem.
