from setuptools import setup


package_version = '1.0.50'

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as req:
    requires = req.read().splitlines()

setup_params = dict(
    name='pysqream-blue',
    version=package_version,
    description='DB-API connector for SQream DB',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/SQream/pysqream-blue",
    author="SQream",
    author_email="info@sqream.com",
    packages=["pysqream_blue", "protos"],
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    keywords='database db-api sqream sqreamdbV2',
    python_requires='>=3.9',
    install_requires=requires
)

if __name__ == '__main__':
    setup(**setup_params)
