# -*- coding: utf-8 -*-
from django.forms import Form, ModelForm, FileField, CharField, Textarea, DateInput, CheckboxSelectMultiple, TextInput, EmailInput, Select
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..models.artifacts import Artifact

import os
import logging
logger = logging.getLogger(__name__)


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


class SeriesEditionForm(ModelForm):
    """Form definition that is used when adding and editing a project serie"""

    class Meta:
        model = ProjectSeries
        fields = (
            'series', 'release_date', 'description_mk',
            'is_public',
            'view_users', 'view_groups',
            'perms_users_artifacts_add', 'perms_groups_artifacts_add',
            'perms_users_artifacts_del', 'perms_groups_artifacts_del',
            'nb_revisions_to_keep'
        )
        labels = {
            'series': 'Name',
            'description_mk': 'Description',
            'nb_revisions_to_keep': 'Revisions limit'
        }
        help_texts = {
            'is_public': 'If checked, the series will be visible from everyone. If not you have to specify the users/groups to which'
            'you are granting access',
            'description_mk': 'Description/content/scope of the series in MarkDown format',
            'nb_revisions_to_keep':
                'Indicates the maximum number of revisions that this series will keep. An artifact without '
                'any revision is considered on its own revision. Leave blank to avoid the limit.'
        }
        widgets = {
            'series': Textarea(attrs={'cols': 60,
                                      'rows': 2,
                                      'style': "resize:none; width: 100%;"}),
            'description_mk': Textarea(attrs={'cols': 60,
                                              'rows': 10,
                                              'style': "resize:vertical; width: 100%; min-height: 50px;"}),
            'release_date': DateInput(attrs={'class': 'datepicker',
                                             'data-date-format': "dd/mm/yyyy",
                                             'data-provide': 'datepicker'},
                                      format='%d/%m/%Y'),
            'view_users': CheckboxSelectMultiple,
            'view_groups': CheckboxSelectMultiple,
            'perms_users_artifacts_add': CheckboxSelectMultiple,
            'perms_groups_artifacts_add': CheckboxSelectMultiple,
            'perms_users_artifacts_del': CheckboxSelectMultiple,
            'perms_groups_artifacts_del': CheckboxSelectMultiple,
        }

    @staticmethod
    def set_context_for_template(context, project_id):
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
                                                         'description_mk', 'is_public',
                                                         'nb_revisions_to_keep'))

        context['permission_headers'] = ['View and download', 'Adding artifacts', 'Removing artifacts']

        # filter out users that do not have access to the project?
        context['active_users'] = User.objects.all()

        context['user_permissions'] = zip(xrange(len(context['active_users'])),
                                          context['active_users'],
                                          form['view_users'],
                                          form['perms_users_artifacts_add'],
                                          form['perms_users_artifacts_del'])

        # group the permissions in a tuple so that we can parse them easily
        context['user_permissions'] = [(perms[0], perms[1], tuple(perms[2:])) for perms in context['user_permissions']]

        context['active_groups'] = Group.objects.all()
        context['group_permissions'] = zip(xrange(len(context['active_groups'])),
                                           context['active_groups'],
                                           form['view_groups'],
                                           form['perms_groups_artifacts_add'],
                                           form['perms_groups_artifacts_del'])
        context['group_permissions'] = [(perms[0], perms[1], tuple(perms[2:])) for perms in context['group_permissions']]


class ArtifactEditionForm(ModelForm):

    # this one is just a text entry, otherwise the clean method is trying to see if it exists or not
    # as a model from the string entered, which yields an error.
    revision = CharField(label='Revision',
                         required=False,
                         help_text='If this file was generated by a particular revision '
                                   'of the code, you may indicate it here.',
                         widget=Textarea(attrs={'cols': 60,
                                                'rows': 1,
                                                'style': "resize:none; width: 100%; min-height: 30px;"}),)

    branch = CharField(label='Branch',
                       required=False,
                       help_text='If the revision of the file is on a specific branch, '
                                 'you may indicate it here.',
                       widget=Textarea(attrs={'cols': 60,
                                              'rows': 1,
                                              'style': "resize:none; width: 100%; min-height: 30px;"}),)

    class Meta:
        model = Artifact
        fields = (
            'artifactfile',
            'description',
            'is_documentation',
            'documentation_entry_file',
            'upload_date',
        )
        labels = {
            'series': 'Name',
            'artifactfile': 'File',
            'description': 'Description',
            'is_documentation': 'Documentation',
            'documentation_entry_file': 'Doc entry'
        }
        help_texts = {
            'is_documentation': 'If checked, the artifact is an archive containing a documentation, that will be deflated'
            'on the server. ',
            'description': 'optional (short) description of the artifact content',
            'documentation_entry_file': 'If the file is contains a documentation, this should be the entry point of the document',
        }
        widgets = {
            'description': Textarea(attrs={'cols': 60,
                                           'rows': 10,
                                           'style': "resize:vertical; width: 100%; min-height: 50px;"}),
            'documentation_entry_file': Textarea(attrs={'cols': 60,
                                                        'rows': 1,
                                                        'style': "resize:none; width: 100%; min-height: 30px;"}),
        }

    @staticmethod
    def set_context_for_template(context, serie_id):
        """Sets extra data that is used in the template for displaying the form"""
        try:
            current_serie = ProjectSeries.objects.get(pk=serie_id)
        except ProjectSeries.DoesNotExist:
            # this should not occur here
            raise

        current_project = current_serie.project
        form = context['form']

        context['project'] = current_project
        context['serie'] = current_serie
        context['serie_id'] = current_serie.id
        context['series'] = current_serie
        context['artifacts'] = current_serie.artifacts.all()

        context['automatic_fields'] = (form[i] for i in ('artifactfile', 'description',
                                                         'is_documentation',
                                                         'documentation_entry_file',
                                                         'revision',
                                                         'branch'))

    def clean_revision(self):
        # agnostic to case
        return self.cleaned_data['revision'].strip().lower()

    def clean_branch(self):
        return self.cleaned_data['branch'].strip()

    def clean_description(self):
        return self.cleaned_data['description'].strip()

    def clean_documentation_entry_file(self):
        if self.cleaned_data['documentation_entry_file']:
            return os.path.relpath(self.cleaned_data['documentation_entry_file'].strip())
        return None

    def clean(self):
        """Validates the submitted archive"""

        if 'artifactfile' not in self.cleaned_data:
            raise ValidationError('The submitted file is invalid')

        artifact_file = self.cleaned_data['artifactfile']
        is_doc = self.cleaned_data['is_documentation']

        # additional checks if we have a doc
        if is_doc:

            if not self.cleaned_data['documentation_entry_file']:
                logger.error("The field 'documentation entry' should be filled for an artifact of type documentation")
                raise ValidationError("The field 'documentation entry' should be filled for an artifact of type documentation")

            # we check if we can open the file with tar
            import tarfile
            try:
                # same logic as tarfile.is_tarfile(tmpfile) but we have fileoj
                tar = tarfile.TarFile.open(fileobj=artifact_file)
            except tarfile.TarError:
                logger.error('The submitted file does not seem to be a valid tar file')
                raise ValidationError('The submitted file does not seem to be a valid tar file')

            # check that the content of the archive is accessible
            doc_entry = self.cleaned_data['documentation_entry_file']
            for e in tar.getmembers():
                if os.path.relpath(e.name) == os.path.relpath(doc_entry):
                    break
            else:
                logger.error("Documentation entry '%s' not found in the tar" % (doc_entry))
                raise ValidationError('The documentation entry "%(value)s" was not found in the archive',
                                      params={'value': doc_entry})

            if e.isdir():
                logger.error('Documentation entry not a file in the tar')
                raise ValidationError('The documentation entry "%(value)s" does points to a directory',
                                      params={'value': doc_entry})

        return self.cleaned_data


class ModalAddUserForm(Form):

    username = CharField(label='user_selection',
                         required=True,
                         initial='',
                         widget=TextInput(attrs={'id': "user_selection"}))

    def __init__(self, project, series, *args, **kwargs):
        super(ModalAddUserForm, self).__init__(*args, **kwargs)

        self.project = project
        self.series = series

    def clean_username(self):

        username = self.data['username'].strip()

        # Try to find corresponding user
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError('Username %(value)s is not registered',
                                  params={'value': self.data['username']})

        return username
