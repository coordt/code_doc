from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout

from code_doc import views



urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^about$', views.about, name='about'),
  url(r'^script$', views.script, name='script'),

  url(r'^accounts/login/$',  login, name='login'),
  url(r'^accounts/logout/$', logout, name='logout'),

  # projects
  # lists all projects
  url(r'^project/$', views.ProjectListView.as_view(), name='project_list'),
  # details of a particular project
  url(r'^project/(?P<project_id>\d+)/$', views.ProjectView.as_view(), name='project'),

  # revisions
  # lists all revisions of a project
  url(r'^revisions/(?P<project_id>\d+)/$',
      views.ProjectView.as_view(),
      name='project_revisions_all'),
  # details about a particular revision of a project
  url(r'^revisions/(?P<project_id>\d+)/(?P<series_id>\d+)/$',
      views.ProjectSeriesDetailsView.as_view(),
      name='project_revision'),
  # edition of a particular project series
  url(r'^project/(?P<project_id>\d+)/(?P<series_id>\w+)/edit',
      views.ProjectSeriesUpdateView.as_view(),
      name='project_revision_edit'),
  # adding a revision to the project
  url(r'^revisions/(?P<project_id>\d+)/add/$',
      views.ProjectSeriesAddView.as_view(),
      name='project_revision_add'),

  # @todo update and delete of a series

  # project series artifacts
  # url(r'^project/(?P<project_id>\d+)/(?P<series_number>[\d\w\s]+)/$',
  #    views.ProjectSeriesArtifactView.as_view(),
  #    name='project_artifacts'),
  url(r'^artifacts/(?P<project_id>\d+)/(?P<series_id>\w+)/add$',
      views.ProjectSeriesArtifactAddView.as_view(),
      name='project_artifacts_add'),
  url(r'^artifacts/(?P<project_id>\d+)/(?P<series_id>\w+)/remove/(?P<artifact_id>\w+)',
      views.ProjectSeriesArtifactRemoveView.as_view(),
      name='project_artifacts_remove'),
  url(r'^artifacts/api/(?P<project_id>\d+)/(?P<series_id>\w+)/$', views.APIGetArtifacts.as_view(), name='api_get_artifacts'),

  # shortcuts
  url(r'^s/(?P<project_name>[\d\w\s]+)/(?P<series_number>[\d\w\s]+)/$', views.ProjectSeriesDetailsShortcutView.as_view(), name='project_shortcuts'),
  url(r'^api/(?P<project_name>[\d\w\s-]+)/(?P<series_number>[\d\w\s-]+)/$', views.GetProjectRevisionIds.as_view(), name='api_get_ids'),

  # topics
  url(r'^topics/$', views.TopicListView.as_view(), name='topics_list'),  # lists all topics
  url(r'^topics/(?P<topic_id>\d+)/$', views.TopicView.as_view(), name='topic'), # gives details on a specific topic

  # maintainers
  url(r'^maintainer/(?P<maintainer_id>\d+)/$', views.MaintainerProfileView.as_view(), name='maintainer'),

  # Authors
  url(r'^authors/$', views.AuthorListView.as_view(), name='authors_list'), # lists all authors
  url(r'^authors/(?P<author_id>\d+)/$', views.detail_author, name='author'), # details about an author


  #url(r'^api/artifact/(?P<project_id>\d+)/(?P<project_revision_id>\d+)/(?P<filename>.+)$', views.FileUploadView.as_view(), name='fileupload'),
  #url(r'^api/artifact/(?P<project_revision_id>\d+)/$', views.FileUploadView.as_view(), name='fileupload_post'),
  #url(r'^details/(?P<project_id>\d+)/$', views.detail_project, name='detail_project'),

)
