# FlameCens



FlameCens is an application written in Python for visualizing the musical expression of audio files. The application visualize dynamics and temporal deviation compared to score or another cover of the same song.


## Overview
FlameCens is an application for visualization of expressive music performance. It compares an audio file to its corresponding musical score (imported in MIDI format) or to another performance of the same song by another artist (also an audio file). The application displays a dynamically modified "flame" texture that changes size according to the dynamics and angle according to the temporal deviation of music, compared to the target file. The vertical axis shows the position of zero temporal deviation while the horizontal axis shows the temporal deviation in seconds.

In the FlamceCens-pitch alternation, the flame changes color according to the pitch of the current note. The alternation works only for monophonic music (polyphonic extention may be developed as future work)


## Usage

*python FlameCens.py file1 file2 artist1 artist2 title tuning*
