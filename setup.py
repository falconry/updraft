from setuptools import setup, find_packages

setup(
    name='updraft',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),
    install_requires=['falcon'],
    entry_points={
        'console_scripts': [
            'updraft = updraft.__main__:main'
        ]
    }
)
