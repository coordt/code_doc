# Code documentation server #

This project provides a simple web application to store documentation and artifacts. It manages permissions on each of the resources served. 

## Installation #
In the sequel, everything will be installed and ran in a virtual environment. 

```
#!bash
> virtualenv my_env
> . my_env/bin/activate

> pip install django
> pip install Pillows
> pip install markdown
> pip install pygments
```

## Deploying the application into production #

The tested configuration is NGinx + uWSGI under Ubuntu 14.04. We need to install 

* the webserver, 
* the necessary tools for python in order to manage virtual environments
* the uWSGI binding and its python extension
* the image I/O libraries needed by Pillow for Django

```
#!bash
> sudo apt-get install nginx 
> sudo apt-get install python-pip python-virtualenv
> sudo apt-get install uwsgi uwsgi-plugin-python
> sudo apt-get install libtiff5-dev libjpeg-dev libpng-dev unzip
> sudo mkdir -p /www/webapp/my_application_name
> cd /www/webapp/my_application_name
> git clone "this_repository" src
> cd src/code_doc/static
> unzip bootstrap-3.2.0-dist.zip
```


Let's call ``$my_application_folder`` the root location where the sources were cloned (here we would have ``$my_application_folder=/www/webapp/my_application_name``).

### Preparation of the virtual environment ###

We want everything running in a virtual environment. This way there is no troubleshooting among several instances of web application hosted by the same server. 
```
#!bash
> cd $my_application_folder
> virtualenv venv
> . venv/bin/activate
> pip install django>=1.7
> pip install Pillow
> pip install markdown
```


### Preparation of the static and media folders ###

In production, the static and media files are served by NGinx and not by Django

```
#!bash
> cd $my_application_folder
> mkdir static
> mkdir media
> sudo chown me:www-data static
> sudo chown me:www-data media
```

### Fixing some permissions ###

The user that will be running django is likely to be ``www-data`` which also has its own group. The database should be writable for this user. This is usually not a problem if you run Django with a real database backend, but if (eg. for small applications) you decide to stay with sqlite, the the db that is stored into a file should have the proper permissions. 

```
#!bash
> cd $my_application_folder/src
> .. venv/bin/activate
> python manage.py syncdb
> sudo chown me:www-data db.sqlite
> sudo chown me:www-data media
```

Beside that, the process running django should be able to read and write from the static and media folders:

```
#!bash
> cd $my_application_folder
> sudo chown me:www-data static
> sudo chown me:www-data media
```

## NGinx configuration ##

## uWSGI configuration ##

### What is this repository for? ###

* Quick summary
* Version
* [Learn Markdown](https://bitbucket.org/tutorials/markdowndemo)

### How do I get set up? ###

* Summary of set up
* Configuration
* Dependencies
* Database configuration
* How to run tests
* Deployment instructions