#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
import sys

try:
    from setuptools import setup
except ImportError:
    print('Please install or upgrade setuptools or pip to continue')
    sys.exit(1)


def read_content(filename):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
    with open(path, 'r') as fh:
        content = fh.read()
    return content


long_description = '\n\n'.join([read_content('README.rst'),
                                read_content('AUTHORS.rst'),
                                read_content('CHANGES.rst')])

install_requires = [
    'enum34 ; python_version < "3"',
    'pyvisa>=1.6',
    'PyYAML',
    'stringparser',
]

tests_require = [
    'coverage',
    'importlib-metadata ; python_version < "3.8"',
    'more-itertools',
    'pytest',
    'pytest-cov',
]

setup(
    name='PyVISA-sim',
    description='Simulated backend for PyVISA implementing TCPIP, GPIB, RS232, and USB resources',
    version='0.4.dev0',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='Hernan E. Grecco',
    author_email='hernan.grecco@gmail.com',
    maintainer='Hernan E. Grecco',
    maintainer_email='hernan.grecco@gmail.com',
    url='https://github.com/pyvisa/pyvisa-sim',
    keywords='VISA GPIB USB serial RS232 TCPIP measurement acquisition simulator mock',
    license='MIT License',
    install_requires=install_requires,
    extras_require={
        'test': tests_require,
    },
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    packages=['pyvisa-sim',
              'pyvisa-sim.testsuite'],
    package_data={
        'pyvisa-sim': ['default.yaml']
    },
    platforms="Linux, Windows, Mac",
    use_2to3=False,
    zip_safe=False
)
