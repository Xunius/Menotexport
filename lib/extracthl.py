'''Extract highlighted texts from PDFs in Mendeley.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-02-23 18:04:10.
'''



from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBox, LTTextLine, LTAnno,\
        LTTextBoxHorizontal, LTTextLineHorizontal, LTChar
from numpy import sqrt, argsort
import wordfix




#------Store highlighted texts with metadata------
class Anno(object):
    def __init__(self,text,ctime=None,color=None,title=None,author=None,\
            note_author=None,page=None,citationkey=None,tags=None):

        self.text=text
        self.ctime=ctime
        self.color=color
        self.title=title
        self.author=author
        self.note_author=note_author
        self.page=page
        self.citationkey=citationkey
        self.tags=tags

        if tags is None:
            self.tags='None'
        if type(tags)==list and None in tags:
            tags=['None' if v is None else v for v in tags]
            self.tags=tags

    def __repr__(self):
        reprstr='''\
Annotation text:    %s
Creation time:      %s
Paper title:        %s
Annotation author:  %s
Citation key:       %s
Annotation color:   %s
Page:               %s
Tags:               %s
''' %(self.text, self.ctime, self.title,\
      self.note_author, self.page, self.citationkey,\
      ', '.join(self.tags))
        
        reprstr=reprstr.encode('ascii','replace')

        return reprstr




#-------Locate and extract strings from a page layout obj-------
def findStrFromBox(anno,box,verbose=True):
    '''Locate and extract strings from a page layout obj

    '''


    texts=u''
    num=0

    #-----------Sort annotations vertically-----------
    anno=sortAnnoY(anno)
    
    #----------------Loop through annos----------------
    for ii,hii in enumerate(anno):

        #----------Create a dummy LTTextLine obj----------
        hiibox=hii['rect']
        dummy=LTTextLine(hiibox)
        dummy.set_bbox(hiibox)   #Needs this step
    
        if box.is_hoverlap(dummy) and box.is_voverlap(dummy):
            textii=[]
            num+=1

            lines=sortY(box._objs)

            #----------------Loop through lines----------------
            for lineii in lines:
                if type(lineii)!=LTTextLine and\
                        type(lineii)!=LTTextLineHorizontal:
                    continue
                if lineii.is_hoverlap(dummy) and\
                        lineii.is_voverlap(dummy):
                    #chars=sortX(lineii._objs)
                    chars=lineii._objs

                    #----------------Loop through chars----------------
                    for charii in chars:
                        if type(charii)==LTAnno:
                            textii.append(charii.get_text())
                        elif type(charii)==LTChar:
                            if charii.is_hoverlap(dummy) and\
                                    charii.is_voverlap(dummy):
                                textii.append(charii.get_text())

            #----------------Concatenate texts----------------
            textii=u''.join(textii).strip(' ')

            textii=textii.strip('\n')
            textii=textii.replace('\n',' ')

            #---------------Join with next line---------------
            if len(texts)>1 and texts[-1]=='-':
                texts=texts[:-1]
                joiner=u''
            else:
                joiner=u' '

            #---------------Jump---------------
            linegap,chargap=measureGap(lines)
            textii=textii.strip()
            if ii==0 or len(texts)==0:
                texts+=joiner+textii
            else:
                #lastbox=anno[ii-1]['rect']
                if checkJump(lastbox, hiibox, lineii,linegap,chargap):
                    textii=u' ...... '+textii 
                    texts+=joiner+textii
                else:
                    texts+=joiner+textii

            lastbox=hiibox
                
    texts=texts.strip()
    #------------------Do some fixes------------------
    if len(texts)>0:
        texts=wordfix.fixWord(texts)

    return texts, num





def measureGap(linelist):
    '''Detect char and line gaps
    '''
    listmean=lambda ll: reduce(lambda x,y:x+y, ll)/float(len(ll))

    try:
        #-----------------Detect line gaps-----------------
        lnum=min(5, len(linelist))   #Get a sample of 5 lines

        #Get y coordinates of bottom left corners of each line
        lineys=[linelist[ii].bbox[1] for ii in range(lnum)]
        linegaps=[abs(lineys[ii+1]-lineys[ii]) for ii in range(lnum-1)]
        linegap=listmean(linegaps)

        #-----------------Detect char gaps-----------------
        lchar=10  #Get a sample of 10 consecutive chars.
        charfound=0
        charxs=[]
        idx=0

        while charfound<lchar and idx<len(linelist):
            lineii=linelist[idx]
            for charjj in lineii._objs:
                if type(charjj)==LTChar:
                    charfound+=1
                    charxs.append(charjj.bbox[0])
                elif type(charjj)==LTAnno:
                    charfound=0
                    charxs=[]

                if charfound>=lchar:
                    break

            idx+=1

        chargaps=[abs(charxs[ii+1]-charxs[ii]) for ii in range(len(charxs)-1)]
        chargap=listmean(chargaps)
        chargap=int(chargap)+1

    except:
        linegap=10
        chargap=5

    return linegap, chargap




def checkJump(lastbox,curbox,curline,linegap,chargap):
    '''Check whether there is a gap between 2 annotations.

    '''
    # 2 annos in the same line
    if abs(lastbox[1]-curbox[1])<=linegap:
        if curbox[0]-lastbox[2]>5*chargap:
            return True

    # 2 annos gap by at least 1 line
    elif abs(lastbox[1]-curbox[1])>=2*linegap:
        return True

    # 2 annos are in continuous lines
    elif abs(lastbox[1]-curbox[1])>linegap and \
        abs(lastbox[1]-curbox[1])<2*linegap:
            # current anno doesn't start at line beginning
        if curbox[0]-curline.bbox[0]>=5*chargap:
            return True
        else:
            # last anno doesn't end with line end
            # assuming last line has same x2 coordinate as current
            if curline.bbox[2]-lastbox[2]>=3*chargap:
                return True

    return False


#-------------------------Fine tune box order-------------------------
def fineTuneOrder(objs,verbose=True):
    '''Fine tune box order

    For a list of box objs that share similar x coordinates
    of the top-left corner, sort using their y (+ve upwards)
    coordinates so that larger y goes first.
    '''

    topleft=[(ii.bbox[0],ii.bbox[3]) for ii in objs]
    objdict={}
    for ii in objs:
        objdict[ii.bbox[0],ii.bbox[3]]=ii

    for ii in range(len(objs)-1):
        x0,y0=topleft[ii]
        x1,y1=topleft[ii+1]

        if abs(x0-x1)<=30 and y1-y0>1:
            topleft[ii]=(x1,y1)
            topleft[ii+1]=(x0,y0)

    result=[]
    for ii in topleft:
        result.append(objdict[ii])

    return result




#---------------------Sort box elements diagnoally---------------------
def sortDiag(layout,verbose=True):
    '''Sort box elements diagnoally

    Sort the box objs in <layout> so that they follow the
    reading order in 2-column PDFs: from top-down, from
    left to right column.

    Sort by measuring the perpendicular distance from the
    topleft corner of a box to the line (y=2w/h*x+h, with origin
    at bottom-left corner of page).
    '''

    dist=lambda x,y,w,h: abs(2.*h*x/w-y+h)/sqrt((2.*h/w)**2+1)

    w=layout.width
    h=layout.height

    dists=[dist(jj.bbox[0],jj.bbox[3],w,h) for jj in layout._objs]
    idx=argsort(dists)

    objs=[layout._objs[ii] for ii in idx]

    return objs




#-------------------------Sort objs vertically-------------------------
def sortY(objs,verbose=True):
    '''Sort objs vertically

    Sort objs with similar x coordinates by y coordinates
    '''

    objdict={}
    for ii in objs:
        objdict[-ii.bbox[3],ii.bbox[0]]=ii

    keys=objdict.keys()
    keys=sorted(keys)

    result=[objdict[ii] for ii in keys]

    return result




#------------------------Sort objs horizontally------------------------
def sortX(objs,verbose=True):
    '''Sort objs horizontally

    Sort objs with similar y coordinates by x coordinates
    '''

    objdict={}
    for ii in objs:
        objdict[ii.bbox[0],-ii.bbox[3]]=ii

    keys=objdict.keys()
    keys=sorted(keys)

    result=[objdict[ii] for ii in keys]

    return result



    
#-------------------------Sort annos vertically-------------------------
def sortAnnoY(objs,verbose=True):
    '''Sort objs vertically

    Sort annotations (from Mendeley database) by (y,x)
    coordinates of the topleft corner.
    '''

    objdict={}
    for ii in objs:
        objdict[-ii['rect'][3],ii['rect'][0]]=ii

    keys=objdict.keys()
    keys=sorted(keys)

    result=[objdict[ii] for ii in keys]

    return result





#------------------------Initiate analysis objs------------------------
def init(filename,verbose=True):
    '''Initiate analysis objs
    '''

    fp = open(filename, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fp)
    # Create a PDF document object that stores the document structure.
    # Supply the password for initialization.
    document = PDFDocument(parser)
    # Check if the document allows text extraction. If not, abort.
    if not document.is_extractable:
        raise PDFTextExtractionNotAllowed
    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()
    # Create a PDF device object.
    device = PDFDevice(rsrcmgr)
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # Set parameters for analysis.
    laparams = LAParams()

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return document, interpreter, device
    



#----------------Get the latest creation time of annos----------------
def getCtime(annos,verbose=True):
    '''Get the latest creation time of a list of annos

    '''

    ctimes=[ii['cdate'] for ii in annos]
    ctimes.sort()
    return ctimes[-1]





#----------------Extract highlighted texts from a PDF--------
def extractHighlights(filename,anno,verbose=True):
    '''Extract highlighted texts from a PDF

    '''
    hlpages=anno.hlpages
    if len(hlpages)==0:
        return []

    #--------------Get pdfmine instances--------------
    document, interpreter, device=init(filename)

    #----------------Loop through pages----------------
    hltexts=[]

    for ii,page in enumerate(PDFPage.create_pages(document)):

        #------------Get highlights in page------------
        if len(hlpages)>0 and ii+1 in hlpages:

            anno_total=len(anno.highlights[ii+1])
            anno_found=0

            interpreter.process_page(page)
            layout = device.get_result()

            #--------------Sort boxes diagnoally--------------
            objs=sortDiag(layout)

            #-----------------Refine ordering-----------------
            objs=fineTuneOrder(objs)

            #----------------Loop through boxes----------------
            for jj,objj in enumerate(objs):

                if type(objj)!=LTTextBox and\
                        type(objj)!=LTTextBoxHorizontal:
                    continue
                textjj,numjj=findStrFromBox(anno.highlights[ii+1],objj)

                if numjj>0:
                    #--------------Attach text with meta--------------
                    textjj=Anno(textjj,\
                        ctime=getCtime(anno.highlights[ii+1]),\
                        title=anno.meta['title'],\
                        page=ii+1,citationkey=anno.meta['citationkey'],\
                        tags=anno.meta['tags'])

                    hltexts.append(textjj)

                #----------------Break if all found----------------
                anno_found+=numjj
                if anno_total==anno_found:
                    break


    return hltexts





