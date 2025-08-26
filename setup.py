from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="azul-game",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python implementation of the Azul board game",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/azul-game",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.21.0',
    ],
    entry_points={
        'console_scripts': [
            'azul=azul.__main__:main',
        ],
    },
)
