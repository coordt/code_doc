from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout

from rest_framework import generics


from code_doc import views



urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  
  url(r'^accounts/login/$',  login, name='login'),
  url(r'^accounts/logout/$', logout, name='logout'),  
  
  # projects
  # lists all projects
  url(r'^project/$', views.ProjectListView.as_view(), name='project_list'), 
  # details of a particular project
  url(r'^project/(?P<project_id>\d+)/$', views.ProjectView.as_view(), name='project'),
  
  # revisions
  # lists all revisions of a project
  url(r'^revisions/(?P<project_id>\d+)/$', views.ProjectView.as_view(), name='project_revisions_all'),
  # details about a particular revision of a project
  url(r'^revisions/(?P<project_id>\d+)/(?P<version_id>\d+)/$', views.ProjectVersionDetailsView.as_view(), name='project_revision'),
  # form for adding a revision to a project
  url(r'^revisions/(?P<project_id>\d+)/add/$', views.ProjectVersionAddView.as_view(), name='project_revision_add'),
  # @todo update and delete of a revision
  
  # project version artifacts
  url(r'^project/(?P<project_id>\d+)/(?P<version_number>[\d\w\s]+)/$', views.ProjectVersionArtifactView.as_view(), name='project_artifacts'),
  url(r'^project/(?P<project_id>\d+)/(?P<version_id>\w+)/add$', views.ProjectVersionArtifactAddView.as_view(), name='project_artifacts_add'),
  
  # shortcuts
  url(r'^s/(?P<project_name>[\d\w\s]+)/(?P<version_number>[\d\w\s]+)/$', views.ProjectVersionDetailsShortcutView.as_view(), name='project_shortcuts'),
  
  # topics
  url(r'^topics/$', views.TopicListView.as_view(), name='topics_list'),  # lists all topics
  url(r'^topics/(?P<topic_id>\d+)/$', views.TopicView.as_view(), name='topic'), # gives details on a specific topic
  
  # maintainers
  url(r'^maintainer/$', views.MaintainerProfileView.as_view(), name='maintainer'),
  
  # Authors
  url(r'^authors/$', views.AuthorListView.as_view(), name='authors_list'), # lists all authors
  url(r'^authors/(?P<author_id>\d+)/$', views.detail_author, name='author'), # details about an author
  
  
  url(r'^api/artifact/(?P<project_id>\d+)/(?P<project_revision_id>\d+)/(?P<filename>.+)$', views.FileUploadView.as_view(), name='fileupload'),
  url(r'^api/artifact/(?P<project_revision_id>\d+)/$', views.FileUploadView.as_view(), name='fileupload_post'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

) 
