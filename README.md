# Code documentation server #

This project provides a simple web application to store documentation and artifacts. It manages permissions on each of the resources served. 

## Deploying the application into production ## 
The tested configuration is NGinx + uWSGI under Ubuntu 14.04

```
#!bash
> sudo apt-get install nginx uwsgi python-pip python-virtualenv
> sudo mkdir /www
> sudo mkdir /www/webapp
> cd /www/webapp
> git clone this_repository
```

Let's call ``$my_application_folder`` the location where the sources were cloned (here we would have ``$my_application_folder=/www/webapp/this_repository``).
```
#!bash
> cd $my_application_folder
> 
```

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