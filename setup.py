#!/usr/bin/pythonMenotexport (Mendeley-Note-Export) extracts and exports highlights, notes and PDFs from your Mendeley database

from distutils.core import setup

setup(name='Menotexport',
        version='1.4',
        description='Menotexport (Mendeley-Note-Export) extracts and exports highlights, notes and PDFs from your Mendeley database',
        author='Guangzhi XU',
        author_email='xugzhi1987@gmail.com',
        url='https://github.com/Xunius/Menotexport',
        packages=['lib'],
        scripts=['menotexport.py','menotexport-gui.py'],
        license='GPL-3'
        )


