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


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def deleting(sender, **kwargs):
    logger.debug('Deleting a user')


# # Revision handling
# @receiver(post_save, sender=Revision)
# def check_revision_count_and_delete(sender, **kwargs):
#     """ Checks if there are too many revisions.
#         If not, we dont have to do anything.
#         If yes, we have to delete the least recent revision of the branch this
#         new revision belongs to.
#     """
#     revision_instance = kwargs['instance']

#     branches = revision_instance.branches.all()

#     for branch in branches:
#         revisions_for_branch = None
#         pass
#         while revisions_for_branch.count() > branch.nr_of_revisions_kept:
#             revision_to_delete = revisions_for_branch.earliest()
#             # Check if this revision is referenced by multiple branches


# @receiver(pre_delete, sender=Revision)
# def delete_corresponding_artifacts(sender, **kwargs):
#     """ Deletes all the artifacts, that belong to this revision"""
#     revision_instance = kwargs['instance']

#     for artifact in revision_instance.artifacts.all():
#         # The proper deletion should be handled by the signal defined in models.py

#         # @todo(Stephan): delete the artifacts here
#         artifact.delete()

@receiver(m2m_changed, sender=Branch.revisions.through)
def callback_check_revision_references(sender, **kwargs):
    """Checks which revisions were removed from the branch. If those revisions
       do not belong to any other branches, then we can delete the revision.
    """
    action = kwargs['action']
    if action == 'post_remove':
        changed_objects = kwargs['pk_set']

        for pk in changed_objects:
            revision = Revision.objects.get(pk=pk)

            if revision.branches.all().count() == 0:
                revision.delete()


# Artifacts
def is_deflated(instance):
    """Returns true if the artifact instance should or have been deflated"""
    return instance.is_documentation and \
        os.path.splitext(instance.artifactfile.name)[1] in ['.tar', '.bz2', '.gz']


# @receiver(pre_save, sender=Artifact)
# def callback_revision_deletion_on_artifact_promotion(sender, **kwargs):
#     """ Checks if the save affected the revision field of the Artifact.
#         If it did, we check to see if we have to delete the old revision.
#     """
#     artifact_instance = kwargs['instance']

#     update_fields = kwargs['update_fields']

#     if update_fields:
#         for (field, value) in update_fields:
#             if field == 'revision':
#                 old_revision = artifact_instance.revision
#                 if old_revision.artifacts.count() == 1:
#                     old_revision.delete()


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
