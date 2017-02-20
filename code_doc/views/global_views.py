
from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic.detail import DetailView
from django.views.generic import ListView

import os
import logging

from ..models import Project, Topic

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
    file_content = open(os.path.join(os.path.dirname(__file__),
                                     'utils',
                                     'send_new_artifact.py'),
                        'rb').read()  # binary is important here
    # TODO add a test on this len(file_content)
    response = HttpResponse(file_content, content_type='application/text')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    response['Content-Length'] = len(file_content)
    return response


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
