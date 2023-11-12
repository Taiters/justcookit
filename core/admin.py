from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import Ingredient, Recipe, User

admin.site.register(User, UserAdmin)
admin.site.register(Ingredient)
admin.site.register(Recipe)
