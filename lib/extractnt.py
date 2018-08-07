'''Extract sticky notes and side-bar notes from documents in Mendeley.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-12 22:09:38.
Update time: 2018-08-06 21:42:56.
'''

import math
import tools
from annotation_template import MAX_ASSOCIATE_DIST

#-----------------Extract notes-----------------
def extractNotes(path,anno,verbose=True):
    '''Extract notes

    <path>: str, absolute path to a PDF file.
    <anno>: FileAnno obj, contains annotations in PDF.
    
    Return <nttexts>: list, Anno objs containing annotation info from a PDF.
                      Prepare to be exported to txt files.
    '''
    from extracthl2 import Anno

    notes=anno.notes
    meta=anno.meta
    nttexts=[]
    authors=tools.getAuthorList(anno.meta)

    if len(anno.ntpages)==0:
        return nttexts

    #----------------Loop through pages----------------
    for pp in anno.ntpages:
        for noteii in notes[pp]:
            textjj=Anno(noteii['content'], ctime=noteii['cdate'],\
                    title=meta['title'],\
                    page=pp,
                    author=authors,
                    citationkey=meta['citationkey'],
                    note_author=anno.meta['user_name'],\
                    tags=meta['tags'],
                    bbox=noteii['rect'],
                    path=path,
                    isgeneralnote=noteii['isgeneralnote'])
            nttexts.append(textjj)

    #----------------Number notes----------------
    for ii,ntii in enumerate(nttexts):
        ntii.num=ii+1

    return nttexts



def attachRefTextsToNotes(nttexts,hltexts):
    '''Attach highlighted texts to a piece of note as its reference.

    <nttexts>: list of Anno objs, extracted notes.
    <hltexts>: list of Anno objs, extracted highlights.

    Return <nttexts>: list of Anno objs, extracted notes, with ref texts
                      attached as a "ori_text" attribute.

    Association of highlighted texts to a note is based on:
        - if location of note is inside the bbox of a highlight box,
        - if not, the closet distance from a highlight box, as long as it is
          within a certain threshold.
        - if the same page has no highlights, skip.
    '''

    def isInside(x,y,rect):
        '''Check if point (x,y) is inside rect'''
        x1,y1,x2,y2=rect
        if x1<x<x2 and y1<y<y2:
            return True
        else:
            return False

    def distFromBox(x,y,rect):
        '''Get closest dist from a point outside of rect to rect'''
        x1,y1,x2,y2=rect
        if y1<y<y2:
            dist=x-x2 if x>x2 else x1-x
        elif x1<x<x2:
            dist=y-y2 if y>y2 else y1-y
        else:
            if x>x2 and y>y2:
                # topright:
                dist=math.sqrt((x-x2)**2+(y-y2)**2)
            elif x<x1 and y>y2:
                # topleft:
                dist=math.sqrt((x-x1)**2+(y-y2)**2)
            elif x<x1 and y<y1:
                # bottomleft:
                dist=math.sqrt((x-x1)**2+(y-y1)**2)
            else:
                # bottomright:
                dist=math.sqrt((x-x2)**2+(y-y1)**2)
        return dist

    hlpages=[hlii.page for hlii in hltexts]

    for ntii in nttexts:
        boxii=ntii.bbox
        pageii=ntii.page
        if pageii not in hlpages:
            continue

        x0=0.5*(boxii[0]+boxii[2])
        y0=0.5*(boxii[1]+boxii[3])

        #--------Check if note inside highlight bbox--------
        got_ref=False
        for jj,hljj in enumerate(hltexts):
            if hljj.page!=pageii:
                continue
            if isInside(x0,y0,hljj.bbox):
                ntii.ori_text=hljj.text
                got_ref=True
                break
        if got_ref:
            continue

        #-----Check if note close to any highlight box-----
        max_dist=MAX_ASSOCIATE_DIST
        hls_in_page=[hlii for hlii in hltexts if hlii.page==pageii]
        dists=[distFromBox(x0,y0,hlii.bbox) for hlii in hls_in_page]
        if min(dists)>max_dist:
            # too far, don't assume association
            continue
        ori_hl=hls_in_page[dists.index(min(dists))]
        ntii.ori_text=ori_hl.text

    return nttexts

