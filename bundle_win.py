import os
import sys
import PyInstaller.__main__

if sys.platform == 'win32':
    PyInstaller.__main__.run([
        './accupatt/__main__.py',
        '--name=AccuPatt',
        '--windowed',
        '--exclude-module=tkinter'
        f'--add-data=../../resources{os.pathsep}resources',
        '--distpath=./dist/win/dist',
        '--specpath=./dist/win',
        '--workpath=./dist/win/build'
        ])