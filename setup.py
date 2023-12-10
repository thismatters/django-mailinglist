import warnings

from setuptools import find_packages, setup

try:
    README = open("README.md").read() + "\n\n"
    README += open("CHANGELOG.md").read()
except:  # noqa: E722
    warnings.warn("Could not read README.md and/or CHANGELOG.md")
    README = None

version = __import__("mailinglist").__version__

setup(
    name="django-mailinglist",
    version=version,
    description=(
        "Django app for managing multiple mailing lists with both "
        "plaintext as well as HTML templates (facilitated by Markdown)."
    ),
    long_description=README,
    long_description_content_type="text/markdown",
    install_requires=[
        "Django>=3.2.0",
        "Markdown>=3.3.0",
        "django-enumfield>=3.0",
        "django-appconf>=1.0.0",
    ],
    author="Paul Stiverson",
    author_email="paul@thismatters.net",
    url="http://github.com/thismatters/django-mailinglist/",
    packages=find_packages(exclude=("tests", "test_project")),
    include_package_data=True,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
)
