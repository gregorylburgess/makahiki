from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'pages.news.views.index', name='news_index'),
)