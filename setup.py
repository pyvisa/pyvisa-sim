#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import sys
    reload(sys).setdefaultencoding("UTF-8")
except:
    pass


try:
    from setuptools import setup
except ImportError:
    print('Please install or upgrade setuptools or pip to continue')
    sys.exit(1)


import codecs


def read(filename):
    return codecs.open(filename, encoding='utf-8').read()


long_description = '\n\n'.join([read('README'),
                                read('AUTHORS'),
                                read('CHANGES')])

__doc__ = long_description

requirements = ['stringparser', 'pyvisa>1.5', 'pyyaml']

setup(name='PyVISA-sim',
      description='Simulated backend for PyVISA implementing TCPIP, GPIB, RS232, and USB resources',
      version='0.1',
      long_description=long_description,
      author='Hernan E. Grecco',
      author_email='hernan.grecco@gmail.com',
      maintainer='Hernan E. Grecco',
      maintainer_email='hernan.grecco@gmail.com',
      url='https://github.com/hgrecco/pyvisa-sim',
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
        ],
      packages=['pyvisa-sim', 
                'pyvisa-sim.testsuite'],
      package_data={
          'pyvisa-sim': ['default.yaml']
      },
      platforms="Linux, Windows,Mac",
      use_2to3=False,
      zip_safe=False)
