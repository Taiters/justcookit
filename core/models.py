from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Unit(models.TextChoices):
    GRAMS = "g", "Grams"
    MILLILETERS = "ml", "Millileters"


class Ingredient(models.Model):
    name = models.CharField(max_length=255)


class Recipe(models.Model):
    source_url = models.URLField(unique=True)
    source_text = models.TextField()
    name = models.CharField(max_length=255)
    prep_time_minutes = models.IntegerField()
    ingredients = models.ManyToManyField(Ingredient, through="RecipeIngredient")
    last_generated = models.DateTimeField(auto_now_add=True)
    last_generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)
    quantity = models.IntegerField(null=True, blank=True)
    unit = models.CharField(
        max_length=8,
        choices=Unit.choices,
        null=True,
        blank=True,
    )
