
from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from django.contrib.auth.models import User
from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse

import os
import json
import logging

from ..models.projects import Project, ProjectSeries
from ..models.models import Topic
from ..forms.forms import ModalAddUserForm

logger = logging.getLogger(__name__)


def index(request):
    """Front page"""

    nb_columns = 4
    max_in_column = 3  # 5 project max in a column

    projects_list = Project.objects.order_by('name')
    topics_list = Topic.objects.filter(project__in=projects_list).distinct().order_by('name')

    context = {'projects_list': projects_list,
               'topics_list': topics_list}

    context['size_row'] = 12 // nb_columns

    current_project_list = [i for i in projects_list]  # copy
    list_project_per_column = []

    for i in range(nb_columns):
        current_max_len = min(max_in_column, len(current_project_list))
        current_chunk = current_project_list[:current_max_len] if current_max_len else []
        current_project_list = current_project_list[current_max_len:]
        list_project_per_column.append(current_chunk)

    # transpose the list
    list_project_per_line = []
    for current_line_index in range(max_in_column):
        current_line = []
        has_some = False
        for current_column in list_project_per_column:
            element_to_add = current_column[current_line_index] if len(current_column) > current_line_index else None
            has_some |= element_to_add is not None
            current_line.append(element_to_add)

        if not has_some:
            break

        list_project_per_line.append(current_line)

    context['list_project_per_line'] = list_project_per_line

    # same for topics
    current_topic_list = [i for i in topics_list]  # copy
    list_topics_per_column = []

    for i in range(nb_columns):
        current_max_len = min(max_in_column, len(current_topic_list))
        current_chunk = current_topic_list[:current_max_len] if current_max_len else []
        current_topic_list = current_topic_list[current_max_len:]
        list_topics_per_column.append(current_chunk)

    # transpose the list
    list_topic_per_line = []
    for current_line_index in range(max_in_column):
        current_line = []
        has_some = False
        for current_column in list_topics_per_column:
            element_to_add = current_column[current_line_index] if len(current_column) > current_line_index else None
            has_some |= element_to_add is not None
            current_line.append(element_to_add)

        if not has_some:
            break

        list_topic_per_line.append(current_line)

    context['list_topic_per_line'] = list_topic_per_line

    return render(request,
                  'code_doc/index.html',
                  context)


def about(request):
    """About page"""
    return render(request, 'code_doc/about.html', {})


def script(request):
    """Returns the script used for uploading stuff"""
    filename = 'code_doc_upload.py'
    file_content = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir,
                                     'utils',
                                     'send_new_artifact.py'),
                        'rb').read()  # binary is important here
    # TODO add a test on this len(file_content)
    response = HttpResponse(file_content, content_type='application/text')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    response['Content-Length'] = len(file_content)
    return response


def get_usernames(request):
    """ Method for getting all usernames. """

    all_users = User.objects.all()
    dict_users = {}
    for user in all_users:
        dict_users[user.username] = user

    if request.is_ajax():
        q = request.GET.get('term', '')

        names = [name for name in dict_users.keys() if q in name]
        results = []
        for cn in names:
            cn_json = {'value': cn}
            results.append(cn_json)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


class ModalAddUserView(FormView):
    form_class = ModalAddUserForm
    template_name = 'code_doc/series/modal_add_user_form.html'

    def get_form_kwargs(self):
        kwargs = FormView.get_form_kwargs(self)

        # Add project and series id
        current_serie = ProjectSeries.objects.get(pk=self.kwargs['series_id'])
        kwargs.update({'serie': current_serie,
                       'project': current_serie.project
                       })
        return kwargs

    def get_success_url(self, **kwargs):
        return reverse('project_series_edit', kwargs={'project_id': self.kwargs['project_id'],
                                                      'series_id': self.kwargs['series_id']})

    def form_valid(self, form):

        # Occurs after the form validation
        # Here we need to add a user.
        current_serie = ProjectSeries.objects.get(pk=self.kwargs['series_id'])

        # Find corresponding user
        # Form has been validated, so we don't need to check for Errors.
        user = User.objects.get(username=form.cleaned_data['username'])

        # Give view permission
        current_serie.view_users.add(user)

        #return super(ModalAddUserView, self).form_valid(form)
        return render(self.request, 'code_doc/series/modal_add_user_form_success.html')


class TopicView(DetailView):
    pk_url_kwarg = 'topic_id'
    template_name = 'code_doc/topics/topics.html'
    context_object_name = 'topic'
    model = Topic


class TopicListView(ListView):
    paginate_by = 10
    template_name = "code_doc/topics/topic_list.html"
    context_object_name = "topics"
    model = Topic
