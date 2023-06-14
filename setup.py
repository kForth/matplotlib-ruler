#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("requirements.txt") as req_file:
    requirements = req_file.readlines()

test_requirements = []

setup(
    author="Kestin Goforth",
    author_email="kgoforth1503@gmail.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="TODO: Description",
    entry_points={},
    install_requires=requirements,
    extras_require=[],
    long_description=readme,
    include_package_data=True,
    keywords="matplotlib_ruler",
    name="matplotlib_ruler",
    packages=find_packages(include=["matplotlib_ruler", "matplotlib_ruler.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/kforth/matplotlib-ruler",
    version="0.1.0",
    zip_safe=False,
)
