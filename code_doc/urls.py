from django.conf.urls import url
from django.contrib.auth.views import login, logout

from .views import global_views, project_views, author_views, artifact_views, revision_views
from code_doc.views import series_views

urlpatterns = [
    url(r'^$', global_views.index, name='index'),
    url(r'^about$', global_views.about, name='about'),
    url(r'^script$', global_views.script, name='script'),

    url(r'^accounts/login/$', login, name='login'),
    url(r'^accounts/logout/$', logout, name='logout'),

    # topics
    # lists all topics
    url(r'^topics/$',
        global_views.TopicListView.as_view(),
        name='topics_list'),
    # gives details on a specific topic
    url(r'^topics/(?P<topic_id>\d+)/$',
        global_views.TopicView.as_view(),
        name='topic'),

    # projects
    # lists all projects
    url(r'^project/$', project_views.ProjectListView.as_view(), name='project_list'),
    # details of a particular project
    url(r'^project/(?P<project_id>\d+)/$', project_views.ProjectView.as_view(), name='project'),

    # Series
    # lists all series of a project
    url(r'^series/(?P<project_id>\d+)/$',
        project_views.ProjectView.as_view(),
        name='project_series_all'),
    # details about a particular series of a project
    url(r'^series/(?P<project_id>\d+)/(?P<series_id>\d+)/$',
        series_views.SeriesDetailsView.as_view(),
        name='project_series'),
    # edition of a particular project series
    url(r'^project/(?P<project_id>\d+)/(?P<series_id>\w+)/edit',
        series_views.SeriesUpdateView.as_view(),
        name='project_series_edit'),
    # adding a revision to the project
    url(r'^series/(?P<project_id>\d+)/add/$',
        series_views.SeriesAddView.as_view(),
        name='project_series_add'),

    # Revisions
    # See the contents of a revision
    url(r'^revision/(?P<project_id>\d+)/(?P<revision_id>\d+)/$',
        revision_views.RevisionDetailView.as_view(),
        name='project_revision'),

    # @todo update and delete of a series

    # project series artifacts
    # url(r'^project/(?P<project_id>\d+)/(?P<series_number>[\d\w\s]+)/$',
    #    series_views.ProjectSeriesArtifactView.as_view(),
    #    name='project_artifacts'),
    url(r'^artifacts/(?P<project_id>\d+)/(?P<series_id>\w+)/add$',
        artifact_views.ArtifactAddView.as_view(),
        name='project_artifacts_add'),
    url(r'^artifacts/(?P<project_id>\d+)/(?P<series_id>\w+)/remove/(?P<artifact_id>\w+)',
        artifact_views.ArtifactRemoveView.as_view(),
        name='project_artifacts_remove'),
    url(r'^artifacts/api/(?P<project_id>\d+)/(?P<series_id>\w+)/$',
        series_views.APIGetSeriesArtifacts.as_view(),
        name='api_get_artifacts'),

    # shortcuts
    url(r'^s/(?P<project_name>[\d\w\s]+)/(?P<series_number>[\d\w\s]+)/$',
        series_views.SeriesDetailsViewShortcut.as_view(),
        name='project_shortcuts'),
    url(r'^api/(?P<project_name>[\d\w\s-]+)/(?P<series_number>[\d\w\s-]+)/$',
        project_views.GetProjectRevisionIds.as_view(),
        name='api_get_ids'),


    # maintainers
    url(r'^maintainer/(?P<maintainer_id>\d+)/$',
        author_views.MaintainerProfileView.as_view(),
        name='maintainer'),

    # Authors
    # lists all authors
    url(r'^authors/$',
        author_views.AuthorListView.as_view(),
        name='authors_list'),
    # details about an author
    url(r'^authors/(?P<author_id>\d+)/$',
        author_views.detail_author,
        name='author'),
    url(r'^authors/(?P<author_id>\d+)/edit$',
        author_views.AuthorUpdateView.as_view(),
        name='author_edit'),

]
