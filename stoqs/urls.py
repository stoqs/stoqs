# -*- coding: utf-8 -*-


from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
##from django.contrib import admin
##admin.autodiscover()

urlpatterns = [
    ##re_path(r'^$',  # noqa
    ##    TemplateView.as_view(template_name='pages/home.html'),
    ##    name="home"),
    ##re_path(r'^about/$',
    ##    TemplateView.as_view(template_name='pages/about.html'),
    ##    name="about"),

    # Uncomment the next line to enable the admin:
    ##re_path(r'^admin/', admin.site.urls),

    # User management
    ##re_path(r'^users/', include("users.urls", namespace="users")),
    ##re_path(r'^accounts/', include('allauth.urls')),

    # Uncomment the next line to enable avatars
    ##re_path(r'^avatar/', include('avatar.urls')),

    # Your stuff: custom urls go here
    re_path(r'', include('stoqs.urls', namespace='stoqs')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# See http://django-debug-toolbar.readthedocs.io/en/1.0/installation.html#explicit-setup
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
