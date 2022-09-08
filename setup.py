from setuptools import setup, find_packages
from pysqreamV2.globals import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as req:
    requires = req.read().split('\n')[:-1]

setup_params = dict(
    name =          'pysqreamV2',
    version =       __version__,
    description =   'DB-API connector for SQream DB', 
    long_description = long_description,
    url = "https://github.com/SQream/pysqream",
    author = "SQream",
    author_email = "info@sqream.com",
    packages = find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    keywords = 'database db-api sqream sqreamdbV2',
    python_requires = '>=3.6.5',
    install_requires=requires
)

if __name__ == '__main__':
    setup(**setup_params)