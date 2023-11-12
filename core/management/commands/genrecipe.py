import json

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from openai import OpenAI

from core import models

RECIPE_URL_ARG = "recipe_url"
is_url = URLValidator()

SYSTEM_MESSAGE = """
You are a recipe parser. You accept text from a web page and find a recipe in it if one is present.
Recipe information is represented as a JSON object which consists of only the following fields:
* name: The name of the recipe
* ingredients: A list of "Ingredient" objects
* steps: A list of "Step" objects
* time: The amount of time in minutes to prepare this recipe as an integer

Each "Ingredient" object should contain only the following fields:
* name: The name of the ingredient. Normalize this by capitalizing and removing any quantities
* quantity: The quantity of the ingredient as an integer. The "unit" for this quantity is stored in a separate field
* unit: The unit of measurement for the "quantity" field

Each "step" should contain only the following fields:
* text: The text which describes the step.

Each "unit" can either be:
* "g" if the unit is grams. If it is a multiple of grams, such as "kg", make the appropriate conversion
* "ml" if the unit is millileters. Convert if necessary
* If you cannot use either "g" or "ml", the unit should be null

Your response should contain a single "recipe" field only. If you cannot find a recipe in the content, this should be null.
You must only output a valid JSON object and nothing else.
"""


def _get_recipe_url(options):
    recipe_url = options[RECIPE_URL_ARG]
    try:
        is_url(recipe_url)
        return recipe_url
    except ValidationError as e:
        raise CommandError(e.message)


class Command(BaseCommand):
    help = "Generates a recipe given a URL"

    def add_arguments(self, parser):
        parser.add_argument(
            RECIPE_URL_ARG, help="A URL to a web page which contains a recipe"
        )

    def handle(self, *args, **options):
        client = OpenAI(api_key=settings.OPEN_API_SECRET_KEY)
        recipe_url = _get_recipe_url(options)
        self.stdout.write(f"Getting recipe content from: {recipe_url}")

        res = requests.get(recipe_url)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()

        self.stdout.write("Generating...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_MESSAGE,
                },
                {"role": "user", "content": text},
            ],
        )

        self.stdout.write(self.style.SUCCESS("Generated a recipe!"))

        result = json.loads(response.choices[0].message.content)
        if result["recipe"] is None:
            raise CommandError("Could not find a recipe at URL")

        recipe = models.Recipe.objects.create(
            source_url=recipe_url,
            source_text=text,
            name=result["recipe"]["name"],
            prep_time_minutes=result["recipe"]["time"],
        )
