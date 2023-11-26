# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from pkg_resources import get_distribution

sys.path.insert(0, os.path.abspath("../.."))

project = "django-mailinglist"
copyright = "2023, Paul Stiverson"
author = "Paul Stiverson"
release = get_distribution("django-mailinglist").version
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = []

root_doc = "index"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

# Django bogus settings for autodoc
import django
from django.conf import settings
from django.core.management import call_command

settings.configure(
    SECRET_KEY="bogus",
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.auth",
        "mailinglist",
    ],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    MAILINGLIST_BASE_URL="http://nowhere",
    MAILINGLIST_DEFAULT_SENDER_EMAIL="real@fake.email",
)

django.setup()

call_command("migrate", interactive=False)
