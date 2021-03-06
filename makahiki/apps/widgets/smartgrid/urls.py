"""urls definition for smartgrid widget."""

from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('',
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/$',
        'apps.widgets.smartgrid.views.view_action',
        name='activity_task'),
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/add/$',
        'apps.widgets.smartgrid.views.add_action',
        name='activity_add_task'),
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/drop/$',
        'apps.widgets.smartgrid.views.drop_action',
        name='activity_drop_task'),
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/codes/$',
        'apps.widgets.smartgrid.view_events.view_codes',
        name='activity_view_codes'),
    url(r'^attend_code/$',
        'apps.widgets.smartgrid.view_events.attend_code',
        name="activity_attend_code"),
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/rsvps/$',
        'apps.widgets.smartgrid.view_events.view_rsvps',
        name='activity_view_rsvps'),
    url(r'^(?P<action_type>[\w]+)/(?P<slug>[\w\d\-]+)/reminder/$',
        'apps.widgets.smartgrid.view_reminders.reminder',
        name='activity_reminder'),
    url(r'^bulk_change/(?P<action_type>[\w]+)/(?P<attribute>[\w]+)/$',
        'apps.widgets.smartgrid.views.bulk_change',
        name="bulk_change"),
)
