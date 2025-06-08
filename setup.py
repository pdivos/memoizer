from setuptools import setup, find_packages

setup(
    name="memoizer",
    version="0.1.0",
    description="A lightweight memoization utility for Python",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Peter Divos",
    author_email="pdivos@gmail.com",
    url="https://github.com/pdivos/memoizer",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
