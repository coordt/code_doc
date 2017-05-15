# Documentation and artifacts store django application #

This project provides a simple web application written in Django/python that aims at sharing artifacts and documentation in a public or private way.
It is especially suited to be the companion of a build server that generates the documentation and eg. installers, and needs to make those visible
to a group of developers.

[TOC]

An example of workflow that we actually use would be:
![workflow][workflow]

The main features are:

* handling projects and associated metadata, such as descriptions, authors, maintainers, repositories, copyright holders, license,
  home page, etc
* organization of projects by series, the meaning of the series is up to the project. It can be a specific release channel (release, beta or even
  continuous build), a set of packages, etc
* serving HTML documentation: documentation files (zip, tar...) are deflated on the server side and served directly from the web application. Each
  revision is kept (if not explicitly removed) and you can track the evolution of the documentation, have consistent release together with documentation, etc
* a small scripting API that let update/push artifacts from remote, which is especially convenient for Continuous Integration servers such as Atlassian Bamboo or Jenkins
* handling a limit on the number of revisions per series, which works well for continuous builds
* permission management: each of the resources that are served can have a set of permissions applied to it, which
  can be used to restrict the visibility of internal or intermediate work/project
* not so ugly interface using Bootstrap

[workflow]: ./doc/images/code_doc_workflow.png

## Screenshots

![main page](./doc/images/main_window.jpg =300x)

## License and Copyright #
The project is developed at the [Max Planck Institute for Intelligent Systems](https://is.tuebingen.mpg.de/), Tübingen, Germany, within the [Software Workshop](https://is.tuebingen.mpg.de/en/software-workshop).
It is released under the BSD-3 clauses license.

## Contribution #
This project is still active and any contribution or feature request is welcome. Please use the Bitbucket issue tracker for that.

The main developer/maintainer is me (Raffi Enficiaud), and a big contributor has been Stephan Wenninger.

## Running the application #
This project is based on the Django framework and has very few dependencies, which makes it easy to run:

```
#!bash

# create a dedicated virtual environment
> virtualenv my_env
> . my_env/bin/activate

# install the dependencies
> pip install django
> pip install Pillow
> pip install markdown
> pip install pygments
```

and now you can just test the application as follow (we deflate Bootstrap which is part of the source code):

```
#!bash
> cd code_doc
> cd src/code_doc/static
> unzip bootstrap-3.2.0-dist.zip
> cd -
> python manage.py migrate
> python manage.py runserver
```

If there is no error message, you can then open a browser and visit http://localhost:8000 .

We do not explain how to deploy this application in production environment.

### Adding a superuser
In order to perform some operations such as adding a project, you need to create a *super user* first.

```
#!bash
> cd code_doc
> python manage.py createsuperuser
```

### Adding a project

This can be currently done only from the admin interface of Django:

* open a browser and visit http://localhost:8000/admin
* then add a project there
    * specify a copyright holder
    * specify a license
    * describe the project
    * indicate a maintainer

And that is it.

## Additional stuff

We use a crowd authentication back-end from: https://github.com/pfalcon/django-crowd-rest-backend
that we modified a bit (removed the "models.py" file and all references to it).
The crowd-rest-back-end application has a dependency on "urllib2", but it is part of python2.7, so it should not be a problem.
