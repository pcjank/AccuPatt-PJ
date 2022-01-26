"""
This is a setup.py script generated by py2applet

Usage:
    python setup.py py2app
"""

import sys
from setuptools import setup

DATA_FILES = [('resources',['resources/AgAircraftData.xlsx','resources/edit-alt-512.webp','resources/editCardList.ui','resources/editSpectrometer.ui','resources/editSpreadFactors.ui','resources/editStringDrive.ui','resources/editThreshold.ui','resources/loadCards.ui','resources/mainWindow.ui','resources/passManager.ui','resources/readString.ui','resources/refresh.png','resources/seriesInfo.ui','resources/schema.sql','resources/illini.icns'])]
OPTIONS = {
    'iconfile':'./resources/illini.icns',
    'plist': {'CFBundleShortVersionString':'2.0.1',}
}

if sys.platform == 'darwin':
    extra_options = dict(
        setup_requires=['py2app'],
        app=['./accupatt/__main__.py'],
        options={'py2app': OPTIONS}
    )
elif sys.platform == 'win32':
    extra_options = dict(
        setup_requires=['py2exe'],
        app = ['./accupatt/__main__.py'],
    )
setup(
    name='AccuPatt',
    version='2.0.0',
    data_files=DATA_FILES,
    **extra_options
)
