from setuptools import setup

setup(
    name="aio-feedfinder2",
    version='0.1.0',
    url="https://github.com/sergei-maertens/feedfinder2",
    license="MIT",
    author="Sergei Maertens, Dan Foreman-Mackey",
    author_email="sergeimaertens@gmail.com, foreman.mackey@gmail.com",
    install_requires=[
        "six",
        "aiohttp",
        "beautifulsoup4",
    ],
    description="Find the feed URLs for a website.",
    long_description=open("README.rst").read(),
    py_modules=["feedfinder2"],
    classifiers=[
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
