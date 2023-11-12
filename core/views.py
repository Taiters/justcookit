import json

import requests
from bs4 import BeautifulSoup
from django.shortcuts import redirect, render

from core.forms import RecipeURLForm


def _load_schema(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    schemas = soup.find_all("script", attrs={"type": "application/ld+json"})
    for s in schemas:
        parsed = json.loads(s.text)
        if parsed.get("@type") == "Recipe":
            return parsed

    return None


def home(request):
    recipe_url_form = RecipeURLForm()
    return render(
        request,
        "core/home.html",
        {
            "form": recipe_url_form,
        },
    )


def recipe(request):
    recipe_url_form = RecipeURLForm(request.GET)
    if not recipe_url_form.is_valid():
        return redirect("core:home")

    schema = _load_schema(recipe_url_form.cleaned_data["recipe_url"])

    return render(
        request,
        "core/recipe.html",
        {
            "schema": json.dumps(schema, indent=4),
        },
    )
