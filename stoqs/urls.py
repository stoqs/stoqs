# -*- coding: utf-8 -*-


from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    ##url(r'^$',  # noqa
    ##    TemplateView.as_view(template_name='pages/home.html'),
    ##    name="home"),
    ##url(r'^about/$',
    ##    TemplateView.as_view(template_name='pages/about.html'),
    ##    name="about"),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # User management
    ##url(r'^users/', include("users.urls", namespace="users")),
    ##url(r'^accounts/', include('allauth.urls')),

    # Uncomment the next line to enable avatars
    ##url(r'^avatar/', include('avatar.urls')),

    # Your stuff: custom urls go here
    url(r'', include('stoqs.urls', namespace='stoqs')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# See http://django-debug-toolbar.readthedocs.io/en/1.0/installation.html#explicit-setup
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
