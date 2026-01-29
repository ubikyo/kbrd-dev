from setuptools import setup, find_packages

setup(
    name="kbrd-dev",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "kivy",
    ],
    entry_points={
        "console_scripts": [
            "kbrd-dev=kbrd_dev.main:main",
        ]
    },
)