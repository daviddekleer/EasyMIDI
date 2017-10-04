#
# Name:        EasyMIDI.py
# Purpose:     Easy MIDI manipulation for algorithmic composition
#
# Author:      David de Kleer <daviddekleer) at )(*outlook . )com>
#
# Created:     04-07-2015
# Copyright:   (c) 2015-2017 David de Kleer
# License:     Please see LICENSE.txt for the terms under which this
#              software is distributed.
#
# A simple, easy to use algorithmic composition MIDI creator for Python, based on midiutil.
#
# Creating a MIDI file can be as simple as this::
#
#    from EasyMIDI import EasyMIDI,Track,Note,Chord,RomanChord
#    from random import choice
#
#    easyMIDI = EasyMIDI()
#    track1 = Track("acoustic grand pino")  # oops
#
#    c = Note('C', octave = 5, duration = 1/4, volume = 100)
#    e = Note('E', 5)
#    g = Note('G', 5)
#    chord = Chord([c,e,g])  # a chord of notes C, E and G
#    track1.addNotes([c, e, g, chord])
#
#    # roman numeral chord, first inversion (defaults to key of C)
#    track1.addNotes(RomanChord('I*', octave = 5, duration = 1))
#
#    easyMIDI.addTrack(track1)
#    easyMIDI.writeMIDI("output.mid")
#


from copy import deepcopy
from difflib import SequenceMatcher
import os

from .midiutil.MidiFile import MIDIFile


# MUSIC THEORY (MUSICTHEORY) #


class MusicTheory():
    """MusicTheory contains some helpful music theory data, like
       the major and minor scales based on the circle of fifths."""

    def __init__(self):
        # all notes
        self.notes = ["A", "A#", "B", "C", "C#", "D", "D#",
                      "E", "F", "F#", "G", "G#"]
        # for translating sharps to flats (so you can also ask for flat keys)
        self.sharpFlatTrans = {"C#": "Db", "D#": "Eb", "F#": "Gb",
                               "G#": "Ab", "A#": "Bb"}

    @property
    def majorScales(self):
        """Builds the scales for major keys."""

        # the circle of fifths for major keys
        majKeys = {
            "C":  [],
            "G":  ["F"],
            "D":  ["F", "C"],
            "A":  ["F", "C", "G"],
            "E":  ["F", "C", "G", "D"],
            "B":  ["F", "C", "G", "D", "A"],
            "F#": ["F", "C", "G", "D", "A", "E"],
            "C#": ["F", "C", "G", "D", "A", "E", "B"],
            "G#": ["B", "E", "A", "D"],
            "D#": ["B", "E", "A"],
            "A#": ["B", "E"],
            "F":  ["B"]
        }

        # determine all the major scale notes
        majScales = {}
        for key in majKeys:

            # determine the indices of the notes on which sharps are based
            sharpBaseIdx = []
            for sharpBaseNote in majKeys[key]:
                sharpBaseIdx.append(self.notes.index(sharpBaseNote))

            # determine a major scale
            keyNotes = []
            i = 0
            while i < len(self.notes):
                if i in sharpBaseIdx:
                    i += 1
                    # keys with flats are special
                    if key in ["G#", "D#", "A#", "F"]:
                        keyNotes.append(self.notes[i-2])
                    else:
                        keyNotes.append(self.notes[i])
                    if self.notes[i] not in ["C", "F"]:
                        i += 1
                elif self.notes[i] in ["B", "E"]:
                    keyNotes.append(self.notes[i])
                    i += 1
                else:
                    keyNotes.append(self.notes[i])
                    i += 2

            majScales[key] = keyNotes

        # start major scales from their root notes
        for key, keyNotes in majScales.items():
            rootIndex = keyNotes.index(key)
            majScales[key] = keyNotes[rootIndex:] + keyNotes[:rootIndex]

        for sharp, flat in self.sharpFlatTrans.items():
            majScales[flat] = majScales[sharp]

        return majScales

    @property
    def minorScales(self):
        """Builds the scales for minor keys."""
        minScales = {}
        for key in self.notes:
            keyNotes = self.majorScales[key][:]  # copy to solve referencing
            # the parallel minor starts on the 6th note of the major scale
            rootIndex = (keyNotes.index(key)+5) % 7
            # the 7th note of the minor scale gets a sharp
            minorPos = (rootIndex+6) % 7
            minorIndex = self.notes.index(keyNotes[minorPos])+1
            minorNote = self.notes[minorIndex % 12]
            keyNotes[minorPos] = minorNote
            # translate major keys to minor parallel
            majMinTrans = {"C": "A", "G": "E", "D": "B",
                           "A": "F#", "E": "C#", "B": "G#",
                           "F#": "D#", "C#": "A#", "G#": "F",
                           "D#": "C", "A#": "G", "F": "D"}
            minScales[majMinTrans[key]] = keyNotes

            # start minor scales from their root notes
            for key, keyNotes in minScales.items():
                rootIndex = keyNotes.index(key)
                minScales[key] = keyNotes[rootIndex:] + keyNotes[:rootIndex]

        for sharp, flat in self.sharpFlatTrans.items():
            minScales[flat] = minScales[sharp]

        return minScales

    def getMajorScales(self):
        """Get the scales for major keys.

        :returns: A dict of major scales (ex. 'C' : ['C', 'D', 'E', ...]).
        :rtype: dict

        """
        return self.majorScales

    def getMinorScales(self):
        """Get the scales for minor keys.

        :returns: A dict of minor scales (ex. 'C' : ['C', 'D', 'E', ...]).
        :rtype: dict

        """
        return self.minorScales


# MIDI MANAGEMENT (EASYMIDI AND TRACK) #


class EasyMIDI:
    """EasyMIDI handles MIDI files with the help of midiutil."""

    def __init__(self):
        """Initialize a midiutil MIDIFile object."""
        self.midFile = MIDIFile()
        self.channel = 0
        self.track = 0

    def __midNote(self, note):
        """Returns the MIDI number of the note name and octave in a Note object.

        :param note: A Note object.
        :type note: :class:`Note`
        :returns: MIDI number of the Note.
        :rtype: int

        """

        # note indices stored in a dict: some sharp/flat notes are the same
        notes = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
                 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
                 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}

        name = note.getName()
        octave = note.getOctave()
        midNote = notes[name] + (octave + 1) * 12

        return midNote

    def addTracks(self, tracks):
        """Add multiple tracks to the midiutil MIDIFile object.

        :param tracks: A list of tracks.
        :type tracks: list of :class:`Track` objects

        """
        for track in tracks:
            self.addTrack(track)

    def addTrack(self, track):
        """Add a single track/channel to the midiutil MIDIFile object.

        :param track: A Track object.
        :type track: :class:`Track`

        """
        if self.channel > 15:
            print("Sorry, can't add more MIDI tracks because all "
                  "16 channels have been occupied.")
            return

        self.channel += 1

        noteList = track.getNotes()
        instrument = track.getInstrument()
        tempo = track.getTempo()
        time = 0

        self.midFile.addTempo(self.track, time, tempo)
        self.midFile.addProgramChange(self.track, self.channel,
                                      time, instrument)

        for note in noteList:
            dur = note.getDuration()
            # convert note duration to MIDI representation
            # example: a quarter note (1/4) is 1 in MIDI
            dur *= 4
            vol = note.getVolume()

            if type(note) == Note:
                noteName = note.getName()
                if noteName != "R":  # skip rests
                    self.midFile.addNote(self.track, self.channel,
                                         self.__midNote(note),
                                         time, dur, vol)
            elif type(note) == Chord or type(note) == RomanChord:
                for chordNote in note.getNotes():
                    noteName = chordNote.getName()
                    if noteName != "R":  # skip rests
                        self.midFile.addNote(self.track, self.channel,
                                             self.__midNote(chordNote),
                                             time, dur, vol)
            time += dur

    def writeMIDI(self, path):
        """Write the MIDI file to the disk.

        :param path: The path to store the MIDI file at (ex. output.mid).
        :type path: str

        """
        with open(path, 'wb') as binfile:
            self.midFile.writeFile(binfile)


class Track:
    """Simple Track class which keeps the list of Notes/Chords, the
       instrument and the tempo. To be used with :func:`addTrack` or
       :func:`addTracks` in :class:`EasyMIDI`."""

    def __init__(self, instrument, tempo=120):
        """Initializes a Track object.

        :param instrument: A midi instrument name.
        :type instrument: str
        :param tempo: The tempo of the track.
        :type tempo: int

        """
        self.noteList = []

        # create a dict of midi instruments and their corresponding numbers
        self.instrumentDict = {}
        path = os.path.join(os.path.dirname(__file__), 'data/instruments.tsv')
        with open(path) as instruments:
            for i in instruments:
                midiNr, instr = i.split('\t')
                self.instrumentDict[instr.strip().lower()] = int(midiNr)

        self.instrument = self.matchInstrument(instrument)
        self.tempo = tempo

    def addNotes(self, notes):
        """Add a list of Notes or Chords to the Track.

        :param notes: The list of Notes or Chords, or single Notes or Chords.
        :type notes: :class:`Note` or :class:`Chord` in list or single objects

        """
        if type(notes) == list:  # it's a list of Notes or Chords
            self.noteList.extend(notes)
        else:  # single note or Chord
            self.noteList.append(notes)

    def addNote(self, note):
        """Is identical to :func:`addNotes`."""
        self.addNotes(note)

    def addChord(self, chord):
        """Is identical to :func:`addNotes`."""
        self.addNotes(chord)

    def addChords(self, chords):
        """Is identical to :func:`addNotes`."""
        self.addNotes(chords)

    def matchInstrument(self, description):
        """(Fuzzy) matches instrument descriptions to MIDI program numbers.

        :param description: The instrument description (ex. acoustic grand).
        :type description: str

        """
        description = description.strip().lower()
        # the easy case, description is equal to a MIDI instrument name
        if description in self.instrumentDict:
            # instrument numbers start at 0!
            return self.instrumentDict[description]-1
        # hard case, fuzzy matching
        ratio = 0
        bestMatch = 0
        # go throug all instruments, try to match their substrings with the
        # best matching substrings of the given description
        for instrumentName in self.instrumentDict:
            r = 0
            for subStr in description.split():
                bestRat = 0
                for subStr2 in instrumentName.split():
                    if subStr == subStr2:
                        bestRat = 1
                        break
                    newRat = SequenceMatcher(None, subStr, subStr2).ratio()
                    if newRat > bestRat:
                        bestRat = newRat
                r += bestRat

            if r > ratio:
                ratio = r
                bestMatch = self.instrumentDict[instrumentName]

        for instrumentName in self.instrumentDict:
            if self.instrumentDict[instrumentName] == bestMatch:
                print('Warning: The instrument "{}" isn\'t available '
                      'as MIDI program name. Selected "{}" instead.'
                      .format(description, instrumentName))

        return bestMatch-1  # instrument numbers start at 0!

    def getNotes(self):
        """Returns a copy of the notes of this Track.

        :returns: A list of Chord and Note objects.
        :rtype: list of :class:`Chord` or :class:`Note`.

        """
        return deepcopy(self.noteList)

    def getTempo(self):
        """Returns the tempo of this Track.

        :returns: The tempo.
        :rtype: int

        """
        return self.tempo

    def getInstrument(self):
        """Returns the instrument of this Track.

        :returns: The instrument.
        :rtype: str

        """
        return self.instrument


# MUSIC MANAGEMENT (NOTE, CHORD AND ROMANCHORD) #


class Note:
    """The Note class contains musical notes and their properties,
       like octave, duration and volume."""

    def __init__(self, name, octave=4, duration=1/4, volume=100):
        """Initializes a Note object.

        :param name: The name of the note (ex. C).
        :type name: str
        :param octave: The octave of the note (1-7).
        :type octave: int
        :param duration: The duration of the note (ex. 1/4 is quarter note).
        :type duration: float or int
        :param volume: The volume of the note (0 to 100)
        :type volume: int

        """
        allowedNames = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#',
                        'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'R']
        # check validity of note name
        if name not in allowedNames:
            raise ValueError("The provided note name is not a valid music "
                             "note name. Please use C, C#, Db, D, D#, "
                             "Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, "
                             "B, or R (rest).")
        self.name = name
        self.duration = duration
        # check validity of octave height
        if octave < 1:
            raise ValueError("The provided octave is too low. Please select "
                             "an octave between 1 and 7 (including).")
        elif octave > 8:
            raise ValueError("The provided octave is too high. Please select "
                             "an octave between 1 and 7 (including).")
        self.octave = octave
        self.volume = volume

    def getName(self):
        """Returns the name of the note.

        :returns: Current name (ex. C).
        :rtype: str

        """
        return self.name

    def getDuration(self):
        """Returns the duration of the note.

        :returns: Current duration (ex. 1/4).
        :rtype: float or int

        """
        return self.duration

    def getOctave(self):
        """Returns the octave of the note.

        :returns: Current octave (ex. 4).
        :rtype: int

        """
        return self.octave

    def getVolume(self):
        """Returns the volume of the note.

        :returns: Current volume (ex. 80).
        :rtype: int

        """
        return self.volume

    def setName(self, name):
        """Sets the name of the note to name.

        :param name: The new name (ex. C).
        :type name: str

        """
        self.name = name

    def setDuration(self, duration):
        """Sets the duration of the note to duration.

        :param duration: The new duration (ex. 1/4).
        :type duration: float or int

        """
        self.duration = duration

    def setOctave(self, octave):
        """Sets the octave of the note to octave.
        :param octave: The new octave (1-7).
        :type octave: int
        """
        self.octave = octave

    def setVolume(self, volume):
        """Sets the volume of the note to volume.

        :param volume: The new volume (0-100).
        :type volume: int

        """
        self.volume = volume

    def __eq__(self, other):
        """For checking if two Notes are equal to each other."""
        if isinstance(other, Note):
            return self.name == other.getName() and \
                self.duration == other.getDuration() and \
                self.octave == other.getOctave() and \
                self.volume == other.getVolume()
        return NotImplemented

    def __ne__(self, other):
        """For checking if two Notes are not equal to each other."""
        return not self.__eq__(other)

    def __hash__(self):
        """For checking if two Notes are not equal to each other."""
        return hash((self.name, self.octave, self.volume))


class Chord:
    """The Chord is a simple class that contains lists of Notes."""

    def __init__(self, noteList=[]):
        """Initializes a Chord object.

        :param noteList: A list of Notes that should form a chord.
        :type noteList: list of :class:`Note`

        """
        self.noteList = self.__orderedSet(noteList)

    def getNotes(self):
        """
        Gets the Notes of the chord.

        :returns: The list of Notes of the Chord.
        :rtype: list of :class:`Note`

        """
        return deepcopy(self.noteList)

    def __orderedSet(self, seq):
        """Makes sure the Chord contains no duplicate Notes and that the
           Note order keeps preserved."""
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    def getDuration(self):
        """Returns the duration of the longest Chord note.

        :returns: The duration.
        :rtype: float or int

        """
        highestDur = 0
        for note in self.noteList:
            curDur = note.getDuration()
            if curDur > highestDur:
                highestDur = curDur
        return highestDur

    def getVolume(self):
        """Returns the volume of the loudest Chord note.

        :returns: The volume.
        :rtype: int

        """
        highestVol = 0
        for note in self.noteList:
            curVol = note.getVolume()
            if curVol > highestVol:
                highestVol = curVol
        return highestVol

    def setNotes(self, noteList):
        """Sets the Chord notes to the Notes in noteList.

        :param noteList: A list of notes that should form a chord.

        """
        self.noteList = self.__orderedSet(noteList)

    def setDuration(self, duration):
        """Sets the duration of the note to duration.

        :param duration: The new duration (ex. 1/4).
        :type duration: float or int

        """
        for note in self.noteList:
            note.setDuration(duration)

    def setOctave(self, octave):
        """Sets the octave of the note to octave.

        :param octave: The new octave (1-7).
        :type octave: int

        """
        self.octave = octave
        for note in self.noteList:
            note.setOctave(octave)

    def setVolume(self, volume):
        """Sets the volume of the note to volume.

        :param volume: The new volume (0-100).
        :type volume: int

        """
        for note in self.noteList:
            note.setVolume(volume)

    def addNote(self, note):
        """Adds a note to the Chord.

        :param note: The note to add.
        :param type: :class:`Note`

        """
        self.noteList.append(note)
        self.noteList = self.__orderedSet(self.noteList)

    def removeNote(self, note):
        """Removes a note from the Chord.

        :param note: The note to remove.
        :param type: :class:`Note`

        """
        self.noteList.remove(note)


class RomanChord(Chord):
    """The RomanChord class supports Roman chord numerals for creating
       chord progressions in a relatively easy way. It's also possible
       to customize the numerals with intervals or signs and inversions:

       * I6, I7: add 6th or 7th note interval to I chord
       * Isus2, Isus4: the suspended chords relative to the I chord
       * I-, I+: Diminished and augmented I chord
       * Imaj7, Imin7, Idom7: major, minor and dominant 7th chord from I
       * I*, I**: first and second inversion of the I chord, can be
         combined with the other customizations (ex. Isus2**)

       Full code example::

          from EasyMIDI import *
          mid = EasyMIDI()
          track = Track('acoustic grand')
          for numeral in ['I', 'IV', 'V', 'I']:
             track.addChord(RomanChord(numeral))
          mid.addTrack(track)
          mid.writeMIDI('output.mid')

    """

    def __init__(self, numeral='I', octave=4, duration=1/4,
                 key='C', major=True, volume=100):
        """Initializes a RomanChord.

        :param numeral: A roman numeral (I, II, III, IV, V, VI or VII)
        :type numeral: str
        :param octave: The octave of the RomanChord (1-7).
        :type octave: int
        :param duration: The duration of the RomanChord (ex. 1/4).
        :type duration: float or int
        :param key: The key of the RomanChord (ex. Ab or G# or D).
        :type key: str
        :param major: If true, use major scale. If false, use minor scale.
        :type major: bool
        :param volume: The volume of the RomanChord (0-100).
        :type volume: int

        """

        # Some input from music theory
        self.theory = MusicTheory()
        self.notes = self.theory.notes
        self.majorScales = self.theory.getMajorScales()
        self.minorScales = self.theory.getMinorScales()

        # the first letters of the numeral must be capital (roman number part)
        self.numeral = ''
        for c in numeral:
            if c.isupper():
                self.numeral += c
            else:
                break

        self.allowedNumerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
        if self.numeral not in self.allowedNumerals:
            raise ValueError("The provided Roman numeral is not valid. Please "
                             "use I, II, III, IV, V, VI or VII.")
        # remove the numeral part from numeral to see if we have
        # something left (like numbers for extra intervals)
        self.numeralRest = numeral.replace(self.numeral, '')

        Chord.__init__(self)

        self.key = key
        if major:
            self.scale = self.majorScales[self.key]
        else:  # minor
            self.scale = self.minorScales[self.key]
        self.major = major

        self.duration = duration
        self.octave = octave  # octave is the octave of the ROOT note
        self.volume = volume
        self._numeralToChord()

    def _numeralToChord(self):
        """Converts a roman numeral chord to Notes to add to this Chord."""

        self.noteList = []  # empty old notelist

        intervals = [1, 3, 5]  # default chord

        # look at the "customizations" of the numeral
        inversion = 0
        numeralRest = self.numeralRest
        if numeralRest:
            try:
                if '*' in str(numeralRest):  # * is inversion sign
                    inversion = numeralRest.count('*')
                    # remove the stars
                    numeralRest = numeralRest.replace('*', '')
                # try to parse what's left as int
                numeralRest = int(numeralRest)
            except ValueError:
                if numeralRest == "sus2":
                    intervals = [1, 2, 5]
                elif numeralRest == "sus4":
                    intervals = [1, 4, 5]
                elif numeralRest == "dom7":  # dominant 7th
                    # seventh half step down
                    intervals.append('7-')
                elif numeralRest == "maj7":  # major seventh
                    intervals.append(7)
                elif numeralRest in ["min7", "m7"]:  # minor seventh
                    # third and seventh half step down
                    intervals = [1, '3-', 5, '7-']
                elif numeralRest == "-":  # diminished
                    # third and fifth half step down
                    intervals = [1, '3-', '5-']
                elif numeralRest == "+":  # augmented
                    # fifth half step up
                    intervals = [1, 3, '5+']

            # check if numeralRest is an int and that it's between 1 and 14
            if isinstance(numeralRest, int):
                if numeralRest > 14:
                    raise ValueError("The provided octave chord numeral "
                                     "interval is too high. Please select "
                                     "one between 1 and 14 (including), "
                                     "like V1 or V14.")
                if numeralRest < 1:
                    raise ValueError("The provided octave chord numeral "
                                     "interval is too low. Please select one "
                                     "between 1 and 12 (including), like V1 "
                                     "or V14.")
                intervals.append(numeralRest)

        # determine the first note
        startIdx = self.allowedNumerals.index(self.numeral)
        startNote = self.scale[startIdx]
        # now go through all the intervals
        for interval in intervals:
            note, octave = self._intervalNote(startNote, interval)
            self.addNote(Note(note, octave, self.duration, self.volume))

        # add inversions
        if inversion < 0:  # inversion inpossible
            raise ValueError("Negative inversions are not possible.")
        elif inversion > 0:  # inversion amount is OK
            for i in range(inversion):
                lenBefore = len(self.noteList)
                lenAfter = 0
                # there are special cases like the chord C-E-G-C, which the
                # algorithm normally converts to E-G-C (duplicate C), so the
                # length 3 (lenAfter) needs to become 4 (lenBefore) again
                while (lenAfter < lenBefore):
                    # grab and copy the first note
                    firstNote = deepcopy(self.noteList[0])
                    # grab first note octave
                    octave = firstNote.getOctave()
                    # move first note up 1 octave
                    firstNote.setOctave(octave + 1)
                    # remove old first note
                    if lenAfter == 0:
                        self.noteList = self.noteList[1:]
                    # add new first note
                    self.addNote(firstNote)
                    lenAfter = len(self.noteList)

    def _intervalNote(self, startNote, interval):
        """Returns the note and octave of an interval given
           the root and the interval."""

        # look if the interval contains a + or - (half step up/down)
        halfStepUp = False
        halfStepDown = False
        # try to parse an int
        try:
            interval = int(interval)
        except ValueError:  # means we have a + or -
            if '-' in interval:
                interval = interval.replace('-', '')
                halfStepDown = True
            elif '+' in interval:
                interval = interval.replace('+', '')
                halfStepUp = True
            else:  # something strange going on
                raise ValueError("Invalid interval.")
            interval = int(interval)

        # find the note
        if interval > 14:  # not allowed
            return False
        startIdx = self.scale.index(startNote)
        noteIdx = ((startIdx + (interval-1)) % 7)
        note = self.scale[noteIdx]

        # find the octave switch sign position
        octaveSignIdx = 0  # this indicates that we have to increase the octave
        octaveSigns = ['C', 'C#', 'D']
        for octaveSign in octaveSigns:  # choose first sign present in scale
            if octaveSign in self.scale:
                octaveSignIdx = self.scale.index(octaveSign)
                break

        # how many notes were before the scale, starting from the octave sign?
        if octaveSignIdx > 0:  # no compensation for octave sign pos if it's 0
            startIdx += len(self.scale[octaveSignIdx:])

        # find the octave
        rootOffset = startIdx + (interval-1)
        octave = (rootOffset // 7) + self.octave

        # add or subtract a half step if applicable
        if halfStepUp:
            note = self.notes[(self.notes.index(note) + 1) % 12]
            if note == 'C':  # advance to next octave
                octave += 1
        elif halfStepDown:
            note = self.notes[(self.notes.index(note) - 1) % 12]
            if note == 'B':  # go back to previous octave
                octave -= 1

        return note, octave

    def setKey(self, key, major=True):
        """Sets the key of the RomanChord, optionally changes scales.

        :param key: The key of the RomanChord (ex. Ab or G# or D).
        :type key: str
        :param major: If true, use major scale. If false, use minor scale.
        :type major: bool

        """
        self.key = key
        if major:  # major
            self.scale = self.majorScales[self.key]
        else:  # minor
            self.scale = self.minorScales[self.key]
        self.major = major
        # renew the chord notes
        self._numeralToChord()

    def getNumeral(self):
        """Returns the numeral of the RomanChord.

        :returns: The numeral.
        :rtype: str

        """
        return self.numeral


# DEMO (A SIMPLE SONG WITHIN 40 LINES OF CODE) #


if __name__ == "__main__":

    from random import choice

    mid = EasyMIDI()
    track1 = Track('acoustic grand')
    track2 = Track('acoustic grand')

    melodyMeasures = 7
    numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
    key = choice(MusicTheory().notes)

    # melody measures
    for i in range(melodyMeasures):
        chordNr = choice(numerals)
        chord = RomanChord(chordNr + '8', duration=1/4, key=key, octave=3)
        track1.addChord(chord)
        for i in range(3):
            chordNr += '*'
            chord_inv = RomanChord(chordNr + '8', duration=1/4,
                                   key=key, octave=2)
            track1.addChord(chord_inv)
        for j in range(16):
            notes = chord.getNotes()
            note = choice(notes)
            note.setDuration(1/16)
            track2.addNote(note)

    # ending measures
    chordName = 'I8'
    for i in range(7):
        chordName += '*'
        chord = RomanChord(chordName, duration=1/16, key=key, octave=2)
        for note in chord.getNotes():
            track2.addNote(note)
    track2.addChord(RomanChord('I8', duration=1, key=key))

    mid.addTracks([track1, track2])
    mid.writeMIDI('output.mid')
