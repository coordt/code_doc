
from django.shortcuts import render

from django.http import HttpResponse, JsonResponse
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Group
from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404

import os
import logging

from ..models.projects import Project, ProjectSeries
from ..models.models import Topic
from ..forms.forms import ModalAddUserForm, ModalAddGroupForm

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


class JSONResponseUsernamesView(TemplateView):
    """ View returning usernames in JSON format."""

    def render_to_json_response(self, context):
        """
        Returns the context in a JSON response.
        """

        return JsonResponse(context, safe=False)

    def render_to_response(self, context):

        return self.render_to_json_response(context)

    def get(self, request):

        if request.is_ajax():
            q = request.GET.get('term', '')
            query_all_users = User.objects.filter(Q(username__contains=q.strip()) |
                                                  Q(first_name__contains=q.strip()) |
                                                  Q(last_name__contains=q.strip())).values_list('username')
            context = [{'value': name} for name in query_all_users]
            success = True

        context.append({'success': success})
        return self.render_to_response(context)


class JSONResponseGroupnamesView(TemplateView):
    """ View returning group names in JSON format."""

    def render_to_json_response(self, context):
        """
        Returns the context in a JSON response.
        """

        return JsonResponse(context, safe=False)

    def render_to_response(self, context):

        return self.render_to_json_response(context)

    def get(self, request):

        if request.is_ajax():
            q = request.GET.get('term', '')
            query_all_groups = Group.objects.filter(name__contains=q.strip()).values_list('name')
            context = [{'value': name} for name in query_all_groups]
            success = True

        context.append({'success': success})
        return self.render_to_response(context)


class ModalAddUserView(PermissionRequiredMixin, FormView):
    """ View for granting access to a series to a registered user. """

    form_class = ModalAddUserForm
    template_name = 'code_doc/series/modal_add_user_form.html'
    permission_required = ('code_doc.series_edit',)

    def has_permission(self):
        perms = self.get_permission_required()
        kwargs = self.get_form_kwargs()
        return self.request.user.has_perms(perms, kwargs['series'])

    def get_form_kwargs(self):
        kwargs = super(ModalAddUserView, self).get_form_kwargs()

        # Add project and series id
        current_series = get_object_or_404(ProjectSeries, pk=self.kwargs['series_id'])

        kwargs['series'] = current_series
        kwargs['project'] = current_series.project
        return kwargs

    def handle_no_permission(self):
        return HttpResponse('Unauthorized', status=401)

    def get_success_url(self, **kwargs):
        return reverse('project_series_edit', kwargs={'project_id': self.kwargs['project_id'],
                                                      'series_id': self.kwargs['series_id']})

    def form_valid(self, form):

        # Occurs after the form validation
        # Here we need to add a user.
        current_series = ProjectSeries.objects.get(pk=self.kwargs['series_id'])

        # Find corresponding user
        # Form has been validated, so we don't need to check for Errors.
        user = User.objects.get(username=form.cleaned_data['username'])

        # Give view permission
        current_series.view_users.add(user)

        return render(self.request, 'code_doc/series/modal_add_user_or_group_form_success.html')


class ModalAddGroupView(PermissionRequiredMixin, FormView):
    """ View for granting access to a series to a registered group. """

    form_class = ModalAddGroupForm
    template_name = 'code_doc/series/modal_add_group_form.html'
    permission_required = ('code_doc.series_edit',)

    def has_permission(self):
        perms = self.get_permission_required()
        kwargs = self.get_form_kwargs()
        return self.request.user.has_perms(perms, kwargs['series'])

    def get_form_kwargs(self):
        kwargs = super(ModalAddGroupView, self).get_form_kwargs()

        # Add project and series id
        current_series = get_object_or_404(ProjectSeries, pk=self.kwargs['series_id'])

        kwargs['series'] = current_series
        kwargs['project'] = current_series.project
        return kwargs

    def handle_no_permission(self):
        return HttpResponse('Unauthorized', status=401)

    def get_success_url(self, **kwargs):
        return reverse('project_series_edit', kwargs={'project_id': self.kwargs['project_id'],
                                                      'series_id': self.kwargs['series_id']})

    def form_valid(self, form):

        # Occurs after the form validation
        # Here we need to add a group.
        current_series = ProjectSeries.objects.get(pk=self.kwargs['series_id'])

        # Find corresponding group
        # Form has been validated, so we don't need to check for Errors.
        group = Group.objects.get(name=form.cleaned_data['groupname'])

        # Give view permission
        current_series.view_groups.add(group)

        return render(self.request, 'code_doc/series/modal_add_user_or_group_form_success.html')


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
