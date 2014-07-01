from django.conf.urls import patterns, url

from django.contrib.auth.views import login, logout

from rest_framework import generics

from code_doc import views



urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^accounts/login/$',  login, name='login'),
  url(r'^accounts/logout/$', logout),  
  url(r'^project/(?P<project_id>\d+)/$', views.detail_project, name='project'),
  url(r'^project2/(?P<project_id>\d+)/$', views.ProjectView.as_view(), name='project2'),
  url(r'^author/(?P<author_id>\d+)/$', views.detail_author, name='author'),
  url(r'^api/artifact/(?P<project_version_id>\d+)/(?P<filename>.+)$', views.FileUploadView.as_view(), name='fileupload'),
  url(r'^api/artifact/(?P<project_version_id>\d+)/$', views.FileUploadView.as_view(), name='fileupload_post'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

) 
