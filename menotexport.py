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

Update time: 2016-04-15 16:25:00.
'''

__version__='Menotexport v1.3'

#---------------------Imports---------------------
import sys,os
import sqlite3
import argparse
import pandas as pd
from lib import extracttags
from lib import extractnt
from lib import exportpdf
from lib import exportannotation
from lib import export2bib
from lib.tools import printHeader, printInd, printNumHeader
#from html2text import html2text
from bs4 import BeautifulSoup
from datetime import datetime

if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse


#-------Fetch a column from pandas dataframe-------
fetchField=lambda x, f: x[f].unique().tolist()



class FileAnno(object):

    def __init__(self,docid,meta,highlights=None,notes=None):
        '''Obj to hold annotations (highlights+notes) in a single PDF.
        '''

        self.docid=docid
        self.meta=meta
        self.highlights=highlights
        self.notes=notes
        self.path=meta['path']
        _dir, self.filename=os.path.split(self.path)
        if _dir=='/pseudo_path':
            self.hasfile=False
        else:
            self.hasfile=True

        if highlights is None:
            self.hlpages=[]
        elif type(highlights) is dict:
            self.hlpages=highlights.keys()
            self.hlpages.sort()
        elif type(highlights) is list:
            self.hlpages=[ii.page for ii in highlights]
            self.hlpages.sort()
        else:
            raise Exception("highlights type wrong")

        if notes is None:
            self.ntpages=[]
        elif type(notes) is dict:
            self.ntpages=notes.keys()
            self.ntpages.sort()
        elif type(notes) is list:
            self.ntpages=[ii.page for ii in notes]
            self.ntpages.sort()
        else:
            raise Exception("notes type wrong")
            

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


def getMetaData(db, docid):
    '''Get meta-data of a doc by documentId.
    '''

    query=\
    '''SELECT Documents.id,
              Documents.citationkey,
              Documents.title,
              Documents.issue,
              Documents.pages,
              Documents.publication,
              Documents.volume,
              Documents.year,
              Documents.doi,
              Documents.abstract,
              Documents.arxivId,
              Documents.chapter,
              Documents.city,
              Documents.country,
              Documents.edition,
              Documents.institution,
              Documents.isbn,
              Documents.issn,
              Documents.month,
              Documents.publisher,
              Documents.series,
              Documents.type,
              Documents.read,
              Documents.favourite,
              DocumentTags.tag,
              DocumentContributors.firstNames,
              DocumentContributors.lastName
       FROM Documents
       LEFT JOIN DocumentTags
           ON DocumentTags.documentId=Documents.id
       LEFT JOIN DocumentContributors
           ON DocumentContributors.documentId=Documents.id
    '''

    #------------------Get file meta data------------------
    ret=db.execute(query)
    data=ret.fetchall()
    fields=['docid','citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','publisher','series','type',\
            'read','favourite','tags','firstnames','lastname']

    df=pd.DataFrame(data=data,columns=fields)
    docdata=df[df.docid==docid]
    result={}
    for ff in fields:
        fieldii=fetchField(docdata,ff)
        result[ff]=fieldii[0] if len(fieldii)==1 else fieldii


    return result


#---------------Get file path of a PDF using documentId---------------
def getFilePath(db,docid,verbose=True):
    '''Get file path of a PDF using documentId
    '''

    query=\
    '''SELECT Files.localUrl, 
              DocumentFiles.hash,
              Documents.id
       FROM Files
       LEFT JOIN DocumentFiles
           ON DocumentFiles.hash=Files.hash
       LEFT JOIN Documents
           ON Documents.id=DocumentFiles.documentId
    '''

    ret=db.execute(query)
    data=ret.fetchall()
    df=pd.DataFrame(data=data,columns=['url','hash','docid'])

    #-----------------Search file path-----------------
    pathdata=df[df.docid==docid]
    if len(pathdata)==0:
        return None
    else:
        url=fetchField(pathdata,'url')[0]
        pth = converturl2abspath(url)
        return pth


def getHighlights(db, results=None, folderid=None,foldername=None):
    '''Extract the coordinates of highlights from the Mendeley database
    and put results into a dictionary.

    <db>: sqlite3.connection to Mendeley sqlite database.
    <results>: dict or None, optional dictionary to hold the results. 
    <folderid>: int, id of given folder. If None, don't do folder filtering.
    <foldername>: str, name of folder corresponding to <folderid>. Used to
                  populate meta data.

    Return: <results>: dictionary containing the query results, with
            the following structure:

            results={documentId1: {'highlights': {page1: [hl1, hl2,...],
                                                page2: [hl1, hl2,...],
                                                ...}
                                 'notes':      {page1: [nt1, nt2,...],
                                                page4: [nt1, nt2,...],
                                                ...}
                                 'meta':       {'title': title,
                                                'tags': [tag1, tag2,...],
                                                'cite': citationkey,
                                                'path': abspath,
                                                ...
                                                }
                     documentId2: ...
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
                    FileHighlights.color,
                    Folders.name,
                    DocumentFolders.folderid,
                    FileHighlights.documentId
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
    if folderid is not None:

        fstr='(Folders.id="%s")' %folderid
        query=query+' AND\n'+fstr

    if results is None:
        results={}

    #------------------Get highlights------------------
    ret = db.execute(query)

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[4], r[5]] 
        # [x1,y1,x2,y2], (x1,y1) being bottom-left,
        # (x2,y2) being top-right. Origin at bottom-left
        cdate = convert2datetime(r[6])
        color=r[7]
        folder=r[8]
        docid=r[10]
        hlight = {'rect': bbox,\
                  'cdate': cdate,\
                  'color': color,
                  'page':pg\
                  }

        #------------Save to dict------------
        if docid in results:
            if 'highlights' in results[docid]:
                if pg in results[docid]['highlights']:
                    results[docid]['highlights'][pg].append(hlight)
                else:
                    results[docid]['highlights'][pg]=[hlight,]
            else:
                results[docid]['highlights']={pg:[hlight,]}
        else:
            meta=getMetaData(db, docid)
            if meta['tags'] is None:
                tags=[folder,]
            elif type(meta['tags']) is list:
                tags=meta['tags']+[folder,]
            else:
                tags=[meta['tags'],folder]
            meta['tags']=tags
            meta['path']=pth
            meta['folder']='' if folder is None else foldername
            results[docid]={'highlights':{pg:[hlight,]}}
            results[docid]['meta']=meta

    return results


#-------------------Get sticky notes-------------------
def getNotes(db, results=None, folderid=None,foldername=None):
    '''Extract notes from the Mendeley database

    <db>: sqlite3.connection to Mendeley sqlite database.
    <results>: dict or None, optional dictionary to hold the results. 
    <folderid>: int, id of given folder. If None, don't do folder filtering.
    <foldername>: str, name of folder corresponding to <folderid>. Used to
                  populate meta data.

    Return: <results>: dictionary containing the query results. See
            more in the doc of getHighlights()
    Update time: 2016-04-12 20:39:15.
    '''

    query=\
    '''SELECT Files.localUrl, FileNotes.page,
                    FileNotes.x, FileNotes.y,
                    FileNotes.author, FileNotes.note,
                    FileNotes.modifiedTime,
                    Folders.name,
                    DocumentFolders.folderid,
                    FileNotes.documentId
            FROM Files
            LEFT JOIN FileNotes
                ON FileNotes.fileHash=Files.hash
            LEFT JOIN DocumentFolders
                ON DocumentFolders.documentId=FileNotes.documentId
            LEFT JOIN Folders
                ON Folders.id=DocumentFolders.folderid
            WHERE (FileNotes.page IS NOT NULL)
    '''

    if folderid is not None:
        fstr='(Folders.id="%s")' %folderid
        query=query+' AND\n'+fstr

    if results is None:
        results={}

    #------------------Get notes------------------
    ret = db.execute(query)

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
   
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30] 
        # needs a rectangle however size does not matter
        author=r[4]
        txt = r[5]
        cdate = convert2datetime(r[6])
        folder=r[7]
        docid=r[9]
        note = {'rect': bbox,\
                'author':author,\
                'content':txt,\
                'cdate': cdate,\
                'page':pg\
                  }

        #------------Save to dict------------
        if docid in results:
            if 'notes' in results[docid]:
                if pg in results[docid]['notes']:
                    results[docid]['notes'][pg].append(note)
                else:
                    results[docid]['notes'][pg]=[note,]
            else:
                results[docid]['notes']={pg:[note,]}
        else:
            meta=getMetaData(db, docid)
            if meta['tags'] is None:
                tags=[folder,]
            elif type(meta['tags']) is list:
                tags=meta['tags']+[folder,]
            else:
                tags=[meta['tags'],folder]
            meta['tags']=tags
            meta['path']=pth
            meta['folder']='' if folder is None else foldername
            results[docid]={'notes':{pg:[note,]}}
            results[docid]['meta']=meta

    return results


#-------------------Get side-bar notes-------------------
def getDocNotes(db, results=None, folderid=None,foldername=None):
    '''Extract side-bar notes from the Mendeley database

    <db>: sqlite3.connection to Mendeley sqlite database.
    <results>: dict or None, optional dictionary to hold the results. 
    <folderid>: int, id of given folder. If None, don't do folder filtering.
    <foldername>: str, name of folder corresponding to <folderid>. Used to
                  populate meta data.

    Return: <results>: dictionary containing the query results. with
            See the doc in getHighlights().
    Update time: 2016-04-12 20:44:38.
    '''

    query=\
    '''SELECT DocumentNotes.text,
              DocumentNotes.documentId,
              DocumentNotes.baseNote,
              DocumentFolders.folderid,
              Folders.name,
              DocumentFiles.hash,
              Documents.title
            FROM DocumentNotes
            LEFT JOIN DocumentFolders
                ON DocumentFolders.documentId=DocumentNotes.documentId
            LEFT JOIN Folders
                ON Folders.id=DocumentFolders.folderid
            LEFT JOIN DocumentFiles
                ON DocumentFiles.documentId=DocumentNotes.documentId
            LEFT JOIN Documents
                ON Documents.id=DocumentNotes.documentId
            WHERE (DocumentNotes.documentId IS NOT NULL)
    '''

    if folderid is not None:
        fstr='(Folders.id="%s")' %folderid
        query=query+' AND\n'+fstr

    if results is None:
        results={}

    #------------------Get notes------------------
    ret = db.execute(query)

    for ii,r in enumerate(ret):
        docnote=r[0]
        docid=r[1]
        basenote=r[2]
        folder=r[4]
        #dochash=r[5]
        title=r[6]
        pg=1

        if docnote is not None and basenote is not None\
                and docnote!=basenote:
            docnote=basenote+'\n\n'+docnote

        #--------------------Parse html--------------------
        soup=BeautifulSoup(docnote,'html.parser')
        docnote=soup.get_text()
        '''
        parser=html2text.HTML2Text()
        parser.ignore_links=True
        docnote=parser.handle(docnote)
        '''

        # Try get file path
        pth=getFilePath(db,docid) or '/pseudo_path/%s.pdf' %title

        bbox = [50, 700, 80, 730] 
        # needs a rectangle however size does not matter
        note = {'rect': bbox,\
                'author':'Mendeley user',\
                'content':docnote,\
                'cdate': datetime.now(),\
                'page':pg\
                  }

        #-------------------Save to dict-------------------
        if docid in results:
            if 'notes' in results[docid]:
                if pg in results[docid]['notes']:
                    results[docid]['notes'][pg].insert(0,note)
                else:
                    results[docid]['notes'][pg]=[note,]
            else:
                results[docid]['notes']={pg:[note,]}
        else:
            meta=getMetaData(db, docid)
            if meta['tags'] is None:
                tags=[folder,]
            elif type(meta['tags']) is list:
                tags=meta['tags']+[folder,]
            else:
                tags=[meta['tags'],folder]
            meta['tags']=tags
            meta['path']=pth
            meta['folder']='' if folder is None else foldername
            results[docid]={'notes':{pg:[note,]}}
            results[docid]['meta']=meta


    return results


#-------------Reformat annotations to a list of FileAnnos-------------
def reformatAnno(annodict):
    '''Reformat annotations to a dict of FileAnnos

    <annodict>: dict, annotation dict. See doc in getHighlights().
    Return <annos>: dict, keys: documentId; value: FileAnno objs.
    '''
    result={}
    for kk,vv in annodict.items():
        annoii=FileAnno(kk,vv['meta'],\
            highlights=vv.get('highlights',{}),\
            notes=vv.get('notes',{}))
        result[kk]=annoii

    return result


#---------Get a list of doc meta-data not in annotation list----------
def getOtherDocs(db,folderid,foldername,annodocids,verbose=True):
    '''Get a list of doc meta-data not in annotation list.

    <annodocids>: list, doc documentId.
    '''

    folderdocids=getFolderDocList(db,folderid)
    if not set(annodocids).issubset(set(folderdocids)):
        raise Exception("Exception")
        
    #------Docids in folder and not in annodocids------
    otherdocids=set(folderdocids).difference((annodocids))
    otherdocids=list(otherdocids)

    #------------------Get meta data------------------
    result=[]
    for ii in otherdocids:
        docii=getMetaData(db,ii)
        docii['path']=getFilePath(db,ii) #Local file path, can be None
        docii['folder']=foldername
        result.append(docii)

    return result


#----------Get a list of docids from a folder--------------
def getFolderDocList(db,folderid,verbose=True):
    '''Get a list of docids from a folder
    '''

    query=\
    '''SELECT Documents.id,
              DocumentFolders.folderid,
              Folders.name
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       LEFT JOIN Folders
           ON Folders.id=DocumentFolders.folderid
    '''

    if folderid is not None:
        fstr='(Folders.id="%s")' %folderid
        fstr='WHERE '+fstr
        query=query+' '+fstr

    #------------------Get docids------------------
    ret=db.execute(query)
    data=ret.fetchall()
    df=pd.DataFrame(data=data,columns=['docid','folderid','folder'])
    docids=fetchField(df,'docid')

    return docids


#--------------Get folder id and name list in database----------------
def getFolderList(db,folder,verbose=True):
    '''Get folder id and name list in database

    <folder>: select folder from database.
              If None, select all folders/subfolders.
              If str, select folder <folder>, and all subfolders. If folder
              name conflicts, select the one with higher level.
              If a tuple of (id, folder), select folder with name <folder>
              and folder id <id>, to avoid name conflicts.

    Return: <folders>: list, with elements of (id, folder_tree).
            where <folder_tree> is a str of folder name with tree structure, e.g.
            test/testsub/testsub2.

    Update time: 2016-06-16 19:38:15.
    '''

    query=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
    '''

    #-----------------Get all folders-----------------
    ret=db.execute(query)
    data=ret.fetchall()
    df=pd.DataFrame(data=data,columns=['folderid','folder','parentID'])
    allfolderids=fetchField(df,'folderid')

    #---------------Select target folder---------------
    if folder is None:
        folderids=allfolderids
    if type(folder) is str:
        # Select the given folder, if more than 1 name match, select the
        # one with lowest parentID.
        seldf=df[df.folder==folder].sort_values('parentID')
        folderids=fetchField(seldf,'folderid')
    elif type(folder) is tuple or type(folder) is list:
        seldf=df[(df.folderid==folder[0]) & (df.folder==folder[1])]
        folderids=fetchField(seldf,'folderid')

    #----------------Get all subfolders----------------
    if folder is not None:
        folderids2=[]
        for ff in folderids:
            folderids2.append(ff)
            subfs=getSubFolders(df,ff)
            folderids2.extend(subfs)
    else:
        folderids2=folderids

    #---------------Remove empty folders---------------
    folderids2=[ff for ff in folderids2 if not isFolderEmpty(db,ff)]

    #---Get names and tree structure of all non-empty folders---
    folders=[]
    for ff in folderids2:
        folders.append(getFolderTree(df,ff))

    #----------------------Return----------------------
    if folder is None:
        return folders
    else:
        if len(folders)==0:
            print("Given folder name not found in database or folder is empty.")
            return []
        else:
            return folders


#--------------------Check a folder is empty or not--------------------
def isFolderEmpty(db,folderid,verbose=True):
    '''Check a folder is empty or not
    '''

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

    fstr='(Folders.id="%s")' %folderid
    fstr='WHERE '+fstr
    query=query+' '+fstr

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return True
    else:
        return False


#-------------------Get subfolders of a given folder-------------------
def getSubFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dataframe, contains all folders (including empty ones) id, name and parentID.
    <folderid>: int, folder id
    '''
    getParentId=lambda df,id: fetchField(df[df.folderid==id],'parentID')[0]
    results=[]

    for ii in range(len(df)):
        idii,fii,pii=df.loc[ii]

        cid=idii
        while True:
            pid=getParentId(df,cid)
            if pid==-1:
                break
            if pid==folderid:
                results.append(idii)
                break
            else:
                cid=pid

    results.sort()
    return results


#-------------Get folder tree structure of a given folder-------------
def getFolderTree(df,folderid,verbose=True):
    '''Get folder tree structure of a given folder

    <df>: dataframe, contains all folders (including empty ones) id, name and parentID.
    <folderid>: int, folder id
    '''

    getFolderName=lambda df,id: fetchField(df[df.folderid==id],'folder')[0]
    getParentId=lambda df,id: fetchField(df[df.folderid==id],'parentID')[0]

    folder=getFolderName(df,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=getParentId(df,cid)
        if pid==-1:
            break
        else:
            pfolder=getFolderName(df,pid)
            folder=u'%s/%s' %(pfolder,folder)
        cid=pid

    return folderid,folder



def extractAnnos(annotations,action,verbose):

    faillist=[]
    annotations2={}  #keys: docid, values: extracted annotations

    #-----------Loop through documents---------------
    num=len(annotations)
    docids=annotations.keys()
    for ii,idii in enumerate(docids):
        annoii=annotations[idii]
        fii=annoii.path
        fnameii=annoii.filename

        if verbose:
            printNumHeader('Processing file:',ii+1,num,3)
            printInd(fnameii,4)

        if 'm' in action:
            from lib import extracthl2

            try:
	        #------ Check if pdftotext is available--------
	        if extracthl2.checkPdftotext():
		    if verbose:
			printInd('Retrieving highlights using pdftotext ...',4,prefix='# <Menotexport>:')
                    hltexts=extracthl2.extractHighlights2(fii,annoii,verbose)
	        else:
		    if verbose:
			printInd('Retrieving highlights using pdfminer ...',4,prefix='# <Menotexport>:')
                    hltexts=extracthl2.extractHighlights(fii,annoii,verbose)
            except:
                faillist.append(fnameii)
                hltexts=[]
        else:
            hltexts=[]

        if 'n' in action:
            if verbose:
                printInd('Retrieving notes...',4,prefix='# <Menotexport>:')
            try:
                nttexts=extractnt.extractNotes(fii,annoii,verbose)
            except:
                faillist.append(fnameii)
                nttexts=[]
        else:
            nttexts=[]

        annoii.highlights=hltexts
        annoii.notes=nttexts
        annotations2[idii]=annoii

    return annotations2,faillist


        
def processFolder(db,outdir,annotations,folderid,foldername,allfolders,action,\
        separate,verbose):
    '''Process files/docs in a folder.

    <db>: sqlite database.
    <outdir>: str, output directory path.
    <annotations>: dict, keys: documentId; values: highlights, notes and meta.
                   See doc in getHighlights().
    <folderid>: int, folder id.
    <foldername>: string, folder name corresponding to <folderid>.
    <allfolders>: bool, user chooses to process all folders or one folder.
    <action>: list, possible elements: m, n, e, b.
    <separate>: bool, whether save one output for each file or all files.
    '''
    
    exportfaillist=[]
    annofaillist=[]
    bibfaillist=[]

    ishighlight=False
    isnote=False
    if 'm' in action or 'p' in action:
        ishighlight=True
    if 'n' in action or 'p' in action:
        isnote=True

    #------------Get raw annotation data------------
    if ishighlight:
        annotations = getHighlights(db,annotations,folderid,foldername)
    if isnote:
        annotations = getNotes(db, annotations, folderid,foldername)
        annotations = getDocNotes(db, annotations, folderid,foldername)

    if len(annotations)==0:
        print('\n# <Menotexport>: No annotations found in folder: %s' %foldername)
        if 'b' not in action and 'p' not in action:
            return exportfaillist,annofaillist,bibfaillist
    else:
        #---------------Reformat annotations---------------
        annotations=reformatAnno(annotations)

    #------Get other docs without annotations------
    otherdocs=getOtherDocs(db,folderid,foldername,annotations.keys())

    #--------Make subdir using folder name--------
    outdir_folder=os.path.join(outdir,foldername)
    if not os.path.isdir(outdir_folder):
        os.makedirs(outdir_folder)

    #-------------------Export PDFs-------------------
    if 'p' in action:
        if verbose:
            printHeader('Exporting annotated PDFs ...',2)

        if len(annotations)>0:
            flist=exportpdf.exportAnnoPdf(annotations,\
                    outdir_folder,verbose)
            exportfaillist.extend(flist)
    
        #--------Copy other PDFs to target location--------
        if verbose:
            printHeader('Exporting un-annotated PDFs ...',2)
        if len(otherdocs)>0:
            flist=exportpdf.copyPdf(otherdocs,outdir_folder,verbose)
            exportfaillist.extend(flist)

    #----------Extract annotations from PDFs----------
    if len(annotations)>0:
        if verbose:
            printHeader('Extracting annotations from PDFs ...',2)
        annotations,flist=extractAnnos(annotations,action,verbose)
        annofaillist.extend(flist)

    #------------Export annotations to txt------------
    if ('m' in action or 'n' in action) and len(annotations)>0:
        if verbose:
            printHeader('Exporting annotations to text file...',2)
        flist=exportannotation.exportAnno(annotations,outdir_folder,action,\
                separate,verbose)
        annofaillist.extend(flist)

        #--------Export annotations grouped by tags--------
        tagsdict=extracttags.groupByTags(annotations)
        extracttags.exportAnno(tagsdict,outdir_folder,action,verbose)

    #----------Export meta and anno to bib file----------
    if 'b' in action:

        if verbose:
            printHeader('Exporting meta-data and annotations to .bib file...',2)

        bibfolder=outdir if allfolders else outdir_folder
        isfile=True if 'p' in action else False

        #-----------Export docs with annotations-----------
        if len(annotations)>0:
            # <outdir> is the base folder to save outputs, specified by user
            # <bibfolder> is the folder to save .bib file, which is <outdir> if <allfolders> is True,
            # or <outdir>/<folder_tree> otherwise.
            flist=export2bib.exportAnno2Bib(annotations,outdir,bibfolder,allfolders,isfile,verbose)
            bibfaillist.extend(flist)

        #------Export other docs without annotations------
        if len(otherdocs)>0:
            flist=export2bib.exportDoc2Bib(otherdocs,outdir,bibfolder,allfolders,isfile,verbose)
            bibfaillist.extend(flist)



    return exportfaillist,annofaillist,bibfaillist
    


#----------------Bulk export to pdf----------------
def main(dbfin,outdir,action,folder,separate,verbose=True):
    
    try:
        db = sqlite3.connect(dbfin)
        if verbose:
            printHeader('Connected to database:')
            printInd(dbfin,2)
    except:
        printHeader('Failed to connect to database:')
        printInd(dbfin)
        return 1

    #----------------Get folder list----------------
    folderlist=getFolderList(db,folder)
    allfolders=True if folder is None else False
    if len(folderlist)==0:
        return 1

    #---------------Loop through folders---------------
    exportfaillist=[]
    annofaillist=[]
    bibfaillist=[]

    for ii,folderii in enumerate(folderlist):
        fidii,fnameii=folderii
        if verbose:
            printNumHeader('Processing folder: "%s"' %fnameii,\
                    ii+1,len(folderlist),1)
        annotations={}
        exportfaillistii,annofaillistii,bibfaillistii=processFolder(db,outdir,annotations,\
            fidii,fnameii,allfolders,action,separate,verbose)

        exportfaillist.extend(exportfaillistii)
        annofaillist.extend(annofaillistii)
        bibfaillist.extend(bibfaillistii)

    #-----------------Close connection-----------------
    if verbose:
        printHeader('Drop connection to database:')
    db.close()

    #------------------Print summary------------------
    exportfaillist=list(set(exportfaillist))
    annofaillist=list(set(annofaillist))
    bibfaillist=list(set(bibfaillist))

    printHeader('Summary',1)
    if len(exportfaillist)>0:
        printHeader('Failed to export PDFs:',2)
        for failii in exportfaillist:
            printInd(failii,2)

    if len(annofaillist)>0:
        printHeader('Failed to extract and export highlights/notes:',2)
        for failii in annofaillist:
            printInd(failii,2)

    if len(bibfaillist)>0:
        printHeader('Failed to export to .bib files:',2)
        for failii in bibfaillist:
            printInd(failii,2)

    if len(exportfaillist)==0 and len(annofaillist)==0 and len(bibfaillist)==0:
        if verbose:
            printHeader('All done.',2)

    return 0









#-----------------------Main-----------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=\
            'Export PDFs, highlights and notes from Mendeley database.')

    parser.add_argument('dbfile', type=str,\
            help='The Mendeley sqlite database file')
    parser.add_argument('outdir', type=str,\
            help='Target folder to save the outputs.')

    parser.add_argument('-p', '--pdf', dest='action',\
            action='append_const', \
            const='p',\
            help='''Bulk export all PDFs (with highlights and notes if they have any).
            Can be used with -m, -n and -b''')
    parser.add_argument('-m', '--markup', dest='action',\
            action='append_const', \
            const='m',\
        help='''Export highlights to a txt file: highlights.txt.
            Can be used with -p, -n and -b.
                If used with -n, highlights and notes are combined
                in annotations.txt.''')
    parser.add_argument('-n', '--note', dest='action',\
            action='append_const', \
            const='n',\
        help='''Export notes to a txt file: notes.txt.
            Can be used with -p, -m and -b.
                If used with -m, highlights and notes are combined
                in annotations.txt.''')
    parser.add_argument('-b', '--bib', dest='action',\
            action='append_const', \
            const='b',\
        help='''Export all meta-data and annotations to .bib files.
            Can be used with -p, -m and -n.
            If a folder is specified via the -f (--folder) option,
            save the .bib file into a sub-directory named after <folder>.
            If choose to process all folders, save the .bib file
            to <outdir>.''')

    parser.add_argument('-f', '--folder', dest='folder',\
            type=str, default=None, help='''Select a Mendeley folder to process.
            If not given, process all folders in the library. In such case,
            the folder structure will be preserved by creating sub-directories.''')

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
        #parser.print_help()
        sys.exit(1)

    dbfile = os.path.abspath(args.dbfile)
    outdir = os.path.abspath(args.outdir)

    main(dbfile,outdir,args.action,args.folder,\
            args.separate,args.verbose)







