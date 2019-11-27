#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from setuptools import setup
except ImportError:
    print('Please install or upgrade setuptools or pip to continue')
    sys.exit(1)


def read(filename):
    path = Path(__file__).parent.joinpath(filename)
    with path.open('r', encoding='utf-8') as fh:
        content = fh.read()
    return content


long_description = '\n\n'.join([read('README.md'), read('AUTHORS.md'), read('CHANGES.md')])

requirements = ['stringparser', 'pyvisa>=1.8', 'pyyaml']

setup(name='PyVISA-sim',
      description='Simulated backend for PyVISA implementing TCPIP, GPIB, RS232, and USB resources',
      version='0.4.dev0',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Hernan E. Grecco',
      author_email='hernan.grecco@gmail.com',
      maintainer='Hernan E. Grecco',
      maintainer_email='hernan.grecco@gmail.com',
      url='https://github.com/pyvisa/pyvisa-sim',
      test_suite='pyvisa-sim.testsuite.testsuite',
      keywords='VISA GPIB USB serial RS232 TCPIP measurement acquisition simulator mock',
      license='MIT License',
      install_requires=requirements,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: MIT License',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Operating System :: MacOS :: MacOS X',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      packages=['pyvisa-sim',
                'pyvisa-sim.testsuite'],
      package_data={
          'pyvisa-sim': ['default.yaml']
      },
      platforms="Linux, Windows, Mac",
      use_2to3=False,
      zip_safe=False)
