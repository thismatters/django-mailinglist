from django.contrib import admin

from test_project import models


@admin.register(models.AdHocUserModel)
class AdHocUserModelAdmin(admin.ModelAdmin):
    model = models.AdHocUserModel
    list_display = ("first_name", "last_name", "email")
