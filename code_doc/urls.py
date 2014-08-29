from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout

from rest_framework import generics


from code_doc import views



urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  
  url(r'^accounts/login/$',  login, name='login'),
  url(r'^accounts/logout/$', logout, name='logout'),  
  
  # projects
  url(r'^project/(?P<project_id>\d+)/$', views.ProjectView.as_view(), name='project'),
  
  # projects versions
  url(r'^project/(?P<project_id>\d+)/versions/$', views.ProjectVersionListView.as_view(), name='project_version_all'),
  url(r'^project/(?P<project_id>\d+)/versions/(?P<version_id>\d+)/$', views.ProjectVersionView.as_view(), name='project_version'),
  url(r'^project/(?P<project_id>\d+)/versions/add/$', views.ProjectVersionAddView.as_view(), name='project_version_add'),
  #url(r'^project/(?P<project_id>\d+)/versions/add/$', views.ProjectVersionAddView.as_view(), name='project_version_add'),
  
  # project version artifacts
  url(r'^project/(?P<project_id>\d+)/(?P<version_number>\w+)/$', views.ProjectVersionArtifactView.as_view(), name='project_artifacts'),
  
  # topics
  url(r'^topic/(?P<topic_id>\d+)/$', views.TopicView.as_view(), name='topic'),
  
  # maintainers
  url(r'^maintainer/$', views.MaintainerProfileView.as_view(), name='maintainer'),
  
  # Authors
  url(r'^authors/$', views.AuthorListView.as_view(), name='authors_list'),
  url(r'^authors/(?P<author_id>\d+)/$', views.detail_author, name='author'),
  
  
  url(r'^api/artifact/(?P<project_id>\d+)/(?P<project_version_id>\d+)/(?P<filename>.+)$', views.FileUploadView.as_view(), name='fileupload'),
  url(r'^api/artifact/(?P<project_version_id>\d+)/$', views.FileUploadView.as_view(), name='fileupload_post'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

) 
