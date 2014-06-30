from django.conf.urls import patterns, url

from rest_framework import generics

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^project/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

)
