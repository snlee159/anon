from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.readlines()
  
long_description = 'Package for automating video \
    anonymization both in the image and audio.'

setup(
    name ='vid_anon',
    version ='1.0.0', 
    author ='Sam Lee',
    author_email ='samanthanlee7@gmail.com',
    url ='https://github.com/snlee159/vid_anon',
    description ='Video anonymization tool',
    long_description = long_description,
    long_description_content_type ="text/markdown",
    license ='MIT',
    packages = find_packages(),
    entry_points ={
        'console_scripts': [
            'vid_anon = app:main'
        ]
    },
    classifiers =[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords ='video python package snlee anonymization anon',
    install_requires = requirements,
    zip_safe = False
)