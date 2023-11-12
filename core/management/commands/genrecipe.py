import json

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By

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

SYSTEM_MESSAGE_RECIPE_SCHEMA = """
You are a recipe parser. You accept text from a web page and find a recipe in it if one is present.

Recipe information must be returned in JSON format, following the recipe schema described at https://schema.org/Recipe. No other fields should be included.

Your response should only contain a single "recipe" field at the top level. If you cannot find a recipe in the provided content, this field should be null.

Populate as many of the available fields on the recipe schema as possible. Ensure correct formats are used, such as ISO 8601 for durations, or QuantitativeValue instead of text where possible.

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
        self.stdout.write(f"Getting page content from: {recipe_url}")

        # res = requests.get(recipe_url)
        # content = res.text

        options = webdriver.FirefoxOptions()
        options.add_argument("-headless")
        browser = webdriver.Firefox(options=options)
        browser.get(recipe_url)
        content = browser.page_source

        self.stdout.write(content)
        soup = BeautifulSoup(content, "html.parser")

        # self.stdout.write(res.text)

        self.stdout.write("Checking for existing recipe schema on page")

        schemas = soup.find_all("script", attrs={"type": "application/ld+json"})
        for s in schemas:
            try:
                parsed = json.loads(s.text)
                if parsed.get("@type") == "Recipe":
                    self.stdout.write(self.style.SUCCESS("Found an existing schema"))
                    self.stdout.write(json.dumps(parsed, indent=4))
                    return
            except Exception:
                self.stdout.write(self.style.WARNING("Failed to parse schema content:"))
                self.stdout.write(self.style.WARNING(s.text))

        text = soup.get_text()

        # self.stdout.write(text)

        self.stdout.write("Generating a schema from page content")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_MESSAGE_RECIPE_SCHEMA,
                },
                {"role": "user", "content": text},
            ],
        )

        result = json.loads(response.choices[0].message.content)
        if result["recipe"] is None:
            raise CommandError("Could not find a recipe at URL")

        self.stdout.write(self.style.SUCCESS("Generated a recipe!"))

        self.stdout.write(json.dumps(result, indent=4))
