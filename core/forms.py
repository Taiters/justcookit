from django import forms


class RecipeURLForm(forms.Form):
    recipe_url = forms.URLField(label="Recipe URL")
