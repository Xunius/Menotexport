'''Extract sticky notes and side-bar notes from documents in Mendeley.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-12 22:09:38.
'''

import tools

#-----------------Extract notes-----------------
def extractNotes(path,anno,verbose=True):
    '''Extract notes

    <path>: str, absolute path to a PDF file.
    <anno>: FileAnno obj, contains annotations in PDF.
    
    Return <nttexts>: list, Anno objs containing annotation info from a PDF.
                      Prepare to be exported to txt files.
    '''
    from extracthl import Anno

    notes=anno.notes
    meta=anno.meta
    nttexts=[]

    #----------------Loop through pages----------------
    if len(anno.ntpages)==0:
        return nttexts

    for pp in anno.ntpages:

        for noteii in notes[pp]:
            note_color=tools.color_labels.get(noteii['color'], noteii['color'])
            textjj=Anno(noteii['content'], ctime=noteii['cdate'],\
                    color=note_color,\
                    title=meta['title'],\
                    page=pp,citationkey=meta['citationkey'], note_author=noteii['author'],\
                    tags=meta['tags'])
            nttexts.append(textjj)

    return nttexts

