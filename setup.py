from setuptools import find_packages, setup

NAME = "feast_custom_stores_demo"
REQUIRES_PYTHON = ">=3.7.0"

setup(
    name=NAME,
    description=open("README.md").read(),
    version="0.0.1",
    long_description_content_type="text/markdown",
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(include=["feast_custom_online_store"]),
    install_requires=[
        "mysql-connector-python",
        "feast==0.12.1"
    ],
    license="Apache",
)
