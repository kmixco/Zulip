from typing import Callable, Dict, Optional, Set, Tuple

from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from zerver.lib.name_restrictions import is_disposable_domain

# TODO: Move DisposableEmailError, etc. into here.
from zerver.models import (
    email_to_username,
    email_to_domain,
    get_user_by_delivery_email,
    is_cross_realm_bot_email,
    DisposableEmailError,
    DomainNotAllowedForRealmError,
    EmailContainsPlusError,
    Realm,
    RealmDomain,
    UserProfile,
)

def validate_disposable(email: str) -> None:
    if is_disposable_domain(email_to_domain(email)):
        raise DisposableEmailError

def get_realm_email_validator(realm: Realm) -> Callable[[str], None]:
    if not realm.emails_restricted_to_domains:
        # Should we also do '+' check for non-resticted realms?
        if realm.disallow_disposable_email_addresses:
            return validate_disposable

        # allow any email through
        return lambda email: None

    '''
    RESTRICTIVE REALMS:

    Some realms only allow emails within a set
    of domains that are configured in RealmDomain.

    We get the set of domains up front so that
    folks can validate multiple emails without
    multiple round trips to the database.
    '''

    query = RealmDomain.objects.filter(realm=realm)
    rows = list(query.values('allow_subdomains', 'domain'))

    allowed_domains = {
        r['domain'] for r in rows
    }

    allowed_subdomains = {
        r['domain'] for r in rows
        if r['allow_subdomains']
    }

    def validate(email: str) -> None:
        '''
        We don't have to do a "disposable" check for restricted
        domains, since the realm is already giving us
        a small whitelist.
        '''

        if '+' in email_to_username(email):
            raise EmailContainsPlusError

        domain = email_to_domain(email)

        if domain in allowed_domains:
            return

        while len(domain) > 0:
            subdomain, sep, domain = domain.partition('.')
            if domain in allowed_subdomains:
                return

        raise DomainNotAllowedForRealmError

    return validate

# Is a user with the given email address allowed to be in the given realm?
# (This function does not check whether the user has been invited to the realm.
# So for invite-only realms, this is the test for whether a user can be invited,
# not whether the user can sign up currently.)
def email_allowed_for_realm(email: str, realm: Realm) -> None:
    '''
    Avoid calling this in a loop!
    Instead, call get_realm_email_validator()
    outside of the loop.
    '''
    get_realm_email_validator(realm)(email)

def validate_email_is_valid(
    email: str,
    validate_email_allowed_in_realm: Callable[[str], None],
) -> Optional[str]:

    try:
        validators.validate_email(email)
    except ValidationError:
        return _("Invalid address.")

    try:
        validate_email_allowed_in_realm(email)
    except DomainNotAllowedForRealmError:
        return _("Outside your domain.")
    except DisposableEmailError:
        return _("Please use your real email address.")
    except EmailContainsPlusError:
        return _("Email addresses containing + are not allowed.")

    return None

def email_reserved_for_system_bots_error(email: str) -> str:
    return '%s is reserved for system bots' % (email,)

def get_existing_user_errors(
    target_realm: Realm,
    emails: Set[str],
) -> Dict[str, Tuple[str, Optional[str], bool]]:
    '''
    We use this function even for a list of one emails.

    It checks "new" emails to make sure that they don't
    already exist.  There's a bit of fiddly logic related
    to cross-realm bots and mirror dummies too.
    '''
    errors = {}  # type: Dict[str, Tuple[str, Optional[str], bool]]

    def process_email(email: str) -> None:
        if is_cross_realm_bot_email(email):
            msg = email_reserved_for_system_bots_error(email)
            code = msg
            deactivated = False
            errors[email] = (msg, code, deactivated)
            return

        try:
            existing_user_profile = get_user_by_delivery_email(email, target_realm)
        except UserProfile.DoesNotExist:
            # HAPPY PATH!  Most people invite users that don't exist yet.
            return

        if existing_user_profile.is_mirror_dummy:
            if existing_user_profile.is_active:
                raise AssertionError("Mirror dummy user is already active!")
            return

        '''
        Email has already been taken by a "normal" user.
        '''
        deactivated = not existing_user_profile.is_active

        if existing_user_profile.is_active:
            msg = _('%s already has an account') % (email,)
            code = _("Already has an account.")
        else:
            msg = 'The account for %s has been deactivated' % (email,)
            code = _("Account has been deactivated.")

        errors[email] = (msg, code, deactivated)

    for email in emails:
        process_email(email)

    return errors
