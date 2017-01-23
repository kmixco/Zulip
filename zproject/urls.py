from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView, RedirectView
from django.utils.module_loading import import_string
import os.path
import zerver.forms
from zproject import dev_urls
from zproject.legacy_urls import legacy_urls
from zerver.views.integrations import IntegrationView, APIView, HelpView
from zerver.lib.integrations import WEBHOOK_INTEGRATIONS
from zerver.webhooks import github_dispatcher


from django.contrib.auth.views import (login, password_reset,
                                       password_reset_done, password_reset_confirm, password_reset_complete)

import zerver.tornado.views
import zerver.views
import zerver.views.auth
import zerver.views.compatibility
import zerver.views.home
import zerver.views.registration
import zerver.views.zephyr
import zerver.views.users
import zerver.views.unsubscribe
import zerver.views.integrations
import zerver.views.user_settings
import zerver.views.muting
import confirmation.views

from zerver.lib.rest import rest_dispatch

# NB: There are several other pieces of code which route requests by URL:
#
#   - legacy_urls.py contains API endpoint written before the redesign
#     and should not be added to.
#
#   - runtornado.py has its own URL list for Tornado views.  See the
#     invocation of web.Application in that file.
#
#   - The Nginx config knows which URLs to route to Django or Tornado.
#
#   - Likewise for the local dev server in tools/run-dev.py.

# These views serve pages (HTML). As such, their internationalization
# must depend on the url.
#
# If you're adding a new page to the website (as opposed to a new
# endpoint for use by code), you should add it here.
i18n_urls = [
    url(r'^$', zerver.views.home.home, name='zerver.views.home.home'),
    # We have a desktop-specific landing page in case we change our /
    # to not log in in the future. We don't want to require a new
    # desktop app build for everyone in that case
    url(r'^desktop_home/$', zerver.views.home.desktop_home, name='zerver.views.home.desktop_home'),

    url(r'^accounts/login/sso/$', zerver.views.auth.remote_user_sso, name='login-sso'),
    url(r'^accounts/login/jwt/$', zerver.views.auth.remote_user_jwt, name='login-jwt'),
    url(r'^accounts/login/social/(\w+)$', zerver.views.auth.start_social_login, name='login-social'),
    url(r'^accounts/login/google/$', zerver.views.auth.start_google_oauth2, name='zerver.views.auth.start_google_oauth2'),
    url(r'^accounts/login/google/send/$',
        zerver.views.auth.send_oauth_request_to_google,
        name='zerver.views.auth.send_oauth_request_to_google'),
    url(r'^accounts/login/google/done/$', zerver.views.auth.finish_google_oauth2, name='zerver.views.auth.finish_google_oauth2'),
    url(r'^accounts/login/subdomain/$', zerver.views.auth.log_into_subdomain, name='zerver.views.auth.log_into_subdomain'),
    url(r'^accounts/login/local/$', zerver.views.auth.dev_direct_login, name='zerver.views.auth.dev_direct_login'),
    # We have two entries for accounts/login to allow reverses on the Django
    # view we're wrapping to continue to function.
    url(r'^accounts/login/', zerver.views.auth.login_page, {'template_name': 'zerver/login.html'}, name='zerver.views.auth.login_page'),
    url(r'^accounts/login/', login, {'template_name': 'zerver/login.html'},
        name='django.contrib.auth.views.login'),
    url(r'^accounts/logout/', zerver.views.auth.logout_then_login, name='zerver.views.auth.logout_then_login'),

    url(r'^accounts/webathena_kerberos_login/',
        zerver.views.zephyr.webathena_kerberos_login,
        name='zerver.views.zephyr.webathena_kerberos_login'),

    url(r'^accounts/password/reset/$', password_reset,
        {'post_reset_redirect': '/accounts/password/reset/done/',
         'template_name': 'zerver/reset.html',
         'email_template_name': 'registration/password_reset_email.txt',
         'password_reset_form': zerver.forms.ZulipPasswordResetForm,
         }, name='django.contrib.auth.views.password_reset'),
    url(r'^accounts/password/reset/done/$', password_reset_done,
        {'template_name': 'zerver/reset_emailed.html'}),
    url(r'^accounts/password/reset/(?P<uidb64>[0-9A-Za-z]+)/(?P<token>.+)/$',
        password_reset_confirm,
        {'post_reset_redirect': '/accounts/password/done/',
         'template_name': 'zerver/reset_confirm.html',
         'set_password_form': zerver.forms.LoggingSetPasswordForm},
        name='django.contrib.auth.views.password_reset_confirm'),
    url(r'^accounts/password/done/$', password_reset_complete,
        {'template_name': 'zerver/reset_done.html'}),

    # Avatar
    url(r'^avatar/(?P<email_or_id>[\S]+)?/(?P<medium>[\S]+)?', zerver.views.users.avatar, name='zerver.views.users.avatar'),
    url(r'^avatar/(?P<email_or_id>[\S]+)?', zerver.views.users.avatar, name='zerver.views.users.avatar'),

    # Registration views, require a confirmation ID.
    url(r'^accounts/home/', zerver.views.registration.accounts_home,
        name='zerver.views.registration.accounts_home'),
    url(r'^accounts/send_confirm/(?P<email>[\S]+)?',
        TemplateView.as_view(template_name='zerver/accounts_send_confirm.html'), name='send_confirm'),
    url(r'^accounts/register/', zerver.views.registration.accounts_register,
        name='zerver.views.registration.accounts_register'),
    url(r'^accounts/do_confirm/(?P<confirmation_key>[\w]+)', confirmation.views.confirm, name='confirmation.views.confirm'),

    url(r'^accounts/confirm_new_email/(?P<confirmation_key>[\w]+)',
        zerver.views.user_settings.confirm_email_change,
        name='zerver.views.user_settings.confirm_email_change'),

    # Email unsubscription endpoint. Allows for unsubscribing from various types of emails,
    # including the welcome emails (day 1 & 2), missed PMs, etc.
    url(r'^accounts/unsubscribe/(?P<type>[\w]+)/(?P<token>[\w]+)',
        zerver.views.unsubscribe.email_unsubscribe, name='zerver.views.unsubscribe.email_unsubscribe'),

    # Portico-styled page used to provide email confirmation of terms acceptance.
    url(r'^accounts/accept_terms/$', zerver.views.home.accounts_accept_terms, name='zerver.views.home.accounts_accept_terms'),

    # Realm Creation
    url(r'^create_realm/$', zerver.views.registration.create_realm, name='zerver.views.create_realm'),
    url(r'^create_realm/(?P<creation_key>[\w]+)$', zerver.views.registration.create_realm, name='zerver.views.create_realm'),

    # Login/registration
    url(r'^register/$', zerver.views.registration.accounts_home, name='register'),
    url(r'^login/$', zerver.views.auth.login_page, {'template_name': 'zerver/login.html'}, name='zerver.views.auth.login_page'),

    # A registration page that passes through the Realm.string_id, for totally open realms.
    url(r'^register/(?P<realm_str>\S+)/$', zerver.views.registration.accounts_home_with_realm_str,
        name='zerver.views.registration.accounts_home_with_realm_str'),

    # API and integrations documentation
    url(r'^api/$', APIView.as_view(template_name='zerver/api.html')),
    url(r'^api/endpoints/$', zerver.views.integrations.api_endpoint_docs, name='zerver.views.integrations.api_endpoint_docs'),
    url(r'^integrations/$', IntegrationView.as_view()),
    url(r'^about/$', TemplateView.as_view(template_name='zerver/about.html')),
    url(r'^apps/$', TemplateView.as_view(template_name='zerver/apps.html')),

    url(r'^robots\.txt$', RedirectView.as_view(url='/static/robots.txt', permanent=True)),

    # Landing page, features pages, signup form, etc.
    url(r'^hello/$', TemplateView.as_view(template_name='zerver/hello.html'), name='landing-page'),
    url(r'^new-user/$', RedirectView.as_view(url='/hello', permanent=True)),
    url(r'^features/$', TemplateView.as_view(template_name='zerver/features.html')),
    url(r'^find_my_team/$', zerver.views.registration.find_my_team, name='zerver.views.registration.find_my_team'),
    url(r'^authors/$', zerver.views.users.authors_view, name='zerver.views.users.authors_view')
]

# If a Terms of Service is supplied, add that route
if settings.TERMS_OF_SERVICE is not None:
    i18n_urls += [url(r'^terms/$', TemplateView.as_view(template_name='zerver/terms.html'))]

# Make a copy of i18n_urls so that they appear without prefix for english
urls = list(i18n_urls)

# These endpoints constitute the redesigned API (V1), which uses:
# * REST verbs
# * Basic auth (username:password is email:apiKey)
# * Take and return json-formatted data
#
# If you're adding a new endpoint to the code that requires authentication,
# please add it here.
# See rest_dispatch in zerver.lib.rest for an explanation of auth methods used
#
# All of these paths are accessed by either a /json or /api/v1 prefix
v1_api_and_json_patterns = [
    # realm-level calls
    url(r'^realm$', rest_dispatch,
        {'PATCH': 'zerver.views.realm.update_realm'}),

    # Returns a 204, used by desktop app to verify connectivity status
    url(r'generate_204$', zerver.views.registration.generate_204, name='zerver.views.registration.generate_204'),

    # realm/domains -> zerver.views.realm_aliases
    url(r'^realm/domains$', rest_dispatch,
        {'GET': 'zerver.views.realm_aliases.list_aliases',
         'POST': 'zerver.views.realm_aliases.create_alias'}),
    url(r'^realm/domains/(?P<domain>\S+)$', rest_dispatch,
        {'PATCH': 'zerver.views.realm_aliases.patch_alias',
         'DELETE': 'zerver.views.realm_aliases.delete_alias'}),

    # realm/emoji -> zerver.views.realm_emoji
    url(r'^realm/emoji$', rest_dispatch,
        {'GET': 'zerver.views.realm_emoji.list_emoji'}),
    url(r'^realm/emoji/(?P<emoji_name>.*)$', rest_dispatch,
        {'PUT': 'zerver.views.realm_emoji.upload_emoji',
         'DELETE': 'zerver.views.realm_emoji.delete_emoji'}),

    # realm/icon -> zerver.views.realm_icon
    url(r'^realm/icon$', rest_dispatch,
        {'PUT': 'zerver.views.realm_icon.upload_icon',
         'DELETE': 'zerver.views.realm_icon.delete_icon_backend',
         'GET': 'zerver.views.realm_icon.get_icon_backend'}),

    # realm/filters -> zerver.views.realm_filters
    url(r'^realm/filters$', rest_dispatch,
        {'GET': 'zerver.views.realm_filters.list_filters',
         'POST': 'zerver.views.realm_filters.create_filter'}),
    url(r'^realm/filters/(?P<filter_id>\d+)$', rest_dispatch,
        {'DELETE': 'zerver.views.realm_filters.delete_filter'}),

    # users -> zerver.views.users
    #
    # Since some of these endpoints do something different if used on
    # yourself with `/me` as the email, we need to make sure that we
    # don't accidentally trigger these.  The cleanest way to do that
    # is to add a regular expression assertion that it isn't `/me/`
    # (or ends with `/me`, in the case of hitting the root URL).
    url(r'^users$', rest_dispatch,
        {'GET': 'zerver.views.users.get_members_backend',
         'POST': 'zerver.views.users.create_user_backend'}),
    url(r'^users/(?!me/)(?P<email>[^/]*)/reactivate$', rest_dispatch,
        {'POST': 'zerver.views.users.reactivate_user_backend'}),
    url(r'^users/(?!me/)(?P<email>[^/]*)/presence$', rest_dispatch,
        {'GET': 'zerver.views.presence.get_presence_backend'}),
    url(r'^users/(?!me$)(?P<email>[^/]*)$', rest_dispatch,
        {'PATCH': 'zerver.views.users.update_user_backend',
         'DELETE': 'zerver.views.users.deactivate_user_backend'}),
    url(r'^bots$', rest_dispatch,
        {'GET': 'zerver.views.users.get_bots_backend',
         'POST': 'zerver.views.users.add_bot_backend'}),
    url(r'^bots/(?!me/)(?P<email>[^/]*)/api_key/regenerate$', rest_dispatch,
        {'POST': 'zerver.views.users.regenerate_bot_api_key'}),
    url(r'^bots/(?!me/)(?P<email>[^/]*)$', rest_dispatch,
        {'PATCH': 'zerver.views.users.patch_bot_backend',
         'DELETE': 'zerver.views.users.deactivate_bot_backend'}),

    # messages -> zerver.views.messages
    # GET returns messages, possibly filtered, POST sends a message
    url(r'^messages$', rest_dispatch,
        {'GET': 'zerver.views.messages.get_old_messages_backend',
         'POST': 'zerver.views.messages.send_message_backend'}),
    url(r'^messages/(?P<message_id>[0-9]+)$', rest_dispatch,
        {'GET': 'zerver.views.messages.json_fetch_raw_message',
         'PATCH': 'zerver.views.messages.update_message_backend'}),
    url(r'^messages/render$', rest_dispatch,
        {'POST': 'zerver.views.messages.render_message_backend'}),
    url(r'^messages/flags$', rest_dispatch,
        {'POST': 'zerver.views.messages.update_message_flags'}),
    url(r'^messages/(?P<message_id>\d+)/history$', rest_dispatch,
        {'GET': 'zerver.views.messages.get_message_edit_history'}),

    # reactions -> zerver.view.reactions
    # PUT adds a reaction to a message
    # DELETE removes a reaction from a message
    url(r'^messages/(?P<message_id>[0-9]+)/emoji_reactions/(?P<emoji_name>.*)$',
        rest_dispatch,
        {'PUT': 'zerver.views.reactions.add_reaction_backend',
         'DELETE': 'zerver.views.reactions.remove_reaction_backend'}),

    # attachments -> zerver.views.attachments
    url(r'^attachments$', rest_dispatch,
        {'GET': 'zerver.views.attachments.list_by_user'}),
    url(r'^attachments/(?P<attachment_id>[0-9]+)$', rest_dispatch,
        {'DELETE': 'zerver.views.attachments.remove'}),

    # typing -> zerver.views.typing
    # POST sends a typing notification event to recipients
    url(r'^typing$', rest_dispatch,
        {'POST': 'zerver.views.typing.send_notification_backend'}),

    # user_uploads -> zerver.views.upload
    url(r'^user_uploads$', rest_dispatch,
        {'POST': 'zerver.views.upload.upload_file_backend'}),

    # invite -> zerver.views.invite
    url(r'^invite/bulk$', rest_dispatch,
        {'POST': 'zerver.views.invite.bulk_invite_users'}),

    # users/me -> zerver.views
    url(r'^users/me$', rest_dispatch,
        {'GET': 'zerver.views.users.get_profile_backend',
         'DELETE': 'zerver.views.users.deactivate_user_own_backend'}),
    url(r'^users/me/buddy$', rest_dispatch,
        {'PATCH': 'zerver.views.users.update_buddy_list'}),
    url(r'^users/me/pointer$', rest_dispatch,
        {'GET': 'zerver.views.pointer.get_pointer_backend',
         'PUT': 'zerver.views.pointer.update_pointer_backend',
         'POST': 'zerver.views.pointer.update_pointer_backend'}),
    url(r'^users/me/presence$', rest_dispatch,
        {'POST': 'zerver.views.presence.update_active_status_backend'}),
    # Endpoint used by mobile devices to register their push
    # notification credentials
    url(r'^users/me/apns_device_token$', rest_dispatch,
        {'POST': 'zerver.views.push_notifications.add_apns_device_token',
         'DELETE': 'zerver.views.push_notifications.remove_apns_device_token'}),
    url(r'^users/me/android_gcm_reg_id$', rest_dispatch,
        {'POST': 'zerver.views.push_notifications.add_android_reg_id',
         'DELETE': 'zerver.views.push_notifications.remove_android_reg_id'}),

    # users/me -> zerver.views.user_settings
    url(r'^users/me/api_key/regenerate$', rest_dispatch,
        {'POST': 'zerver.views.user_settings.regenerate_api_key'}),
    url(r'^users/me/enter-sends$', rest_dispatch,
        {'POST': 'zerver.views.user_settings.change_enter_sends'}),
    url(r'^users/me/avatar$', rest_dispatch,
        {'PUT': 'zerver.views.user_settings.set_avatar_backend',
         'DELETE': 'zerver.views.user_settings.delete_avatar_backend'}),

    # settings -> zerver.views.user_settings
    url(r'^settings/display$', rest_dispatch,
        {'PATCH': 'zerver.views.user_settings.update_display_settings_backend'}),
    url(r'^settings/notifications$', rest_dispatch,
        {'PATCH': 'zerver.views.user_settings.json_change_notify_settings'}),
    url(r'^settings/ui$', rest_dispatch,
        {'PATCH': 'zerver.views.user_settings.json_change_ui_settings'}),

    # users/me/alert_words -> zerver.views.alert_words
    url(r'^users/me/alert_words$', rest_dispatch,
        {'GET': 'zerver.views.alert_words.list_alert_words',
         'POST': 'zerver.views.alert_words.set_alert_words',
         'PUT': 'zerver.views.alert_words.add_alert_words',
         'DELETE': 'zerver.views.alert_words.remove_alert_words'}),

    url(r'^users/me/(?P<stream_id>\d+)/topics$', rest_dispatch,
        {'GET': 'zerver.views.streams.get_topics_backend'}),


    # streams -> zerver.views.streams
    # (this API is only used externally)
    url(r'^streams$', rest_dispatch,
        {'GET': 'zerver.views.streams.get_streams_backend'}),

    # GET returns `stream_id`, stream name should be encoded in the url query (in `stream` param)
    url(r'^get_stream_id', rest_dispatch,
        {'GET': 'zerver.views.streams.json_get_stream_id'}),

    # GET returns "stream info" (undefined currently?), HEAD returns whether stream exists (200 or 404)
    url(r'^streams/(?P<stream_id>\d+)/members$', rest_dispatch,
        {'GET': 'zerver.views.streams.get_subscribers_backend'}),
    url(r'^streams/(?P<stream_id>\d+)$', rest_dispatch,
        {'PATCH': 'zerver.views.streams.update_stream_backend',
         'DELETE': 'zerver.views.streams.deactivate_stream_backend'}),
    url(r'^default_streams$', rest_dispatch,
        {'POST': 'zerver.views.streams.add_default_stream',
         'DELETE': 'zerver.views.streams.remove_default_stream'}),
    # GET lists your streams, POST bulk adds, PATCH bulk modifies/removes
    url(r'^users/me/subscriptions$', rest_dispatch,
        {'GET': 'zerver.views.streams.list_subscriptions_backend',
         'POST': 'zerver.views.streams.add_subscriptions_backend',
         'PATCH': 'zerver.views.streams.update_subscriptions_backend',
         'DELETE': 'zerver.views.streams.remove_subscriptions_backend'}),
    # muting -> zerver.views.muting
    url(r'^users/me/subscriptions/muted_topics$', rest_dispatch,
        {'POST': 'zerver.views.muting.set_muted_topics',
         'PATCH': 'zerver.views.muting.update_muted_topic'}),

    # used to register for an event queue in tornado
    url(r'^register$', rest_dispatch,
        {'POST': 'zerver.views.events_register.events_register_backend'}),

    # events -> zerver.tornado.views
    url(r'^events$', rest_dispatch,
        {'GET': 'zerver.tornado.views.get_events_backend',
         'DELETE': 'zerver.tornado.views.cleanup_event_queue'}),
]

# Include the dual-use patterns twice
urls += [
    url(r'^api/v1/', include(v1_api_and_json_patterns)),
    url(r'^json/', include(v1_api_and_json_patterns)),
]

# user_uploads -> zerver.views.upload.serve_file_backend
#
# This url is an exception to the url naming schemes for endpoints. It
# supports both API and session cookie authentication, using a single
# URL for both (not 'api/v1/' or 'json/' prefix). This is required to
# easily support the mobile apps fetching uploaded files without
# having to rewrite URLs, and is implemented using the
# 'override_api_url_scheme' flag passed to rest_dispatch
urls += url(r'^user_uploads/(?P<realm_id_str>(\d*|unk))/(?P<filename>.*)',
            rest_dispatch,
            {'GET': ('zerver.views.upload.serve_file_backend',
                     {'override_api_url_scheme'})}),

# Incoming webhook URLs
# We don't create urls for particular git integrations here
# because of generic one below
for incoming_webhook in WEBHOOK_INTEGRATIONS:
    if incoming_webhook.url_object:
        urls.append(incoming_webhook.url_object)

urls.append(url(r'^api/v1/external/github', github_dispatcher.api_github_webhook_dispatch))

# Mobile-specific authentication URLs
urls += [
    # This json format view used by the mobile apps lists which authentication
    # backends the server allows, to display the proper UI and check for server existence
    url(r'^api/v1/get_auth_backends', zerver.views.auth.api_get_auth_backends, name='zerver.views.auth.api_get_auth_backends'),

    # used by mobile apps to check if they are compatible with the server
    url(r'^compatibility$', zerver.views.compatibility.check_compatibility),

    # This json format view used by the mobile apps accepts a username
    # password/pair and returns an API key.
    url(r'^api/v1/fetch_api_key$', zerver.views.auth.api_fetch_api_key, name='zerver.views.auth.api_fetch_api_key'),

    # This is for the signing in through the devAuthBackEnd on mobile apps.
    url(r'^api/v1/dev_fetch_api_key$', zerver.views.auth.api_dev_fetch_api_key, name='zerver.views.auth.api_dev_fetch_api_key'),
    # This is for fetching the emails of the admins and the users.
    url(r'^api/v1/dev_get_emails$', zerver.views.auth.api_dev_get_emails, name='zerver.views.auth.api_dev_get_emails'),

    # Used to present the GOOGLE_CLIENT_ID to mobile apps
    url(r'^api/v1/fetch_google_client_id$',
        zerver.views.auth.api_fetch_google_client_id,
        name='zerver.views.auth.api_fetch_google_client_id'),
]

# Include URL configuration files for site-specified extra installed
# Django apps
for app_name in settings.EXTRA_INSTALLED_APPS:
    app_dir = os.path.join(settings.DEPLOY_ROOT, app_name)
    if os.path.exists(os.path.join(app_dir, 'urls.py')):
        urls += [url(r'^', include('%s.urls' % (app_name,)))]
        i18n_urls += import_string("{}.urls.i18n_urlpatterns".format(app_name))

# Tornado views
urls += [
    # Used internally for communication between Django and Tornado processes
    url(r'^notify_tornado$', zerver.tornado.views.notify, name='zerver.tornado.views.notify'),
]

# Python Social Auth
urls += [url(r'^', include('social_django.urls', namespace='social'))]

# User documentation site
urls += [url(r'^help/(?P<article>.*)$', HelpView.as_view(template_name='zerver/help/main.html'))]

if settings.DEVELOPMENT:
    urls += dev_urls.urls
    i18n_urls += dev_urls.i18n_urls

# The sequence is important; if i18n urls don't come first then
# reverse url mapping points to i18n urls which causes the frontend
# tests to fail
urlpatterns = i18n_patterns(*i18n_urls) + urls + legacy_urls
