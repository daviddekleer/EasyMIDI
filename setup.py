from setuptools import setup, find_packages

with open('README.rst') as file:
    long_description = file.read()

setup(name='EasyMIDI',
      version='1.0',
      description='A simple, easy to use algorithmic composition MIDI creator.',
      author='David de Kleer',
      #author_email='daviddekleer) at )(*outlook . )com',
      license='MIT',
      url='https://github.com/daviddekleer/EasyMIDI',
      packages=['EasyMIDI', 'EasyMIDI/midiutil'],
      include_package_data = True,
      platforms='Platform Independent',
      classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Topic :: Multimedia :: Sound/Audio :: MIDI',
          ],
      keywords = 'Music MIDI Algorithmic Composition',
      download_url = 'https://github.com/daviddekleer/EasyMIDI/archive/1.0.tar.gz',
      long_description = long_description
)
