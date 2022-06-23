# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from pathlib import Path

sys.path.insert(0, Path(__file__).parents[2].resolve().as_posix())
sys.path.insert(0, (Path(__file__).parents[2].resolve() / "src").as_posix())
print(sys.path)

# -- Project information -----------------------------------------------------

project = "SRAM Reliability Platform"
copyright = "2022, Sergio Vinagrero Gutierrez"
author = "Sergio Vinagrero Gutierrez"

# The full version, including alpha/beta/rc tags
release = "0.1.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


numfig = True
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"
# html_theme = "press"
# html_theme = "tima_sphinx_theme"

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = "description"

# Don't show class signature with the class' name.
autodoc_class_signature = "separated"

html_logo = "logo.svg"

html_theme_options = {
    "show_nav_level": 4,
    "navigation_depth": 6,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/servinagrero/SRAMPlatform.git",
            "icon": "fab fa-github-square",
            "type": "fontawesome",
        }
    ],
}
pygments_style = "sas"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = [
    'css-style.css',
]

html_style = 'mystyle.css'
