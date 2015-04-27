# -*- coding: utf-8 -*-
from django.forms import Form, ModelForm, FileField, Textarea, DateInput, CheckboxSelectMultiple

from code_doc.models import ProjectSeries


class ArtifactForm(Form):
    artifactfile = FileField(
        label='Select a file',
        help_text='max. 42 megabytes'
    )


class ProjectSeriesForm(ModelForm):
    """Form definition that is used when adding and editing a ProjectVersion"""
    class Meta:
        model = ProjectSeries
        fields = (
            'series', 'release_date', 'description_mk', 'view_users', 'view_groups', 'is_public',
            'view_artifacts_users', 'view_artifacts_groups'
        )
        labels = {
            'series': 'Series name',
            'description_mk': 'Description'
        }
        help_texts = {
            'description_mk': 'Description/content of the series in MarkDown format'
        }
        widgets = {
            'series': Textarea(attrs={
                                'cols': 120,
                                'rows': 2,
                                'style': "resize:none"
                                }),
            'description_mk': Textarea(attrs={
                                        'cols': 120,
                                        'rows': 10,
                                        'style': "resize:vertical"
                                        }),
            'release_date': DateInput(attrs={
                                        'class': 'datepicker',
                                        'data-date-format': "dd/mm/yyyy",
                                        'data-provide': 'datepicker'
                                        },
                                      format='%d/%m/%Y'),
            'view_users': CheckboxSelectMultiple,
            'view_groups': CheckboxSelectMultiple,
            'view_artifacts_users': CheckboxSelectMultiple,
            'view_artifacts_groups': CheckboxSelectMultiple
        }
