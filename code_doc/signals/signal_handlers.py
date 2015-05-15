from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.dispatch import receiver

from django.conf import settings

from code_doc.models import Author, Revision, Branch, Artifact, get_deflation_directory

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
       information is copied over to the Author. """
    user_instance = kwargs['instance']

    if not hasattr(user_instance, 'author'):
        linked_author = Author(lastname=user_instance.last_name,
                               firstname=user_instance.first_name,
                               email=user_instance.email,
                               django_user=user_instance)
        linked_author.save()
        user_instance.author = linked_author


# Relation between Branches and Revisions
@receiver(m2m_changed, sender=Branch.revisions.through)
def callback_check_revision_references(sender, **kwargs):
    """Handles changes in the Branch <--> Revision relation.

       Enforces the revision_limit for branches, and deletes
       non-referenced Revisions.
    """
    action = kwargs['action']

    if kwargs['reverse']:
        # We modified the reverse relationship which means we
        # modified revision.branches.
        # kwargs['instance'] thus always returns a revision
        if action == 'post_add':
            # We have added a branch to a revision. Check if the maximum
            # revision count for this branch is violated, and if it is,
            # delete the earliest Revisions of this branch
            changed_objects = kwargs['pk_set']
            for pk in changed_objects:
                branch = Branch.objects.get(pk=pk)
                enforce_revision_limit_for_branch(branch)

        elif action == 'post_remove':
            # We have removed a branch from a revision.
            revision = kwargs['instance']
            ensure_revision_references(revision)
    else:
        # We modified the forward relationship which means we
        # modified branch.revisions.
        # kwargs['instance'] thus always returns a branch
        if action == 'post_add':
            # We added a revision to a branch. Check if the maximum
            # revision count is violated.
            branch = kwargs['instance']
            enforce_revision_limit_for_branch(branch)

        elif action == 'post_remove':
            # We removed a revision from a branch. Now we have to check
            # if this removed revision is referenced by any other branch.
            # If not, we can delete it.
            changed_objects = kwargs['pk_set']
            for pk in changed_objects:
                revision = Revision.objects.get(pk=pk)
                ensure_revision_references(revision)


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
    while branch.revisions.count() > branch.nr_of_revisions_kept:
        revision_to_remove = branch.revisions.earliest()
        branch.revisions.remove(revision_to_remove)


# Branches
@receiver(post_save, sender=Branch)
def callback_enforce_revision_limit_on_change(sender, **kwargs):
    branch_instance = kwargs['instance']
    enforce_revision_limit_for_branch(branch_instance)


# Artifacts
def is_deflated(instance):
    """Returns true if the artifact instance should or have been deflated"""
    return instance.is_documentation and \
        os.path.splitext(instance.artifactfile.name)[1] in ['.tar', '.bz2', '.gz']


@receiver(pre_save, sender=Artifact)
def callback_check_revision_artifact_count(sender, **kwargs):
    artifact_instance = kwargs['instance']
    updated_fields = kwargs['update_fields']

    if updated_fields:
        for field in updated_fields:
            if field == 'revision':
                if artifact_instance.id:    # If the object existed before
                    # Get the Artifact before it was changed
                    pre_saved_artifact = sender.objects.get(pk=artifact_instance.pk)
                    pre_saved_revision = pre_saved_artifact.revision

                    # Delete the revision if this Artifact is the only one it references
                    if pre_saved_revision.artifacts.count() == 1:
                        pre_saved_revision.delete()

                        # @note(Stephan):
                        # I don't know why we need this explicit save here.
                        # If we don't have it, then the following Exception is raised:
                        # DatabaseError("Save with update_fields did not affect any rows.")
                        artifact_instance.save()

                # We are not handling any other field updates manually
                break


@receiver(post_save, sender=Artifact)
def callback_artifact_deflation_on_save(sender, instance, created, raw, **kwargs):
    """Callback received after an artifact has been saved in the database. In case of a documentation
    artifact, and in case the artifact is a zip/archive, we deflate it"""

    # logger.debug('[project artifact] post_save artifact %s', instance)

    # we do not perform any deflation in case of database populating action
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
    # logger.debug('[project artifact] post_delete artifact %s', instance)
    storage, path = instance.artifactfile.storage, instance.artifactfile.path
    storage.delete(path)
    try:
        storage.delete(path)
    except WindowsError, e:
        logger.warning('[project artifact] error removing %s for instance %s', path, instance)
    # if(os.path.exists(instance.full_path_name())):
    #    os.remove(instance.full_path_name())
