from django.contrib.gis.admin import *
from django.contrib.gis.admin import ModelAdmin as BaseModelAdmin
from django.contrib.gis.admin import TabularInline as BaseTabularInline
from django.contrib.gis.admin import StackedInline as BaseStackedInline

import threading
_thread_local_vars = threading.local()

class ModelAdmin(BaseModelAdmin):
    # A handy constant for the name of the alternate database.

    def __init__(self,*pargs, **kwargs):
        super(ModelAdmin, self).__init__(*pargs, **kwargs)
        self.using=_thread_local_vars.dbName
        
    def save_model(self, request, obj, form, change):
        # Tell Django to save objects to the 'other' database.
        obj.save(using=self.using)

    def delete_model(self, request, obj):
        # Tell Django to delete objects from the 'other' database
        obj.delete(using=self.using)

    def queryset(self, request):
        # Tell Django to look for objects on the 'other' database.
        return super(ModelAdmin, self).queryset(request).using(self.using)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the 'other' database.
        return super(ModelAdmin, self).formfield_for_foreignkey(db_field, request=request, using=self.using, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        # Tell Django to populate ManyToMany widgets using a query
        # on the 'other' database.
        return super(ModelAdmin, self).formfield_for_manytomany(db_field, request=request, using=self.using, **kwargs)



class TabularInline(BaseTabularInline):
    def __init__(self,*pargs, **kwargs):
        super(TabularInline, self).__init__(*pargs, **kwargs)
        self.using=_thread_local_vars.dbName

    def queryset(self, request):
        # Tell Django to look for inline objects on the 'other' database.
        return super(TabularInline, self).queryset(request).using(self.using)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the 'other' database.
        return super(TabularInline, self).formfield_for_foreignkey(db_field, request=request, using=self.using, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        # Tell Django to populate ManyToMany widgets using a query
        # on the 'other' database.
        return super(TabularInline, self).formfield_for_manytomany(db_field, request=request, using=self.using, **kwargs)

class StackedInline(BaseStackedInline):
    def __init__(self,*pargs, **kwargs):
        super(StackedInline, self).__init__(*pargs, **kwargs)
        self.using=_thread_local_vars.dbName

    def queryset(self, request):
        # Tell Django to look for inline objects on the 'other' database.
        return super(StackedInline, self).queryset(request).using(self.using)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the 'other' database.
        return super(StackedInline, self).formfield_for_foreignkey(db_field, request=request, using=self.using, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        # Tell Django to populate ManyToMany widgets using a query
        # on the 'other' database.
        return super(StackedInline, self).formfield_for_manytomany(db_field, request=request, using=self.using, **kwargs)
