from setuptools import setup

setup(name='tomcru_jerry',
      version='0.1.4',
      description='General purpose web library',
      url='https://github.com/dkgs/tomcru-jerry',
      author='oboforty',
      author_email='rajmund.csombordi@hotmail.com',
      license='MIT',
      zip_safe=False,
      package_dir={'': 'src'},
      install_requires=[
          'bcrypt',
      ])
