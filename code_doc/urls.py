from django.conf.urls import patterns, url

from rest_framework import generics

from code_doc import views



urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^project/(?P<project_id>\d+)/$', views.detail_project, name='project'),
  url(r'^author/(?P<author_id>\d+)/$', views.detail_author, name='author'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

)
