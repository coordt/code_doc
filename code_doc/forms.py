# -*- coding: utf-8 -*-
from django.forms import (
    Form,
    ModelForm,
    CharField,
    Textarea,
    DateInput,
    CheckboxSelectMultiple,
    TextInput,
    EmailInput,
)
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.forms.widgets import HiddenInput

from .models.projects import ProjectSeries
from .models.authors import Author
from .models.artifacts import Artifact

import os
import logging

logger = logging.getLogger(__name__)


class AuthorForm(ModelForm):
    class Meta:
        model = Author
        fields = "__all__"
        widgets = {
            "firstname": TextInput(attrs={"size": 50}),
            "lastname": TextInput(attrs={"size": 50}),
            "email": EmailInput(attrs={"size": 50}),
            "gravatar_email": EmailInput(attrs={"size": 50}),
            "home_page_url": TextInput(attrs={"size": 50}),
        }


class SeriesEditionForm(ModelForm):
    """Form definition that is used when adding and editing a project series."""

    class Meta:
        model = ProjectSeries
        fields = (
            "project",
            "series",
            "release_date",
            "description_mk",
            "is_public",
            "view_users",
            "view_groups",
            "perms_users_artifacts_add",
            "perms_groups_artifacts_add",
            "perms_users_artifacts_del",
            "perms_groups_artifacts_del",
            "nb_revisions_to_keep",
        )
        labels = {
            "series": "Name",
            "description_mk": "Description",
            "nb_revisions_to_keep": "Revisions limit",
        }
        help_texts = {
            "is_public": (
                "If checked, the series will be visible from everyone. If not "
                "you have to specify the users/groups to which"
                "you are granting access"
            ),
            "description_mk": "Description/content/scope of the series in MarkDown format",
            "nb_revisions_to_keep": "Indicates the maximum number of revisions that this series will keep. An artifact without "
            "any revision is considered on its own revision. Leave blank to avoid the limit.",
        }
        widgets = {
            "project": HiddenInput(),
            "series": Textarea(
                attrs={"cols": 60, "rows": 2, "style": "resize:none; width: 100%;"}
            ),
            "description_mk": Textarea(
                attrs={
                    "cols": 60,
                    "rows": 10,
                    "style": "resize:vertical; width: 100%; min-height: 50px;",
                }
            ),
            "release_date": DateInput(
                attrs={
                    "class": "datepicker",
                    "data-date-format": "dd/mm/yyyy",
                    "data-provide": "datepicker",
                },
                format="%d/%m/%Y",
            ),
            "view_users": CheckboxSelectMultiple,
            "view_groups": CheckboxSelectMultiple,
            "perms_users_artifacts_add": CheckboxSelectMultiple,
            "perms_groups_artifacts_add": CheckboxSelectMultiple,
            "perms_users_artifacts_del": CheckboxSelectMultiple,
            "perms_groups_artifacts_del": CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):

        super(SeriesEditionForm, self).__init__(*args, **kwargs)

        active_users = set()
        active_groups = set()
        if kwargs["instance"] is not None:
            instance = kwargs["instance"]
            for perm in (
                "view_users",
                "perms_users_artifacts_add",
                "perms_users_artifacts_del",
            ):
                active_users |= set(
                    (_ for _ in getattr(instance, perm).values_list("id", flat=True))
                )

            for perm in (
                "view_groups",
                "perms_groups_artifacts_add",
                "perms_groups_artifacts_del",
            ):
                active_groups |= set(
                    (_ for _ in getattr(instance, perm).values_list("id", flat=True))
                )

        else:
            for perm in (
                "view_users",
                "perms_users_artifacts_add",
                "perms_users_artifacts_del",
            ):
                active_users |= set([_.id for _ in kwargs["initial"][perm]])
            for perm in (
                "view_groups",
                "perms_groups_artifacts_add",
                "perms_groups_artifacts_del",
            ):
                active_groups |= set([_.id for _ in kwargs["initial"][perm]])

        # we narrow the queryset in all cases to the ones that appear in those sets
        # otherwise the form shows all possible entries, which clutters the view
        # the initial parameter is useful for setting the initial selection, but not for the queryset
        for perm in (
            "view_users",
            "perms_users_artifacts_add",
            "perms_users_artifacts_del",
        ):
            qs = (
                self.fields[perm]
                .queryset.filter(id__in=list(active_users))
                .order_by("username")
            )
            self.fields[perm].queryset = qs
        for perm in (
            "view_groups",
            "perms_groups_artifacts_add",
            "perms_groups_artifacts_del",
        ):
            qs = (
                self.fields[perm]
                .queryset.filter(id__in=list(active_groups))
                .order_by("name")
            )
            self.fields[perm].queryset = qs

        # If creation, permissions are not editable
        if kwargs["instance"] is None:
            for perm in (
                "view_users",
                "perms_users_artifacts_add",
                "perms_users_artifacts_del",
            ):
                self.fields[perm].disabled = True


class ArtifactEditionForm(ModelForm):

    # this one is just a text entry, otherwise the clean method is trying to see if it exists or not
    # as a model from the string entered, which yields an error.
    revision = CharField(
        label="Revision",
        required=False,
        help_text="If this file was generated by a particular revision "
        "of the code, you may indicate it here.",
        widget=Textarea(
            attrs={
                "cols": 60,
                "rows": 1,
                "style": "resize:none; width: 100%; min-height: 30px;",
            }
        ),
    )

    branch = CharField(
        label="Branch",
        required=False,
        help_text="If the revision of the file is on a specific branch, "
        "you may indicate it here.",
        widget=Textarea(
            attrs={
                "cols": 60,
                "rows": 1,
                "style": "resize:none; width: 100%; min-height: 30px;",
            }
        ),
    )

    class Meta:
        model = Artifact
        fields = (
            "artifactfile",
            "description",
            "is_documentation",
            "documentation_entry_file",
            "upload_date",
        )
        labels = {
            "series": "Name",
            "artifactfile": "File",
            "description": "Description",
            "is_documentation": "Documentation",
            "documentation_entry_file": "Doc entry",
        }
        help_texts = {
            "is_documentation": (
                "If checked, the artifact is an archive containing a documentation, "
                "that will be deflated on the server. "
            ),
            "description": "optional (short) description of the artifact content",
            "documentation_entry_file": (
                "If the file is contains a documentation, this should be the entry "
                "point of the document"
            ),
        }
        widgets = {
            "description": Textarea(
                attrs={
                    "cols": 60,
                    "rows": 10,
                    "style": "resize:vertical; width: 100%; min-height: 50px;",
                }
            ),
            "documentation_entry_file": Textarea(
                attrs={
                    "cols": 60,
                    "rows": 1,
                    "style": "resize:none; width: 100%; min-height: 30px;",
                }
            ),
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
        form = context["form"]

        context["project"] = current_project
        context["serie"] = current_serie
        context["serie_id"] = current_serie.id
        context["series"] = current_serie
        context["artifacts"] = current_serie.artifacts.all()

        context["automatic_fields"] = (
            form[i]
            for i in (
                "artifactfile",
                "description",
                "is_documentation",
                "documentation_entry_file",
                "revision",
                "branch",
            )
        )

    def clean_revision(self):
        # agnostic to case
        return self.cleaned_data["revision"].strip().lower()

    def clean_branch(self):
        return self.cleaned_data["branch"].strip()

    def clean_description(self):
        return self.cleaned_data["description"].strip()

    def clean_documentation_entry_file(self):
        if self.cleaned_data["documentation_entry_file"]:
            return os.path.relpath(
                self.cleaned_data["documentation_entry_file"].strip()
            )
        return None

    def clean(self):
        """Validates the submitted archive"""

        if "artifactfile" not in self.cleaned_data:
            raise ValidationError("The submitted file is invalid")

        artifact_file = self.cleaned_data["artifactfile"]
        is_doc = self.cleaned_data["is_documentation"]

        # additional checks if we have a doc
        if is_doc:

            if not self.cleaned_data["documentation_entry_file"]:
                msg = "The field 'documentation entry' should be filled for an artifact of type documentation"
                logger.error(msg)
                raise ValidationError(msg)

            # we check if we can open the file with tar
            import tarfile

            try:
                # same logic as tarfile.is_tarfile(tmpfile) but we have fileoj
                tar = tarfile.TarFile.open(fileobj=artifact_file)
            except tarfile.TarError:
                logger.error("The submitted file does not seem to be a valid tar file")
                raise ValidationError(
                    "The submitted file does not seem to be a valid tar file"
                )

            # check that the content of the archive is accessible
            doc_entry = self.cleaned_data["documentation_entry_file"]
            for e in tar.getmembers():
                if os.path.relpath(e.name) == os.path.relpath(doc_entry):
                    break
            else:
                logger.error(
                    "Documentation entry '%s' not found in the tar" % (doc_entry)
                )
                raise ValidationError(
                    'The documentation entry "%(value)s" was not found in the archive',
                    params={"value": doc_entry},
                )

            if e.isdir():
                logger.error("Documentation entry not a file in the tar")
                raise ValidationError(
                    'The documentation entry "%(value)s" does points to a directory',
                    params={"value": doc_entry},
                )

        return self.cleaned_data


class ModalAddUserForm(Form):

    username = CharField(
        label="user_selection",
        required=True,
        initial="",
        widget=TextInput(attrs={"id": "user_selection"}),
    )

    def __init__(self, project, series, *args, **kwargs):
        super(ModalAddUserForm, self).__init__(*args, **kwargs)

        self.project = project
        self.series = series

    def clean_username(self):

        username = self.data["username"].strip()

        # Try to find corresponding user
        if not User.objects.filter(username=username).exists():
            raise ValidationError(
                "Username %(value)s is not registered",
                params={"value": self.data["username"]},
            )

        return username


class ModalAddGroupForm(Form):

    groupname = CharField(
        label="group_selection",
        required=True,
        initial="",
        widget=TextInput(attrs={"id": "group_selection"}),
    )

    def __init__(self, project, series, *args, **kwargs):
        super(ModalAddGroupForm, self).__init__(*args, **kwargs)

        self.project = project
        self.series = series

    def clean_groupname(self):

        groupname = self.data["groupname"].strip()

        # Try to find corresponding group
        if not Group.objects.filter(name=groupname).exists():
            raise ValidationError(
                "Group %(value)s is not registered",
                params={"value": self.data["groupname"]},
            )

        return groupname
