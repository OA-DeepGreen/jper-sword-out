from setuptools import setup, find_packages

setup(
    name = 'jper-sword-out',
    version = '1.1',
    packages = find_packages(),
    install_requires = [
        "esprit",
        "Flask~=3.0",
        "sword2"
    ],
    url = 'http://cottagelabs.com/',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'Consumes notifications from JPER and pushes them to repositories via swordv2',
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
