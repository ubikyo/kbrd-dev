from setuptools import setup, find_packages

setup(
    name="kbrd-dev",
    version="1.0.0",

    package_dir={"": "src"},
    packages=find_packages(where="src"),

    entry_points={
        "console_scripts": [
            "kbrd-dev = kbrd_dev.app:main",
        ],
    },
)