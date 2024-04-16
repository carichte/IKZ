#!/usr/bin/env python
#from distutils.core import setup
#import os
from setuptools import setup


setup(
    name='IKZxray',
    version='0.1',
    description='Collection of libraries for IKZ.',
    author='Carsten Richter',
    author_email='carsten.richter@ikz-berlin.de',
    url='',
    packages = ['IKZ.xray',
                'IKZ.plot',
                'IKZ.process',
                ],
#    package_data = {
#       "IKZ": ["media/*"]},
#    entry_points={ #later
#        'console_scripts': [
#            'id01_microscope_contrast=id01lib.camtools:get_microscope_contrast',
#        ],
#    },
    install_requires=[
                      'numpy',
                      'xrayutilities',
                      'xmltodict',
                      'matplotlib',
                      'scipy',
                      'h5py',
                      #'silx>=0.7.0',
                      #'Pillow',
                      #'SpecClient',
                     ],
    #scripts = [],
    long_description = """
                        Collection of libraries for IKZ.
                     """
     )


