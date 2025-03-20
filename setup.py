from setuptools import setup, find_packages

setup(
    name="verification_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "discord.py>=2.0.0",
        "aiohttp>=3.8.0",
        "pytz>=2021.3",
        "python-dotenv>=0.19.0",
        "pyyaml>=6.0",
    ],
) 