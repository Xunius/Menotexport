#!/usr/bin/python
'''
- Bulk export annotated PDFs from Mendeley, with notes and highlights.
- Extract mendeley notes and highlights and save into text file(s).
- Group highlights and notes by tags, and export to a text file.
- Note that PDFs without annotations are not exported.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-02-23 18:04:10.
'''


#---------------------Imports---------------------
import sys
import sqlite3
import os
import PyPDF2
import argparse
import pandas as pd
from textwrap import TextWrapper
from lib import pdfannotation
from lib import extracttags
from lib import extracthl
from datetime import datetime

if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse



class FileAnno(object):

    def __init__(self, path, meta, highlights=None, notes=None):
        '''Obj to hold annotations (highlights+notes) in a single PDF.
        '''

        self.path=path
        self.meta=meta
        self.highlights=highlights
        self.notes=notes

        if highlights is None:
            self.hlpages=[]
        else:
            self.hlpages=highlights.keys()
            self.hlpages.sort()

        if notes is None:
            self.ntpages=[]
        else:
            self.ntpages=notes.keys()
            self.ntpages.sort()

        self.pages=list(set(self.hlpages+self.ntpages))
        self.pages.sort()




def convert2datetime(s):
    return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ')




def converturl2abspath(url):
    '''Convert a url string to an absolute path
    This is necessary for filenames with unicode strings.
    '''

    #--------------------For linux--------------------
    path = unquote(str(urlparse(url).path)).decode("utf8") 
    path=os.path.abspath(path)

    if os.path.exists(path):
        return path
    else:
        #-------------------For windowes-------------------
        if url[5:8]==u'///':   
            url=u'file://'+url[8:]
            path=urlparse(url)
            path=os.path.join(path.netloc,path.path)
            path=unquote(str(path)).decode('utf8')
            path=os.path.abspath(path)
            return path



def getHighlights(db, results=None, folder=None):
    '''Extract the locations of highlights from the Mendeley database
    and put results into a dictionary.

    <db>: sqlite3.connection to Mendeley sqlite database.
    <results>: dict or None, optional dictionary to hold the results. 

    Return: <results>: dictionary containing the query results, with
            the following structure:

            results={filepath1: {'highlights': {page1: [hl1, hl2,...],
                                                page2: [hl1, hl2,...],
                                                ...}
                                 'notes':      {page1: [nt1, nt2,...],
                                                page4: [nt1, nt2,...],
                                                ...}
                                 'meta':       {'title': title,
                                                'tags': [tag1, tag2,...],
                                                'cite': citationkey}
                     filepath2: ...
                                }
            where hl1={'rect': bbox,
                       'cdate': cdate,
                       'page':pg}
                  note={'rect': bbox,
                        'author':author,
                        'content':txt,
                        'cdate': cdate,
                        'page':pg}
    
    Update time: 2016-02-24 00:36:33.
    '''

    query =\
    '''SELECT Files.localUrl, FileHighlightRects.page,
                    FileHighlightRects.x1, FileHighlightRects.y1,
                    FileHighlightRects.x2, FileHighlightRects.y2,
                    FileHighlights.createdTime,
                    Folders.name,
                    DocumentFolders.folderid
            FROM Files
            LEFT JOIN FileHighlights
                ON FileHighlights.fileHash=Files.hash
            LEFT JOIN FileHighlightRects
                ON FileHighlightRects.highlightId=FileHighlights.id
            LEFT JOIN DocumentFolders
                ON DocumentFolders.documentId=FileHighlights.documentId
            LEFT JOIN Folders
                ON Folders.id=DocumentFolders.folderid
            WHERE (FileHighlightRects.page IS NOT NULL)
    '''
    if folder is not None:

        fstr=['(Folders.name="%s")' %ii for ii in folder]
        fstr=' AND '.join(fstr)
        query=query+' AND\n'+fstr


    query2=\
    '''SELECT Files.localUrl, DocumentTags.tag,
              Documents.title,
              Documents.citationkey
       FROM Files
       LEFT JOIN FileHighlights
           ON FileHighlights.fileHash=Files.hash
       LEFT JOIN DocumentTags
           ON DocumentTags.documentId=FileHighlights.documentId
       LEFT JOIN Documents
           ON Documents.id=FileHighlights.documentId
    '''

            
    if results is None:
        results={}

    #------------------Get file meta data------------------
    ret2=db.execute(query2)
    data=ret2.fetchall()

    df=pd.DataFrame(data=data,columns=['url',\
            'tags','title','citetationkey'])
    fetchField=lambda x, f: x[f].unique().tolist()

    #------------------Get highlights------------------
    ret = db.execute(query)
    pthold=None

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[4], r[5]]
        cdate = convert2datetime(r[6])
        folder=r[7]
        hlight = {'rect': bbox,\
                  'cdate': cdate,\
                  'page':pg\
                  }

        #------------Update metadata only once/file------------
        if pthold!=pth or ii==0:
            dataii=df[df.url==r[0]]
            tags=fetchField(dataii,'tags')
            tags+=[folder,]
            title=fetchField(dataii,'title')[0]
            cite=fetchField(dataii,'citetationkey')[0]

            meta={'title': title,\
                  'tags': tags,\
                  'cite': cite\
                  }

        if pth in results:
            if 'highlights' in results[pth]:
                if pg in results[pth]['highlights']:
                    results[pth]['highlights'][pg].append(hlight)
                else:
                    results[pth]['highlights'][pg]=[hlight,]
            else:
                results[pth]['highlights']={pg:[hlight,]}
        else:
            results[pth]={'highlights':{pg:[hlight,]}}
            results[pth]['meta']=meta


        pthold=pth

    return results



#-------------------Get notes-------------------
def getNotes(db, results=None, folder=None):
    '''Extract notes from the Mendeley database

    <db>: sqlite3.connection to Mendeley sqlite database.
    <results>: dict or None, optional dictionary to hold the results. 

    Return: <results>: dictionary containing the query results, with
            the following structure:

            results={filepath1: {'highlights': {page1: [hl1, hl2,...],
                                                page2: [hl1, hl2,...],
                                                ...}
                                 'notes':      {page1: [nt1, nt2,...],
                                                page4: [nt1, nt2,...],
                                                ...}
                                 'meta':       {'title': title,
                                                'tags': [tag1, tag2,...],
                                                'cite': citationkey}
                     filepath2: ...
                                }
            where hl1={'rect': bbox,
                       'cdate': cdate,
                       'page':pg}
                  note={'rect': bbox,
                        'author':author,
                        'content':txt,
                        'cdate': cdate,
                        'page':pg}

    Update time: 2016-02-24 00:36:50.
    '''

    query=\
    '''SELECT Files.localUrl, FileNotes.page,
                    FileNotes.x, FileNotes.y,
                    FileNotes.author, FileNotes.note,
                    FileNotes.modifiedTime,
                    Folders.name,
                    DocumentFolders.folderid
            FROM Files
            LEFT JOIN FileNotes
                ON FileNotes.fileHash=Files.hash
            LEFT JOIN DocumentFolders
                ON DocumentFolders.documentId=FileNotes.documentId
            LEFT JOIN Folders
                ON Folders.id=DocumentFolders.folderid
            WHERE (FileNotes.page IS NOT NULL)
    '''

    if folder is not None:
        fstr=['(Folders.name="%s")' %ii for ii in folder]
        fstr=' AND '.join(fstr)
        query=query+' AND\n'+fstr


    query2=\
    '''SELECT Files.localUrl, DocumentTags.tag,
              Documents.title,
              Documents.citationkey
       FROM Files
       LEFT JOIN FileNotes
           ON FileNotes.fileHash=Files.hash
       LEFT JOIN DocumentTags
           ON DocumentTags.documentId=FileNotes.documentId
       LEFT JOIN Documents
           ON Documents.id=FileNotes.documentId
    '''

    if results is None:
        results={}

    #------------------Get file meta data------------------
    ret2=db.execute(query2)
    data=ret2.fetchall()

    df=pd.DataFrame(data=data,\
            columns=['url', 'tags','title','citetationkey'])
    fetchField=lambda x, f: x[f].unique().tolist()

    #------------------Get notes------------------
    ret = db.execute(query)
    pthold=None

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
   
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30] 
        # needs a rectangle however size does not matter
        author=r[4]
        txt = r[5]
        cdate = convert2datetime(r[6])
        folder=r[7]
        note = {'rect': bbox,\
                'author':author,\
                'content':txt,\
                'cdate': cdate,\
                'page':pg\
                  }

        if pthold!=pth or ii==0:
            dataii=df[df.url==r[0]]
            tags=fetchField(dataii,'tags')
            tags+=[folder,]
            title=fetchField(dataii,'title')[0]
            cite=fetchField(dataii,'citetationkey')[0]

            meta={'title': title,\
                  'tags': tags,\
                  'cite': cite\
                  }

        if pth in results:
            if 'notes' in results[pth]:
                if pg in results[pth]['notes']:
                    results[pth]['notes'][pg].append(note)
                else:
                    results[pth]['notes'][pg]=[note,]
            else:
                results[pth]['notes']={pg:[note,]}
        else:
            results[pth]={'notes':{pg:[note,]}}
            results[pth]['meta']=meta

        pthold=pth

    return results




#-------------Reformat annotations to a list of FileAnnos-------------
def reformatAnno(annodict):
    '''Reformat annotations to a list of FileAnnos

    <annodict>: dict, annotation dict. See doc in getHighlights().
    Return <annos>: list, contains FileAnno objs corresponding to
                    annotations (highlights and notes) in each file.
    '''

    annos=[]
    for kk,vv in annodict.items():
        annoii=FileAnno(kk, vv['meta'], highlights=vv.get('highlights',{}),\
                notes=vv.get('notes',{}))
        annos.append(annoii)

    return annos


    

#-----------------Extract notes-----------------
def extractNotes(path,anno,verbose=True):
    '''Extract notes

    <path>: str, absolute path to a PDF file.
    <anno>: FileAnno obj, contains annotations in PDF.
    
    Return <nttexts>: list, Anno objs containing annotation info from a PDF.
                      Prepare to be exported to txt files.
    '''
    from lib.extracthl import Anno

    notes=anno.notes
    meta=anno.meta

    nttexts=[]

    #----------------Loop through pages----------------
    if len(anno.ntpages)==0:
        return nttexts

    for pp in anno.ntpages:

        for noteii in notes[pp]:
            textjj=Anno(noteii['content'], ctime=noteii['cdate'],\
                    title=meta['title'],\
                    page=pp,citationkey=meta['cite'], note_author=noteii['author'],\
                    tags=meta['tags'])
            nttexts.append(textjj)

    return nttexts



#---------------Export pdf---------------
def exportPdf(fin,fout,annotations,overwrite,\
        allpages,verbose):
    '''Export PDF with annotations.

    <fin>: string, absolute path to input PDF file.
    <fout>: string, absolute path to the output PDF file.
    <annotations>: FileAnno obj.
    <overwrite>: bool, whether to overwrite existing output
                 PDFs or not.
    <allpages>: bool, True to export complete PDF files;
                      False to export only pages with annotations.

    Update time: 2016-02-19 14:32:56.
    '''

    try:
        inpdf = PyPDF2.PdfFileReader(open(fin, 'rb'))
        if inpdf.isEncrypted:
            # PyPDF2 seems to think some files are encrypted even
            # if they are not. We just ignore the encryption.
            # This seems to work for the one file where I saw this issue
            inpdf._override_encryption = True
            inpdf._flatten()
    except IOError:
        print('Could not find pdf file %s' %fin)
        return

    outpdf = PyPDF2.PdfFileWriter()

    #----------------Loop through pages----------------
    if allpages:
        pages=range(1,inpdf.getNumPages()+1)
    else:
        pages=annotations.pages

    for pii in pages:

        inpg = inpdf.getPage(pii-1)

        #----------------Process highlights----------------
        if pii in annotations.hlpages:
            for hjj in annotations.highlights[pii]:
                anno = pdfannotation.createHighlight(hjj["rect"],\
                        cdate=hjj["cdate"])
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
    if os.path.isfile(fout):
        if not overwrite:
            if verbose:
                print('\n# <mennoteexport>: Skip overwriting PDF...')
            return
        else:
            if verbose:
                print('\n# <mennoteexport>: Exporting and overwriting PDF...')
    else:
        if verbose:
            print('\n# <mennoteexport>: Exporting PDF...')

    outpdf.write(open(fout, "wb"))

    return



#------------------Export annotations in a single PDF------------------
def _exportAnnoFile(abpath_out,anno,verbose=True):
    '''Export annotations in a single PDF

    <abpath_out>: str, absolute path to output txt file.
    <anno>: list, in the form [highlight_list, note_list].
            highlight_list and note_list are both lists of
            Anno objs (see extracthl.py), containing highlights
            and notes in TEXT format with metadata. To be distinguished
            with FileAnno objs which contains texts coordinates.
            if highlight_list or note_list is [], no such info
            in this PDF.

    Function takes annotations from <anno> and output to the target txt file
    in the following format:

    -----------------------------------------------------
    # Title of PDF

        > Highlighted text line 1
          Highlighted text line 2
          Highlighted text line 3
          ...
            
            - @citationkey
            - Tags: @tag1, @tag2, @tag3...
            - Ctime: creation time
    
    -----------------------------------------------------
    # Title of another PDF

        > Highlighted text line 1
          Highlighted text line 2
          Highlighted text line 3
          ...
            
            - @citationkey
            - Tags: @tag1, @tag2, @tag3...
            - Ctime: creation time

    Use tabs in indention, and markup syntax: ">" for highlights, and "-" for notes.

    Update time: 2016-02-24 13:59:56.
    '''

    conv=lambda x:unicode(x)

    wrapper=TextWrapper()
    wrapper.width=80
    wrapper.initial_indent=''
    #wrapper.subsequent_indent='\t'+int(len('> '))*' '
    wrapper.subsequent_indent='\t'

    wrapper2=TextWrapper()
    wrapper2.width=80-7
    wrapper2.initial_indent=''
    #wrapper2.subsequent_indent='\t\t'+int(len('- Tags: '))*' '
    wrapper2.subsequent_indent='\t\t'

    hlii,ntii=anno
    try:
        titleii=hlii[0].title
    except:
        titleii=ntii[0].title

    outstr=u'\n\n{0}\n# {1}'.format(int(80)*'-',conv(titleii))

    with open(abpath_out, mode='a') as fout:
        outstr=outstr.encode('ascii','replace')
        fout.write(outstr)

        #-----------------Write highlights-----------------
        if len(hlii)>0:

            if verbose:
                print('\n# <mennoteexport>: Exporting highlights in:')
                print(titleii)

            #-------------Loop through highlights-------------
            for hljj in hlii:
                hlstr=wrapper.fill(hljj.text)
                tagstr=', '.join(['@'+kk for kk in hljj.tags])
                tagstr=wrapper2.fill(tagstr)
                outstr=u'''
\n\t> {0}

\t\t- @{1}
\t\t- Tags: {2}
\t\t- Ctime: {3}
'''.format(*map(conv,[hlstr, hljj.citationkey,\
    tagstr, hljj.ctime]))

                outstr=outstr.encode('ascii','replace')
                fout.write(outstr)

        #-----------------Write notes-----------------
        if len(ntii)>0:

            if verbose:
                print('\n# <mennoteexport>: Exporting notes in:')
                print(titleii)

            #----------------Loop through notes----------------
            for ntjj in ntii:
                ntstr=wrapper.fill(ntjj.text)
                tagstr=', '.join(['@'+kk for kk in ntjj.tags])
                tagstr=wrapper2.fill(tagstr)
                outstr=u'''
\n\t- {0}

\t\t- @{1}
\t\t- Tags: {2}
\t\t- Ctime: {3}
'''.format(*map(conv,[ntstr, ntjj.citationkey,\
    tagstr, ntjj.ctime]))

                outstr=outstr.encode('ascii','replace')
                fout.write(outstr)

        

    

    
#--------------------Export highlights and/or notes--------------------
def exportAnno(annodict,outdir,action,separate,verbose=True):
    '''Export highlights and/or notes to txt file

    <annodict>: dict, keys: PDF file paths,
                      values: [highlight_list, note_list], 
                      see doc in _exportAnnoFile().
    <outdir>: str, path to output folder.
    <action>: list, actions from cli arguments.
    <separate>: bool, True: save annotations if each PDF separately.
                      False: save annotations from all PDFs to a single file.

    Calls _exportAnnoFile() for core processes.
    '''

    #-----------Export all to a single file-----------
    if not separate:
            
        if 'm' in action and 'n' not in action:
            fileout='Mendeley_highlights.txt'
        elif 'n' in action and 'm' not in action:
            fileout='Mendeley_notes.txt'
        elif 'm' in action and 'n' in action:
            fileout='Mendeley_annotations.txt'

        abpath_out=os.path.join(outdir,fileout)
        if os.path.isfile(abpath_out):
            os.remove(abpath_out)

        if verbose:
            print('\n# <mennoteexport>: Exporting all annotations to:\n')
            print(abpath_out)

    #----------------Loop through files----------------
    for fii,annoii in annodict.items():

        fnameii=os.path.basename(fii)
        fnameii=os.path.splitext(fnameii)[0]

        #---------Get individual output if needed---------
        if separate:
            if 'm' in action and 'n' not in action:
                fileout='Highlights_%s.txt' %fnameii
            elif 'n' in action and 'm' not in action:
                fileout='Notes_%s.txt' %fnameii
            elif 'm' in action and 'n' in action:
                fileout='Anno_%s.txt' %fnameii
            abpath_out=os.path.join(outdir,fileout)
            if os.path.isfile(abpath_out):
                os.remove(abpath_out)

            if verbose:
                print('\n# <mennoteexport>: Exporting annotations to:\n')
                print(abpath_out)

        #----------------------Export----------------------
        try:
            _exportAnnoFile(abpath_out,annoii)
        except:
            annofaillist.append(fnameii)
            continue




#--------------------Check folder names in database--------------------
def checkFolder(db,folder,verbose=True):
    '''Check folder names in database

    '''

    if folder is None:
        return

    query=\
    '''SELECT Documents.title,
              DocumentFolders.folderid,
              Folders.name
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       LEFT JOIN Folders
           ON Folders.id=DocumentFolders.folderid
    '''

    fstr=['(Folders.name="%s")' %ii for ii in folder]
    fstr='WHERE '+' OR '.join(fstr)
    query=query+' '+fstr

    #------------------Get file meta data------------------
    ret=db.execute(query)
    data=ret.fetchall()

    if len(data)==0:
        print("Given folder name not found in database or folder is empty.")
        return 1
    else:
        return 0

        

    



#----------------Bulk export to pdf----------------
def main(dbfin, outdir, action, folder, overwrite, allpages,\
        separate,verbose=True):

    
    db = sqlite3.connect(dbfin)

    if verbose:
        print('\n# <mennoteexport>: Connected to database:\n')
        print(dbfin)

    #----------------Check folder name----------------
    if folder is not None:
        checkok=checkFolder(db,folder)
        if checkok!=0:
            return

    #------------------Get highlights------------------
    annotations = getHighlights(db,None,folder)

    #--------------------Get notes--------------------
    annotations = getNotes(db, annotations, folder)

    #-----------------Close connection-----------------
    if verbose:
        print('\n# <mennoteexport>: Drop connection to database:\n')
    db.close()

    if len(annotations)==0:
        print('\n# <mennoteexport>: No annotations found. Quit.\n')
        #sys.exit(0)
        return 1


    #---------------Reformat annotations---------------
    annotations=reformatAnno(annotations)

    #---------------------Loop through files---------------------
    toexports={}
    global exportfaillist
    global annofaillist
    exportfaillist=[]
    annofaillist=[]

    total=len(annotations)
    for ii in xrange(total):
        annoii=annotations[ii]
        fii=annoii.path
        fnameii=os.path.splitext(os.path.basename(fii))[0]

        if verbose:
            print('\n'+int(30)*'-'+str(ii+1)+'/'+str(total)+int(30)*'-')
            print('# <mennoteexport>: Processing file:\n')
            print(fnameii)

        if 'e' in action:
            try:
                exportPdf(fii,os.path.join(outdir,os.path.basename(fii)),\
                        annoii,overwrite,allpages,verbose)
            except:
                exportfaillist.append(fii)

        if 'm' in action:
            if verbose:
                print('\n# <mennoteexport>: Retrieving highlights...')
            try:
                hltexts=extracthl.extractHighlights(fii,annoii,verbose)
            except:
                annofaillist.append(fii)
                hltexts=[]
        else:
            hltexts=[]

        if 'n' in action:
            if verbose:
                print('\n# <mennoteexport>: Retrieving sticky notes...')
            try:
                nttexts=extractNotes(fii,annoii,verbose)
            except:
                annofaillist.append(fii)
                nttexts=[]
        else:
            nttexts=[]

        toexports[fii]=[hltexts,nttexts]

    #------------Export annotations to txt------------
    if 'm' in action or 'n' in action:
        exportAnno(toexports,outdir,action,separate)

        #--------Export annotations grouped by tags--------
        tagsdict=extracttags.groupByTags(toexports)
        extracttags.exportAnno(tagsdict,outdir,action,verbose)

    
    if len(exportfaillist)>0:
        print('\n\n\n'+'-'*int(70))
        print('\n# <mennoteexport>: Failed to export PDFs:')
        for failii in exportfaillist:
            print(failii)

    if len(annofaillist)>0:
        print('\n\n\n'+'-'*int(70))
        print('\n# <mennoteexport>: Failed to extract and export highlights/notes:')
        for failii in annofaillist:
            print(failii)

    if len(exportfaillist)==0 and len(annofaillist)==0:
        if verbose:
            print('\n# <mennoteexport>: All done.')

    return 0









#-----------------------Main-----------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=\
            'Export PDFs, highlights and notes from Mendeley database.')

    parser.add_argument('dbfile', type=str,\
            help='The Mendeley sqlite database file')
    parser.add_argument('outdir', type=str,\
            help='Target folder to save the outputs.')

    parser.add_argument('-e', '--export', dest='action',\
            action='append_const', \
            const='e',\
            help='''Bulk export all PDFs with highlights and notes.
            Can be used with -m and -n''')
    parser.add_argument('-m', '--markup', dest='action',\
            action='append_const', \
            const='m',\
        help='''Export highlights to a txt file: highlights.txt.
            Can be used with -e and -n.
                If used with -n, highlights and notes are combined
                in annotations.txt.''')
    parser.add_argument('-n', '--note', dest='action',\
            action='append_const', \
            const='n',\
        help='''Export notes to a txt file: notes.txt.
            Can be used with -e and -m.
                If used with -m, highlights and notes are combined
                in annotations.txt.''')

    parser.add_argument('-f', '--folder', dest='folder',\
            type=str, default=None, nargs=1, help='''Select a Mendeley folder to process.''')

    parser.add_argument('-w', '--overwrite', action='store_false',\
            help='''Do not overwrite any PDF files in target folder.
            Default to overwrite.''')
    parser.add_argument('-s', '--separate', action='store_true',\
            help='''Export annotations to a separate txt file
            for each PDF.
            Default to export all file annotations to a single file.''')
    parser.add_argument('-v', '--verbose', action='store_true',\
            default=True,\
            help='Print some texts.')

    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        sys.exit(1)

    dbfile = os.path.abspath(args.dbfile)
    outdir = os.path.abspath(args.outdir)

    main(dbfile,outdir,args.action,args.folder,\
            args.overwrite,True,args.separate,args.verbose)







