from setuptools import setup, find_packages

setup(name='cheshire',
      version='0.0.1',
      description='Python wrapper for ASO tools',
      url='https://github.com/xyla-io/cheshire',
      author='Xyla',
      author_email='gklei89@gmail.com',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          "python-decouple",
          "pandas",
          "requests",
          "tqdm",
          "fire",
      ],
      zip_safe=False)
