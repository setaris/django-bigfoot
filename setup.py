import sys

from setuptools import setup, find_packages

install_requires = [
    'django >= 1.4',
    'django-tables2 == 0.13'
]

setup(
    name = "django-bigfoot",
    version = '0.1',
    description = "A Django library for defining HTML building blocks (e.g.," +
        " forms, form fields, tables) that can be easily rendered into HTML.",
    url = "https://github.com/setaris/django-bigfoot",
    author = "Setaris",
    author_email = "support@setaris.com",
    packages = find_packages(),
    install_requires = install_requires,
)
