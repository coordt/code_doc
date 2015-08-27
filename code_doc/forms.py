# -*- coding: utf-8 -*-
from django.forms import Form, ModelForm, FileField, Textarea, DateInput, CheckboxSelectMultiple, TextInput, EmailInput, Select

from code_doc.models import ProjectSeries, Project, Author
from django.contrib.auth.models import User, Group


class ArtifactForm(Form):
    artifactfile = FileField(
        label='Select a file',
        help_text='max. 42 megabytes'
    )


class AuthorForm(ModelForm):
    class Meta:
        model = Author
        fields = '__all__'
        widgets = {
            'firstname': TextInput(attrs={'size': 50}),
            'lastname': TextInput(attrs={'size': 50}),
            'email': EmailInput(attrs={'size': 50}),
            'gravatar_email': EmailInput(attrs={'size': 50}),
            'home_page_url': TextInput(attrs={'size': 50}),
        }


class ProjectSeriesForm(ModelForm):
    """Form definition that is used when adding and editing a ProjectVersion"""
    class Meta:
        model = ProjectSeries
        fields = (
            'series', 'release_date', 'description_mk',
            'is_public',
            'view_users', 'view_groups',
            'perms_users_artifacts_add', 'perms_groups_artifacts_add',
            'perms_users_artifacts_del', 'perms_groups_artifacts_del'
        )
        labels = {
            'series': 'Name',
            'description_mk': 'Description'
        }
        help_texts = {
            'is_public': 'If checked, the serie will be visible from everyone. If not you have to specify the users/groups to which'
            'you are granting access',
            'description_mk': 'Description/content of the series in MarkDown format'
        }
        widgets = {
            'series': Textarea(attrs={
                                'cols': 60,
                                'rows': 2,
                                'style': "resize:none; width: 100%;"
                                }),
            'description_mk': Textarea(attrs={
                                        'cols': 60,
                                        'rows': 10,
                                        'style': "resize:vertical; width: 100%; min-height: 50px;"
                                        }),
            'release_date': DateInput(attrs={
                                        'class': 'datepicker',
                                        'data-date-format': "dd/mm/yyyy",
                                        'data-provide': 'datepicker'
                                        },
                                      format='%d/%m/%Y'),
            'view_users': CheckboxSelectMultiple,
            'view_groups': CheckboxSelectMultiple,
            'perms_users_artifacts_add': CheckboxSelectMultiple,
            'perms_groups_artifacts_add': CheckboxSelectMultiple,
            'perms_users_artifacts_del': CheckboxSelectMultiple,
            'perms_groups_artifacts_del': CheckboxSelectMultiple,
        }

    def set_context_for_template(self, context, project_id):
        """Sets extra data that is used in the template for displaying the form"""
        try:
            current_project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            # this should not occur here
            raise
        form = context['form']

        context['project'] = current_project
        context['project_id'] = current_project.id

        context['automatic_fields'] = (form[i] for i in ('series', 'release_date',
                                                         'description_mk', 'is_public'))

        context['permission_headers'] = ['View', 'Adding artifacts', 'Removing artifacts']

        # filter out users that do not have access to the project?
        context['active_users'] = User.objects.all()

        context['user_permissions'] = zip(xrange(len(context['active_users'])),
                                          context['active_users'],
                                          form['view_users'],
                                          form['perms_users_artifacts_add'],
                                          form['perms_users_artifacts_del'])
        context['user_permissions'] = [(perms[0], perms[1], tuple(perms[2:])) for perms in context['user_permissions']]

        context['active_groups'] = Group.objects.all()
        context['group_permissions'] = zip(xrange(len(context['active_groups'])),
                                           context['active_groups'],
                                           form['view_groups'],
                                           form['perms_groups_artifacts_add'],
                                           form['perms_groups_artifacts_del'])
        context['group_permissions'] = [(perms[0], perms[1], tuple(perms[2:])) for perms in context['group_permissions']]
