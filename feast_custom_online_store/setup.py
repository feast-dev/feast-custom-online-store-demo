from setuptools import setup

NAME = "feast-custom-stores-demo"
REQUIRES_PYTHON = ">=3.7.0"

setup(
    name="feast_custom_stores_demo",
    description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=REQUIRES_PYTHON,
    install_requires=[
        "mysql-connector-python",
        "feast==0.12.1"
    ],
    license="Apache",
)
