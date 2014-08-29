# -*- coding: utf-8 -*-
from django import forms

class ArtifactForm(forms.Form):
    artifactfile = forms.FileField(
        label='Select a file',
        help_text='max. 42 megabytes'
    )


class ProjectVersionForm(forms.Form):
  version = forms.CharField()
  description = forms.CharField()