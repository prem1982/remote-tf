from setuptools import setup, find_packages
from git import Repo
import os
repo = Repo(os.getcwd())


setup(
    name='cloud_oos_detection',
    version=repo.tags[-1].name,
    packages=find_packages(),
    setup_requires=[
        'setuptools',
        'setuptools-git',
        'wheel',
    ]
)
