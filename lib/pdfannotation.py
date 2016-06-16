'''Utitlity functions for annotation extraction.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# LGPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the LGPLv3 license.


Update time: 2016-02-19 14:33:33.
'''




from datetime import datetime
from PyPDF2.generic import *



YELLOW = [0.95, 0.9, 0.2]



def getRGBcolor(color,verbose=True):
    '''Convert html color to RGB (0,1)
    '''
    color=color.replace('#','')
    rgb=tuple(map(ord,color.decode('hex')))
    return [float(ii)/255 for ii in rgb]

    


def floatArray(lst):
    return ArrayObject([FloatObject(i) for i in lst])



def now():
    # Python timezone handling is a messs, so just use UTC
    return TextStringObject(datetime.utcnow().\
            strftime("D:%Y%m%d%H%M%SZ00'00"))



def _baseAnno(rect, contents=None, author=None, subject=None,
                       cdate=None, color=None, alpha=1, flag=4):
    '''Set shared properties of all markup annotations.'''

    if cdate is None:
        cdate = now()
    else:
        assert isinstance(cdate, datetime),\
                "cdate is not a datetime object"
        cdate = TextStringObject(cdate.strftime("D:%Y%m%d%H%M%SZ00'00"))

    retval = DictionaryObject({\
            NameObject('/CA'): FloatObject(alpha),\
            NameObject('/F'): NumberObject(flag),\
            NameObject('/Rect'): floatArray(rect),\
            NameObject('/Type'): NameObject('/Annot'),\
            NameObject('/CreationDate'): cdate,\
            NameObject('/M'): now(),\
            })

    # Whether to add an explicit popup when adding to page
    retval.popup = False  
    if contents is not None:
        retval[NameObject('/Contents')] = TextStringObject(contents)
    if author is not None:
        retval[NameObject('/T')] = TextStringObject(author)
    if subject is not None:
        retval[NameObject('/Subj')] = TextStringObject(subject)
    if color is not None:
        retval[NameObject('/C')] = floatArray(color)


    return retval



def _popupAnnotation(parent, rect=None):
    '''Create a 'Popup' annotation connected to parent
    (an indirect object).
    '''

    if rect is None:
        # Make Golden ratio rectangle lined up at 
        # right-hand side of parent
        _, _, x, y = parent.getObject()['/Rect']
        rect = [x, y-100, x+162, y]

    retval=DictionaryObject({\
            NameObject('/Type'): NameObject('/Annot'),\
          NameObject('/Subtype'): NameObject('/Popup'),\
          NameObject('/M'): now(),\
          NameObject('/Rect'): floatArray(rect),\
          NameObject('/Parent'): parent,\
        })

    return retval



def createHighlight(rect, contents=None, author=None,\
                         subject=None, cdate=None, color=None,\
                         alpha=1, flag=4):
    '''Create a Highlight annotation given rect.

    <rect>: list, coordinates of highlighted rectangles:
            [x0,y0,x1,y1], 
            where (x0,y0) is the lower left corner, (x1,y1) the upper
            right corner.

    <contents>: string, content.
    <author>: string, author of the annotation.
    <subject>: string, annotation subject.
    <cdate>: datetime obj or None, creation time. If None, obtain
             the current time.
    <color>: list-type, the color of the highlighted region,
             as an array of type [g], [r,g,b], or [c,m,y,k].
    <alpha>: float, the alpha transparency of the highlight.
    <flag>: int, bit flag of options.  4 means the annotation
            should be printed.  See the PDF spec for more.

    Return: <retval>: A DictionaryObject representing the annotation.

    Update time: 2016-02-19 14:39:13.
    '''

    x0,y0,x1,y1=rect
    qpl=[x0, y1, x1, y1, x0, y0, x1, y0]
    if color is None:
        color=YELLOW
    else:
        try:
            color=getRGBcolor(color)
        except:
            color=YELLOW

    retval = _baseAnno(rect, contents, author,\
            subject, cdate, color, alpha, flag)
    retval[NameObject('/Subtype')] = NameObject('/Highlight')
    retval[NameObject('/QuadPoints')] = floatArray(qpl)

    return retval



def createNote(rect, contents=None, author=None, subject=None,\
                    cdate=None, color=None, alpha=1, flag=4,\
                    icon=None, open_=True, state=None, state_model=None):
    '''Create a text annotation given rect as a sticky note.

    <rect>: a rectangle [x0,y0,x1,y1].  The icon will be in the
            top-left corner of this rectangle (x0,y1) regardless
            of the size.
    <cdate>: datetime obj or None, creation time. If None, obtain
             the current time.
    <color>: list-type, the color of the highlighted region,
             as an array of type [g], [r,g,b], or [c,m,y,k].
    <alpha>: float, the alpha transparency of the highlight.
    <flag>: int, bit flag of options.  4 means the annotation
            should be printed.  See the PDF spec for more.
    <icon>: string, the icon to use for the note.
            Try "Comment", "Key", "Note", "Help", "NewParagraph",
            "Paragraph", "Insert"
    <open_>: bool, whether the note should be opened by default.
    <state>: ?, set the state of the annotation. See the PDF
            spec state_model for further details.

    Return: <retval>: A DictionaryObject representing the annotation.

    Update time: 2016-02-19 14:39:13.
    '''
    
    if color is None:
        color=YELLOW
    else:
        try:
            color=getRGBcolor(color)
        except:
            color=YELLOW

    retval = _baseAnno(rect, contents, author, subject, cdate,
                                color, alpha, flag)
    retval.popup = True

    retval[NameObject('/Subtype')] = NameObject('/Text')
    retval[NameObject('/Open')] = BooleanObject(open_)

    if icon is not None:
        retval[NameObject('/Name')] = NameObject('/' + icon)
    if state is not None:
        retval[NameObject('/State')] = TextStringObject(state)
    if state_model is not None:
        retval[NameObject('/StateModel')] = TextStringObject(state_model)

    return retval



def addAnnotation(page, outpdf, anno):
    """Add the annotation to the output PDF. 

    """
    # We need to make an indirect reference, or Acrobat will get huffy.
    indir = outpdf._addObject(anno)
    if '/Annots' in page:
        page['/Annots'].append(indir)
    else:
        page[NameObject('/Annots')] = ArrayObject([indir])

    if anno.popup:
        popup = _popupAnnotation(indir)
        indir_popup = outpdf._addObject(popup)
        anno[NameObject('/Popup')] =  indir_popup
        page['/Annots'].append(indir_popup)

    return page







