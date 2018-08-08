'''Export PDF with annotations from Mendeley.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-12 22:09:38.
'''

import os
import shutil
import PyPDF2
import pdfannotation
from tools import printInd, printNumHeader, makedirs



#--------------------Export PDFs with annotations--------------
def exportAnnoPdf(annotations,outdir,verbose=True):
    '''Export PDFs

    <annotations>: dict, keys: docid, values: menotexport.DocAnno obj.
    <outdir>: str, folder path to save PDFs.

    Update time: 2018-07-28 20:21:09.
    '''

    faillist=[]
    num=len(annotations)
    for ii,annoii in enumerate(annotations.values()):
        if not annoii.hasfile:
            continue

        for fjj,annojj in annoii.file_annos.items():
            assert fjj is not None, 'fjj is None'
            # when side-bar note exists but no pdf.
            # shouldn't happen if annoii.hasfile is False

            fnamejj=annojj.filename

            if verbose:
                printNumHeader('Exporting PDF:',ii+1,num,3)
                printInd(fnamejj,4)
            try:
                exportPdf(fjj,outdir,annojj,verbose)
            except:
                faillist.append(fnamejj)

    return faillist


#---------------------Copy PDF to target location---------------------
def copyPdf(doclist,outdir,verbose=True):
    '''Copy PDF to target location

    <doclist>: list of meta data dicts
    <outdir>: str, path to output folder
    '''
    if not os.path.isdir(outdir):
        makedirs(outdir)

    faillist=[]

    num=len(doclist)
    for ii,docii in enumerate(doclist):

        pathii=docii['path']
        if pathii is None:
            continue

        for jj,pjj in enumerate(pathii):
            basedir,filename=os.path.split(pjj)
            targetname=os.path.join(outdir,filename)

            if not os.path.exists(pjj):
                faillist.append(pjj)
                continue

            if verbose:
                printNumHeader('Copying file:',ii+1,num,3)
                printInd(filename,4)

            try:
                shutil.copy2(pjj,targetname)
            except:
                faillist.append(filename)

    return faillist


#---------------Export pdf---------------
def exportPdf(fin,outdir,annotations,verbose):
    '''Export PDF with annotations.

    <fin>: string, absolute path to input PDF file.
    <outdir>: string, absolute path to the output directory.
    <annotations>: FileAnno obj.

    Update time: 2016-02-19 14:32:56.
    '''

    #---------------Skip unlinked files---------------
    assert annotations.hasfile, 'no file of %s' %fin
    #if not annotations.hasfile:
        #return

    try:
        inpdf = PyPDF2.PdfFileReader(open(fin, 'rb'))
        if inpdf.isEncrypted:
            # PyPDF2 seems to think some files are encrypted even
            # if they are not. We just ignore the encryption.
            # This seems to work for the one file where I saw this issue
            #inpdf._override_encryption = True
            #inpdf._flatten()
            # UPDATE: trying to decrypt takes a lot of time,
            # as this rarely happens to academic docs I'm skipping this
            # and simply treat as fail
            raise Exception("Skip encrypt")
    except IOError:
        print('Could not find pdf file %s' %fin)

    outpdf = PyPDF2.PdfFileWriter()

    #----------------Loop through pages----------------
    pages=range(1,inpdf.getNumPages()+1)

    for pii in pages:

        inpg = inpdf.getPage(pii-1)

        #----------------Process highlights----------------
        if pii in annotations.hlpages:
            for hjj in annotations.highlights[pii]:
                anno = pdfannotation.createHighlight(hjj["rect"],\
                        cdate=hjj["cdate"], color=hjj['color'])
                inpg=pdfannotation.addAnnotation(inpg,outpdf,anno)

        #------------------Process notes------------------
        if pii in annotations.ntpages:
            for njj in annotations.notes[pii]:
                note = pdfannotation.createNote(njj["rect"], \
                        contents=njj["content"], author=njj["author"],\
                        cdate=njj["cdate"])
                inpg=pdfannotation.addAnnotation(inpg,outpdf,note)

        outpdf.addPage(inpg)

    #-----------------------Save-----------------------
    filename=annotations.filename
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    abpath_out=os.path.join(outdir,filename)
    if os.path.isfile(abpath_out):
        os.remove(abpath_out)

    with open(abpath_out, mode='wb') as fout:
        outpdf.write(fout)

    return

