**EasyMIDI**
============

|docs|

A simple, easy to use algorithmic composition MIDI creator for Python, based on midiutil.

Creating a MIDI file can be as simple as this::

   from EasyMIDI import EasyMIDI,Track,Note,Chord,RomanChord
   from random import choice

   easyMIDI = EasyMIDI()
   track1 = Track("acoustic grand pino")  # oops

   c = Note('C', octave = 5, duration = 1/4, volume = 100)
   e = Note('E', 5)
   g = Note('G', 5)
   chord = Chord([c,e,g])  # a chord of notes C, E and G
   track1.addNotes([c, e, g, chord])

   # roman numeral chord, first inversion (defaults to key of C)
   track1.addNotes(RomanChord('I*', octave = 5, duration = 1))

   easyMIDI.addTrack(track1)
   easyMIDI.writeMIDI("output.mid")

**Installation**
================

EasyMIDI is only compatible with Python3. If you have `setuptools` for
Python 3, you can install the package by running `python3 setup.py install`
(use `sudo python3 setup.py install` on Linux or `python3 setup.py install --user`).
TODO PyPI - pip install support

**Documentation**
=================

Documentation can be found here: http://easymidi.readthedocs.io

.. |docs| image:: https://readthedocs.org/projects/easymidi/badge/
    :alt: Documentation Status
    :scale: 100%
    :target: https://easymidi.readthedocs.io
