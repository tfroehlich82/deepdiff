import os
import sys
from setuptools import setup

if sys.version_info.major == 2:  # pragma: no cover
    sys.exit('Python 2 is not supported anymore. The last version of DeepDiff that supported Py2 was 3.3.0')

# if you are not using vagrant, just delete os.link directly,
# The hard link only saves a little disk space, so you should not care
if os.environ.get('USER', '') == 'vagrant':
    del os.link

version = '5.5.0'


def get_reqs(filename):
    with open(filename, "r") as reqs_file:
        reqs = reqs_file.readlines()
    return reqs


reqs = get_reqs("requirements.txt")
cli_reqs = get_reqs("requirements-cli.txt")

with open('README.md') as file:
    long_description = file.read()


setup(name='deepdiff',
      version=version,
      description='Deep Difference and Search of any Python object/data.',
      url='https://github.com/seperman/deepdiff',
      download_url='https://github.com/seperman/deepdiff/tarball/master',
      author='Seperman',
      author_email='sep@zepworks.com',
      license='MIT',
      packages=['deepdiff'],
      zip_safe=True,
      test_suite="tests",
      include_package_data=True,
      tests_require=['mock'],  # 'numpy==1.11.2' numpy is needed but comes already installed with travis
      long_description=long_description,
      long_description_content_type='text/markdown',
      install_requires=reqs,
      python_requires='>=3.6',
      extras_require={
          "cli": cli_reqs,
      },
      classifiers=[
          "Intended Audience :: Developers",
          "Operating System :: OS Independent",
          "Topic :: Software Development",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: Implementation :: PyPy",
          "Development Status :: 5 - Production/Stable",
          "License :: OSI Approved :: MIT License"
      ],
      entry_points={
          'console_scripts': [
              'deep=deepdiff.commands:cli',
          ],
      },
      )
