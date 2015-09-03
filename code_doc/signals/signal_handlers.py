from django.db import IntegrityError
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.dispatch import receiver

from django.conf import settings

from ..models import Author, Revision, Branch, Artifact, get_deflation_directory, ProjectSeries

import logging
import tempfile
import os
import tarfile
import shutil
import functools

# logger for this file
logger = logging.getLogger(__name__)


# User to author linking
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def linkToAuthor(sender, **kwargs):
    """Checks if a User is already linked to an Author.
       If not, then a new Author is created and the User's
       information is copied over to the Author.
    """
    def user_is_linkable_to_author(user):
        """A user must provide enough information in order to be linkable to an Author."""
        return not (user.last_name == "" or
                    user.first_name == "" or
                    user.email == "")

    user_instance = kwargs['instance']

    if not hasattr(user_instance, 'author'):
        if user_is_linkable_to_author(user_instance):

            # @note(Stephan):
            # We cannot use get_or_create here since in the get we only care about
            # the email (since it is the primary key of the Author).
            if Author.objects.filter(email=user_instance.email).count() == 1:
                linked_author = Author.objects.get(email=user_instance.email)
            else:
                linked_author = Author.objects.create(
                                  lastname=user_instance.last_name,
                                  firstname=user_instance.first_name,
                                  email=user_instance.email,
                                  django_user=user_instance)
            user_instance.author = linked_author
            user_instance.save()


@receiver(m2m_changed, sender=Artifact.project_series.through)
def callback_check_revision_references(sender,
                                       action,
                                       reverse,
                                       instance, **kwargs):
    """If an artifact is removed from a series, we have to check if the
       revision it belonged to still contains artifacts.

       If an artifact is added to a series, a revision is implicitely "added" to
       to this series
    """

    logger.debug('[signal artifact-serie] m2m_changed / artifact %s', instance)

    if reverse:

        changed_artifacts_pks = kwargs['pk_set']
        project_series = instance

        # We modified the reverse relationship which means we
        # modified series.artifact.
        if action == 'pre_add':
            # checking integrity for all added artifacts
            proj = project_series.project
            for pk in changed_artifacts_pks:
                artifact = Artifact.objects.get(pk=pk)
                if artifact.project != proj:
                    raise IntegrityError

        elif action == 'post_remove':
            # Removing artifacts: we have to check if the
            # revision is still referenced.
            for pk in changed_artifacts_pks:
                artifact = Artifact.objects.get(pk=pk)
                artifact_revision = artifact.revision

                if artifact_revision and len(artifact_revision.get_all_referencing_series()) == 0:
                    artifact_revision.delete()

                if artifact.project_series.count() == 0:
                    artifact.delete()

        elif action == 'post_add':
            for pk in changed_artifacts_pks:
                artifact = Artifact.objects.get(pk=pk)
                limits_artifact_numbers(artifact)

    else:
        # We modified the forward relationship which means we
        # modified artifact.project_series.
        artifact = instance

        if action == 'pre_add':
            # We want to add a Series to an Artifact, we need to check that
            # this Series belongs to the same Project that the Artifact does
            proj = artifact.project
            added_series_pks = kwargs['pk_set']
            for pk in added_series_pks:
                series = ProjectSeries.objects.get(pk=pk)
                if series.project != proj:
                    raise IntegrityError

        elif action == 'post_add':
            limits_artifact_numbers(artifact)

        elif action == 'post_remove':
            # clean up revision if it does not contain any artifact
            # only in case of the deletion of an artifact
            revision = artifact.revision
            if revision and len(revision.get_all_referencing_series()) == 0:
                revision.delete()

            if artifact.project_series.count() == 0:
                artifact.delete()


# Relation between Branches and Revisions
# @receiver(m2m_changed, sender=Branch.revisions.through)
# def callback_check_revision_references(sender, **kwargs):
#     """Handles changes in the Branch <--> Revision relation.

#        Enforces the revision_limit for branches, and deletes
#        non-referenced Revisions.
#     """
#     action = kwargs['action']

#     if kwargs['reverse']:
#         # We modified the reverse relationship which means we
#         # modified revision.branches.
#         # kwargs['instance'] thus always returns a revision
#         if action == 'post_add':
#             # We have added a branch to a revision. Check if the maximum
#             # revision count for this branch is violated, and if it is,
#             # delete the earliest Revisions of this branch
#             changed_objects = kwargs['pk_set']
#             for pk in changed_objects:
#                 branch = Branch.objects.get(pk=pk)
#                 enforce_revision_limit_for_branch(branch)

#         elif action == 'post_remove':
#             # We have removed a branch from a revision.
#             revision = kwargs['instance']
#             ensure_revision_references(revision)
#     else:
#         # We modified the forward relationship which means we
#         # modified branch.revisions.
#         # kwargs['instance'] thus always returns a branch
#         if action == 'post_add':
#             # We added a revision to a branch. Check if the maximum
#             # revision count is violated.
#             branch = kwargs['instance']
#             enforce_revision_limit_for_branch(branch)

#         elif action == 'post_remove':
#             # We removed a revision from a branch. Now we have to check
#             # if this removed revision is referenced by any other branch.
#             # If not, we can delete it.
#             changed_objects = kwargs['pk_set']
#             for pk in changed_objects:
#                 revision = Revision.objects.get(pk=pk)
#                 ensure_revision_references(revision)


def ensure_revision_references(revision):
    """Checks if the revision is still referenced by any branch.
       If it is not, the revision can be deleted.
    """
    if revision.branches.all().count() == 0:
        revision.delete()


def enforce_revision_limit_for_branch(branch):
    """Checks if the branch has too many Revisions. If it does,
       we remove the earliest Revisions until the desired max amount
       is reached.
    """
    while branch.revisions.count() > branch.nb_revisions_to_keep:
        revision_to_remove = branch.revisions.earliest()
        branch.revisions.remove(revision_to_remove)


def limits_artifact_numbers(artifact):
    """Contains the logic for removing the revisions from series or branches
    when their respective limit is reached"""

    # logger.debug('[signals.limits_artifact_numbers] artifact %s', artifact)

    project = artifact.project
    proj_nb_revisions_to_keep = project.nb_revisions_to_keep

    if artifact.revision is not None:
        # we are in the mode where we limit the revisions

        for serie in artifact.project_series.all():

            # these two numbers serve the same purpose
            if serie.nb_revisions_to_keep is not None or proj_nb_revisions_to_keep is not None:

                nb_revisions_limit = serie.nb_revisions_to_keep \
                    if serie.nb_revisions_to_keep is not None \
                    else proj_nb_revisions_to_keep

                if nb_revisions_limit > 0:
                    # get all revisions of this serie
                    all_artifacts = Artifact.objects.filter(project_series=serie)

                    # we do not delete our own revision
                    all_serie_revision = Revision.objects\
                        .filter(artifacts__in=all_artifacts)\
                        .distinct()\
                        .order_by('commit_time')

                    nb_current_revisions = all_serie_revision.count()
                    if(nb_current_revisions > nb_revisions_limit):
                        for rev_to_remove in all_serie_revision[:(nb_current_revisions - nb_revisions_limit)]:
                            artifacts_to_prune = serie.artifacts.filter(revision=rev_to_remove).all()
                            # logger.debug('[signals.limits_artifact_numbers] artifacts %s removed, all %s',
                            #             artifacts_to_prune.all(),
                            #             all_artifacts.all())

                            for art in artifacts_to_prune:
                                serie.artifacts.remove(art)

                            # serie.artifacts.remove(*artifacts_to_prune)

                    pass

    else:
        # we filter the number of artifacts without revision instead
        for serie in artifact.project_series.all():

            # these two numbers serve the same purpose
            if serie.nb_revisions_to_keep is not None or proj_nb_revisions_to_keep is not None:
                all_artifacts = Artifact.objects.filter(project_series=serie)\
                    .order_by('upload_date')

                nb_current_artifacts = all_artifacts.count()
                nb_artifacts_limit = serie.nb_revisions_to_keep \
                    if serie.nb_revisions_to_keep is not None \
                    else proj_nb_revisions_to_keep

                if(nb_current_artifacts > nb_artifacts_limit):
                    artifacts_to_prune = all_artifacts[:(nb_current_artifacts - nb_artifacts_limit)]
                    # logger.debug('[signals.limits_artifact_numbers] artifacts %s removed, all %s',
                    #             artifacts_to_prune.all(),
                    #             all_artifacts.all())

                    # for art in artifacts_to_prune:
                    #    art.project_series.remove(serie)
                    serie.artifacts.remove(*artifacts_to_prune)

            pass  # if
        pass  # for

    pass  # if artifact.revision


# Artifacts
def is_deflated(instance):
    """Returns true if the artifact instance should or have been deflated"""
    return instance.is_documentation and \
        os.path.splitext(instance.artifactfile.name)[1] in ['.tar', '.bz2', '.gz']


@receiver(post_save, sender=Artifact)
def callback_artifact_deflation_on_save(sender,
                                        instance,
                                        created,
                                        raw,
                                        **kwargs):
    """Callback received after an artifact has been saved in the database. In case of a documentation
    artifact, and in case the artifact is a zip/archive, we deflate it"""

    logger.debug('[project artifact] post_save artifact %s', instance)

    # we do not perform operation in case of database populating action
    if raw:
        return

    # we do not perform any action in case of save failure
    if not created:
        return

    # deflate if documentation
    if is_deflated(instance):

        # I do not know if this one is needed in fact, it is if we are in the save method of
        # Artifact but from here the file should be fully accessible
        with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE) as f:
            for chunk in instance.artifactfile.chunks():
                f.write(chunk)
            f.seek(0)
            instance.artifactfile.close()

            deflate_directory = get_deflation_directory(instance)
            # logger.debug('[project artifact] deflating artifact %s to %s', instance, deflate_directory)
            tar = tarfile.open(fileobj=f)

            curdir = os.path.abspath(os.curdir)
            if(not os.path.exists(deflate_directory)):
                os.makedirs(deflate_directory)
            os.chdir(deflate_directory)
            tar.extractall()  # path = deflate_directory)
            os.chdir(curdir)

    pass


@receiver(pre_delete, sender=Artifact)
def callback_artifact_documentation_delete(sender, instance, using, **kwargs):
    """Callback received before an artifact has is being removed from the database. In case of
    a documentation artifact, and in case the artifact is a zip/archive, the deflated directory
    is removed."""
    # logger.debug('[project artifact] pre_delete artifact %s', instance)

    # deflate if documentation and archive
    if is_deflated(instance):
        deflate_directory = get_deflation_directory(instance)
        if(os.path.exists(deflate_directory)):
            # logger.debug('[project artifact] removing deflated artifact %s from %s', instance, deflate_directory)

            def on_error(instance, function, path, excinfo):
                logger.warning('[project artifact] error removing %s for instance %s',
                               path, instance)
                return

            shutil.rmtree(deflate_directory, False, functools.partial(on_error, instance=instance))

    # removing the file on post delete
    pass


@receiver(post_delete, sender=Artifact)
def callback_artifact_delete(sender, instance, using, **kwargs):
    """Removes the artifact itself"""
    # logger.debug('[project artifact] post_delete artifact %s', instance)
    storage, path = instance.artifactfile.storage, instance.artifactfile.path
    try:
        storage.delete(path)
    except WindowsError, e:
        logger.warning('[project artifact] error removing %s for instance %s', path, instance)
    # if(os.path.exists(instance.full_path_name())):
    #    os.remove(instance.full_path_name())
