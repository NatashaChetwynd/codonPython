from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='codonPython',
    version='0.2.2',
    license='BSD',
    packages=['codonPython', ],
    install_requires=requirements,
    author='NHS Digital DIS Team',
    author_email='paul.ellingham@nhs.net',
    url='https://digital.nhs.uk/data-and-information',
    description='This is a first attempt at how our package will work.'
)
