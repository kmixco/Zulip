from typing import List

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.utils.timezone import now as timezone_now


def revoke_invitations(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Realm = apps.get_model("zerver", "Realm")
    Confirmation = apps.get_model("confirmation", "Confirmation")
    Confirmation.INVITATION = 2
    Confirmation.MULTIUSE_INVITE = 6
    PreregistrationUser = apps.get_model("zerver", "PreregistrationUser")
    UserProfile = apps.get_model("zerver", "UserProfile")
    MultiuseInvite = apps.get_model("zerver", "MultiuseInvite")

    STATUS_REVOKED = 2

    def get_valid_invite_confirmations_generated_by_users(
        user_ids: List[int],
    ) -> List[int]:
        prereg_user_ids = (
            PreregistrationUser.objects.filter(referred_by_id__in=user_ids)
            .exclude(status=STATUS_REVOKED)
            .values_list("id", flat=True)
        )
        confirmation_ids = list(
            Confirmation.objects.filter(
                type=Confirmation.INVITATION,
                object_id__in=prereg_user_ids,
                expiry_date__gte=timezone_now(),
            ).values_list("id", flat=True)
        )

        multiuse_invite_ids = MultiuseInvite.objects.filter(
            referred_by_id__in=user_ids
        ).values_list("id", flat=True)
        confirmation_ids += list(
            Confirmation.objects.filter(
                type=Confirmation.MULTIUSE_INVITE,
                expiry_date__gte=timezone_now(),
                object_id__in=multiuse_invite_ids,
            ).values_list("id", flat=True)
        )

        return confirmation_ids

    print("")
    for realm_id in Realm.objects.values_list("id", flat=True):
        deactivated_user_ids = UserProfile.objects.filter(
            is_active=False, realm_id=realm_id
        ).values_list("id", flat=True)
        confirmation_ids = get_valid_invite_confirmations_generated_by_users(deactivated_user_ids)

        if len(confirmation_ids) > 0:
            print(
                f"Revoking invitations by deactivated users in realm {realm_id}: {confirmation_ids}"
            )

        Confirmation.objects.filter(id__in=confirmation_ids).update(expiry_date=timezone_now())


class Migration(migrations.Migration):
    """
    User deactivation used to *not* revoke invitations generated by the user.
    This has been fixed in the implementation, but this migration is still needed
    to ensure old invitations are revoked for users who were deactivated in the past.
    """

    atomic = False

    dependencies = [
        ("zerver", "0382_create_role_based_system_groups"),
    ]

    operations = [
        migrations.RunPython(
            revoke_invitations,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        )
    ]
