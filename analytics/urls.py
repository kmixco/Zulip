from django.conf.urls import url
import analytics.views

i18n_urlpatterns = [
    url(r'^activity$', analytics.views.get_activity,
        name='analytics.views.get_activity'),
    url(r'^realm_activity/(?P<realm>[\S]+)/$', analytics.views.get_realm_activity,
        name='analytics.views.get_realm_activity'),
    url(r'^user_activity/(?P<email>[\S]+)/$', analytics.views.get_user_activity,
        name='analytics.views.get_user_activity'),
]

urlpatterns = i18n_urlpatterns
