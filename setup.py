from pathlib import Path
from setuptools import find_packages
from setuptools import setup


version = "3.0.3.dev0"

long_description = (
    f"{Path('README.rst').read_text()}\n{Path('CHANGES.rst').read_text()}"
)

setup(
    name="plone.cachepurging",
    version=version,
    description="Cache purging support for Zope 2 applications",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    # Get more strings from
    # https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Plone",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: Core",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    keywords="plone cache purge",
    author="Plone Foundation",
    author_email="plone-developers@lists.sourceforge.net",
    url="https://pypi.org/project/plone.cachepurging",
    license="GPL version 2",
    packages=find_packages("src"),
    namespace_packages=["plone"],
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "setuptools",
        "plone.registry",
        "requests",
        "z3c.caching",
        "Zope",
        "zope.annotation",
        "zope.component",
        "zope.event",
        "zope.globalrequest",
        "zope.i18nmessageid",
        "zope.interface",
        "zope.schema",
        "zope.testing",
    ],
    extras_require={"test": []},
)
