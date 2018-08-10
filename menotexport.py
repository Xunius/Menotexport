#!/usr/bin/python
'''
- Bulk export annotated PDFs from Mendeley, with notes and highlights.
- Extract mendeley notes and highlights and save into text file(s).
- Group highlights and notes by tags, and export to a text file.
- PDFs without annotations are also exported.
- Export meta-data and annotations to .bib file, in a default format or in one suitable
  for Zotero import.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-15 16:25:00.
Update time: 2016-06-22 16:26:11.
Update time: 2018-06-24 13:21:26.
Update time: 2018-07-28 19:46:44.
Update time: 2018-08-06 21:42:33.

TODO: 

    * add python 3 compatibility. If seems that pdfminer support 3 now:
    https://github.com/pdfminer/pdfminer.six
    * Possible to remove pandas dependency? -- Done in v1.5.1
    * multi-thread or -process something to speed up

'''

__version__='Menotexport v1.5.1'

#---------------------Imports---------------------
import sys,os
import sqlite3
import argparse
from lib import extracttags
from lib import extractnt
from lib import exportpdf
from lib import exportannotation
from lib import export2bib
from lib import export2ris
from lib import extracthl2
from lib.tools import printHeader, printInd, printNumHeader, makedirs
#from html2text import html2text
from bs4 import BeautifulSoup
from datetime import datetime
import re

if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse


#---------Regex pattern for matching dois---------
DOI_PATTERN=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
        re.DOTALL|re.UNICODE)

# Sometimes citation imported via a .bib or .ris file may contain
# a note field (`annote = {{some note}} `for .bib, `N1 - some note` for .ris).
# It can be doi strings:
#    * doi: 10.1021/ed020p517.1
#    * 10.1021/ed020p517.1
# It can also be ISBN strings: e.g. ISBN 978..... 
# It can also be PMID strings: e.g. PMID: xxxx 
# It could be something else, whatever the citation provider decides to put in.
# So to distinguish them from actuall notes made by users, below is a list
# of regex patterns trying to catch some recognizable patterns and exclude
# them from the notes.

NOTE_EXCLUDE_PATTERNS=[
        DOI_PATTERN,
        ]




class DocAnno(object):
    def __init__(self,docid,meta,highlights=None,notes=None):
        '''Obj to hold annotations (highlights+notes) in a doc.
        '''

        self.docid=docid
        self.meta=meta

        # Get file paths and names, a doc can have multiple files associated
        self.path=meta['path'] # always a list if not None
        if self.path is None:
            self.hasfile=False
            self.filename=None
            self.path=[None,]  # if DocNotes exists but no file, to make
            # the iteration below possible
        else:
            self.hasfile=True
            self.filename=[os.path.split(pii)[1] for pii in self.path]

        #----------Create a fileanno obj for each file----------
        self.file_annos={}

        if len(self.path)>1:
            self.has_multifile=True
        else:
            self.has_multifile=False

        for ii, pii in enumerate(self.path):
            hlii=highlights.get(pii,{})
            ntii=notes.get(pii,{})
            metaii=meta.copy()
            metaii['path']=pii

            annoii=FileAnno(docid,metaii,highlights=hlii,notes=ntii)
            self.file_annos[pii]=annoii


class FileAnno(object):

    def __init__(self,docid,meta,highlights=None,notes=None):
        '''Obj to hold annotations (highlights+notes) in a single PDF.
        '''

        self.docid=docid
        self.meta=meta
        self.highlights=highlights
        self.notes=notes

        self.path=meta['path'] # a string or None
        if self.path is None:
            self.hasfile=False
            self.filename=None
        else:
            self.hasfile=True
            self.filename=os.path.split(self.path)[1]

        if highlights is None:
            self.hlpages=[]
        elif isinstance(highlights, dict):
            self.hlpages=highlights.keys()
            self.hlpages.sort()
        else:
            raise Exception("highlights type wrong")

        if notes is None:
            self.ntpages=[]
        elif isinstance(notes, dict):
            self.ntpages=notes.keys()
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


def getUserName(db):
    '''Query db to get user name'''

    query=\
    '''SELECT Profiles.firstName, Profiles.lastName
    FROM Profiles WHERE Profiles.isSelf="true"
    '''
    ret=db.execute(query).fetchall()
    return ' '.join(filter(None,ret[0]))


def getProfileNames(db):
    '''Get user (including co-authors) names'''

    query =\
    '''SELECT Profiles.uuid,
              Profiles.firstName,
              Profiles.lastName
            FROM Profiles
    '''
    ret=db.execute(query).fetchall()
    data=dict([(ii[0],' '.join(filter(None,ii[1:]))) for ii in ret])
    return data


def getMetaData(db, docid):
    '''Get meta-data of a doc by documentId.
    '''

    # fetch column from Document table
    query_base=\
    '''SELECT Documents.%s
       FROM Documents
       WHERE (Documents.id=%s)
    '''

    query_tags=\
    '''
    SELECT DocumentTags.tag
    FROM DocumentTags
    WHERE (DocumentTags.documentId=%s)
    ''' %docid

    query_firstnames=\
    '''
    SELECT DocumentContributors.firstNames
    FROM DocumentContributors
    WHERE (DocumentContributors.documentId=%s)
    ''' %docid

    query_lastnames=\
    '''
    SELECT DocumentContributors.lastName
    FROM DocumentContributors
    WHERE (DocumentContributors.documentId=%s)
    ''' %docid

    query_keywords=\
    '''
    SELECT DocumentKeywords.keyword
    FROM DocumentKeywords
    WHERE (DocumentKeywords.documentId=%s)
    ''' %docid

    query_folder=\
    '''
    SELECT Folders.name
    FROM Folders
       LEFT JOIN DocumentFolders
           ON Folders.id=DocumentFolders.folderid
    WHERE (DocumentFolders.documentId=%s)
    ''' %docid

    def fetchField(db,query):
        aa=db.execute(query).fetchall()
        bb=[ii[0] for ii in aa]
        if len(bb)==1:
            return bb[0]
        elif len(bb)==0:
            return None
        else:
            return bb

    #------------------Get file meta data------------------
    fields=['id','citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','day','publisher','series','type',\
            'read','favourite']

    result={}

    # query single-worded fields, e.g. year, city
    for kii in fields:
        vii=fetchField(db,query_base %(kii,docid))
        result[kii]=vii

    result['tags']=fetchField(db,query_tags)
    result['firstnames']=fetchField(db,query_firstnames)
    result['lastname']=fetchField(db,query_lastnames)
    result['keywords']=fetchField(db,query_keywords)
    result['folder']=fetchField(db,query_folder)

    #-----------------Append user name-----------------
    result['user_name']=getUserName(db)

    #------------------Add local url------------------
    result['path']=getFilePath(db,docid)  # None or list

    #-----Add folder to tags, if not there already-----
    folder=result['folder']
    result['folder']=folder or 'Canonical' # if no folder name, a canonical doc
    tags=result['tags']
    if folder is not None:
        if tags is None:
            if isinstance(folder,list):
                tags=folder
            else:
                tags=[folder,]
        elif isinstance(tags,list) and isinstance(folder,list):
            tags.extend(folder)
            tags=list(set(tags))
        elif isinstance(tags,list) and not isinstance(folder,list):
            tags.append(folder)
            tags=list(set(tags))
        elif not isinstance(tags,list) and isinstance(folder,list):
            tags=folder+[tags,]
            tags=list(set(tags))
        elif not isinstance(tags,list) and not isinstance(folder,list):
            tags=[tags, folder]
            tags=list(set(tags))
        else:
            # there shouldn't be anything else, should it?
            #pass
            tags=[]
    else:
        tags=tags or []

    if not isinstance(tags,list):
        tags=[tags,]
    tags.sort()

    result['tags']=tags

    return result


#---------------Get file path of PDF(s) using documentId---------------
def getFilePath(db,docid,verbose=True):
    '''Get file path of PDF(s) using documentId

    Return <pth>: None or a LIST of file paths. If a single path, a len-1 list.
    '''

    query=\
    '''SELECT Files.localUrl
       FROM Files
       LEFT JOIN DocumentFiles
           ON DocumentFiles.hash=Files.hash
       LEFT JOIN Documents
           ON Documents.id=DocumentFiles.documentId
       WHERE (Documents.id=%s)
    ''' %docid

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return None
    else:
        pth=[converturl2abspath(urlii[0]) for urlii in data]
        return pth


#----------Extract highlights coordinates and related meta data-------
def getHighlights(db,filterdocid,results=None):
    '''Extract highlights coordinates and related meta data.

    <db>: sqlite3.connection to Mendeley sqlite database.
    <filterdocid>: int, id of document to query.
    <results>: dict or None, optional dictionary to hold the results. If None,
               create a new empty dict.

    Return: <results>: dictionary containing the query results, with
            the following structure:

            results={documentId1:
                {'highlights': {path1: {page1: [hl1, hl2,...],
                                        page2: [hl1, hl2,...],
                                        ...}
                                path2: {page1: [hl1, hl2,...],
                                        page2: [hl1, hl2,...],
                                        ...}
                                }
                 'notes': {path1: {page1: [nt1, nt2,...],
                                   page4: [nt1, nt2,...],
                                   ...}
                           ...}
                 'meta': {'title': title,
                          'tags': [tag1, tag2,...],
                          'cite': citationkey,
                           ...
                          }
                     documentId2: ...
                    }

            where hl1={'rect': bbox,\
                       'cdate': cdate,\
                       'color': color,
                       'page':pg,
                        'author':'highlight author',\
                       'path':pth
                      }
                  note={'rect': bbox,\
                        'author':'note author',\
                        'content':docnote,\
                        'cdate': datetime.now(),\
                        'page':pg,
                        'path':pth
                        }
    
    Update time: 2016-02-24 00:36:33.
    Update time: 2018-06-27 21:45:27.
    Update time: 2018-07-28 20:00:11.
    '''

    # For Mendeley versions newer than 1.16.1 (include), with highlight colors
    query_new =\
    '''SELECT Files.localUrl, FileHighlightRects.page,
                    FileHighlightRects.x1, FileHighlightRects.y1,
                    FileHighlightRects.x2, FileHighlightRects.y2,
                    FileHighlights.createdTime,
                    FileHighlights.author,
                    Profiles.firstName,
                    Profiles.lastName,
                    FileHighlights.color
            FROM Files
            LEFT JOIN FileHighlights
                ON FileHighlights.fileHash=Files.hash
            LEFT JOIN FileHighlightRects
                ON FileHighlightRects.highlightId=FileHighlights.id
            LEFT JOIN Profiles
                ON Profiles.uuid=FileHighlights.profileUuid
            WHERE (FileHighlightRects.page IS NOT NULL) AND
            (FileHighlights.documentId=%s)
    ''' %filterdocid

    # For Mendeley versions older than 1.16.1, no highlight colors
    query_old =\
    '''SELECT Files.localUrl, FileHighlightRects.page,
                    FileHighlightRects.x1, FileHighlightRects.y1,
                    FileHighlightRects.x2, FileHighlightRects.y2,
                    FileHighlights.createdTime,
                    FileHighlights.author,
                    Profiles.firstName,
                    Profiles.lastName
            FROM Files
            LEFT JOIN FileHighlights
                ON FileHighlights.fileHash=Files.hash
            LEFT JOIN FileHighlightRects
                ON FileHighlightRects.highlightId=FileHighlights.id
            LEFT JOIN Profiles
                ON Profiles.uuid=FileHighlights.profileUuid
            WHERE (FileHighlightRects.page IS NOT NULL) AND
            (FileHighlights.documentId=%s)
    ''' %filterdocid

    if results is None:
        results={}

    #------------------Get highlights------------------
    try:
	ret = db.execute(query_new)
	hascolor=True
    except:
	ret = db.execute(query_old)
	hascolor=False

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[4], r[5]]
        # [x1,y1,x2,y2], (x1,y1) being bottom-left,
        # (x2,y2) being top-right. Origin at bottom-left.
        # Fix incorrect storage ordering in Mendeley:
        if bbox[0] > bbox[2]: bbox[0], bbox[2] = bbox[2], bbox[0]
        if bbox[1] > bbox[3]: bbox[1], bbox[3] = bbox[3], bbox[1]
        cdate = convert2datetime(r[6])

        # Changes suggested by matteosecli: retrieve author of highlight:
        author=r[7]
        if not author.strip():
            author=' '.join(filter(None,r[8:10]))

        color=r[10] if hascolor else None

        hlight = {'rect': bbox,\
                  'cdate': cdate,\
                  'color': color,
                  'page': pg,
                  'author': author,
                  'path': pth   # distinguish between multi-attachments
                  }

        #------------Save to dict------------
        # any better way of doing this sht?
        if filterdocid in results:
            if 'highlights' in results[filterdocid]:
                if pth in results[filterdocid]['highlights']:
                    if pg in results[filterdocid]['highlights'][pth]:
                        results[filterdocid]['highlights'][pth][pg].append(hlight)
                    else:
                        results[filterdocid]['highlights'][pth][pg]=[hlight,]
                else:
                    results[filterdocid]['highlights'][pth]={pg:[hlight,]}
            else:
                results[filterdocid]['highlights']={pth:{pg:[hlight,]}}
        else:
            results[filterdocid]={'highlights':{pth:{pg:[hlight,]}}}

    return results


#-------------------Get sticky notes-------------------
def getNotes(db,filterdocid,results=None):
    '''Extract notes and related meta data

    <db>: sqlite3.connection to Mendeley sqlite database.
    <filterdocid>: int, id of document to query.
    <results>: dict or None, optional dictionary to hold the results. If None,
               create a new empty dict.

    Return: <results>: dictionary containing the query results. See
            more in the doc of getHighlights()

    Update time: 2016-04-12 20:39:15.
    Update time: 2018-06-27 21:52:04.
    Update time: 2018-07-28 20:01:40.
    '''

    query=\
    '''SELECT Files.localUrl, FileNotes.page,
                    FileNotes.x, FileNotes.y,
                    FileNotes.note,
                    FileNotes.modifiedTime,
                    FileNotes.author,
                    Profiles.firstName,
                    Profiles.lastName
            FROM Files
            LEFT JOIN FileNotes
                ON FileNotes.fileHash=Files.hash
            LEFT JOIN Profiles
                ON Profiles.uuid=FileNotes.profileUuid
            WHERE (FileNotes.page IS NOT NULL) AND
            (FileNotes.documentId=%s)
    ''' %filterdocid

    if results is None:
        results={}

    #------------------Get notes------------------
    ret = db.execute(query)

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30]
        # needs a rectangle, size does not matter

        txt = r[4]
        cdate = convert2datetime(r[5])

        # Changes suggested by matteosecli: retrieve author of note:
        author=r[6]
        if not author.strip():
            author=' '.join(filter(None,r[7:9]))

        note = {'rect': bbox,\
                'author':author,\
                'content':txt,\
                'cdate': cdate,\
                'page':pg,
                'path':pth,
                'isgeneralnote': False
                  }

        #------------Save to dict------------
        if filterdocid in results:
            if 'notes' in results[filterdocid]:
                if pth in results[filterdocid]['notes']:
                    if pg in results[filterdocid]['notes'][pth]:
                        results[filterdocid]['notes'][pth][pg].append(note)
                    else:
                        results[filterdocid]['notes'][pth][pg]=[note,]
                else:
                    results[filterdocid]['notes'][pth]={pg:[note,]}
            else:
                results[filterdocid]['notes']={pth:{pg:[note,]}}
        else:
            results[filterdocid]={'notes':{pth:{pg:[note,]}}}


    return results


#-------------------Get side-bar notes-------------------
def getDocNotes(db,filterdocid,results=None):
    '''Extract side-bar notes and related meta data

    <db>: sqlite3.connection to Mendeley sqlite database.
    <filterdocid>: int, id of document to query.
    <results>: dict or None, optional dictionary to hold the results. If None,
               create a new empty dict.

    Return: <results>: dictionary containing the query results. with
            See the doc in getHighlights().

    Update time: 2016-04-12 20:44:38.
    Update time: 2018-06-27 21:56:51.
    Update time: 2018-07-28 20:02:10.
    '''

    # Some versions of Mendeley saves notes in DocumentsNotes
    query=\
    '''SELECT DocumentNotes.text,
              DocumentNotes.documentId,
              DocumentNotes.baseNote
            FROM DocumentNotes
            WHERE (DocumentNotes.documentId IS NOT NULL) AND
            (DocumentNotes.documentId=%s)
    ''' %filterdocid

    # Some versions (not sure which exactly) of Mendeley saves
    # notes in Documents.note
    query2=\
    '''SELECT Documents.note
            FROM Documents
            WHERE (Documents.note IS NOT NULL) AND
            (Documents.id=%s)
    ''' %filterdocid

    # regex to transform Mendeley's old note formatting to html
    # e.g. <m:bold>Bold</m:bold>  to <bold>Bold</bold>
    pattern=re.compile(r'<(/?)m:(bold|italic|underline|center|left|right|linebreak)(/?)>',
            re.DOTALL | re.UNICODE)
    subfunc=lambda match: u'<%s%s%s>' %match.groups()

    if results is None:
        results={}

    #------------------Get notes------------------
    ret=[]
    try:
        ret1 = db.execute(query).fetchall()
        ret.extend(ret1)
    except:
        pass
    try:
        ret2 = db.execute(query2).fetchall()
        ret.extend(ret2)
    except:
        pass
    username=getUserName(db)

    for ii,rii in enumerate(ret):
        docnote=rii[0]
        if len(docnote)==0:
            # skip u''
            continue

        # skip things that are not user notes. See def of NOTE_EXCLUDE_PATTERNS
        skip=False
        for patternii in NOTE_EXCLUDE_PATTERNS:
            if patternii.match(docnote) is not None:
                skip=True
                break

        if skip:
            continue

        docid=filterdocid
        try:
            basenote=rii[2]
        except:
            basenote=None
        pg=1

        if docnote is not None and basenote is not None\
                and docnote!=basenote:
            docnote=basenote+'\n\n'+docnote

        #--------Convert old <m:tag> to html <tag>--------
        docnote=re.sub(pattern,subfunc,docnote)

        #--------------------Parse html--------------------
        soup=BeautifulSoup(docnote,'html.parser')
        # replace <br> tags with newline
        for br in soup.find_all('br'):
            br.replace_with('\n')
        docnote=soup.get_text()
        '''
        parser=html2text.HTML2Text()
        parser.ignore_links=True
        docnote=parser.handle(docnote)
        '''

        # Try get file path
        #pth=getFilePath(db,docid) or '/pseudo_path/%s.pdf' %title
        pth=getFilePath(db,docid) # a list, could be more than 1, or None
        # If no attachment, use None as path
        if pth is None:
            # make it compatible with the for loop below
            pth=[None,]

        bbox = [50, 700, 80, 730] 
        # needs a rectangle, size does not matter
        note = {'rect': bbox,
                'author': username,
                'content':docnote,
                'cdate': datetime.now(),
                'page':pg,
                'path':pth,
                'isgeneralnote': True
                  }

        #-------------------Save to dict-------------------
        # if multiple attachments, add to each of them
        for pthii in pth:
            if docid in results:
                if 'notes' in results[docid]:
                    if pthii in results[docid]['notes']:
                        if pg in results[docid]['notes'][pthii]:
                            results[docid]['notes'][pthii][pg].insert(0,note)
                        else:
                            results[docid]['notes'][pthii][pg]=[note,]
                    else:
                        results[docid]['notes'][pthii]={pg:[note,]}
                else:
                    results[docid]['notes']={pthii:{pg:[note,]}}
            else:
                results[docid]={'notes':{pthii:{pg:[note,]}}}


    return results


#-------------Reformat annotations to a dict of DocAnno objs-------------
def reformatAnno(annodict):
    '''Reformat annotations to a dict of DocAnno objs

    <annodict>: dict, annotation dict. See doc in getHighlights().
    Return <result>: dict, keys: documentId; value: DocAnno objs.
    '''
    result={}
    for kk,vv in annodict.items():
        annoii=DocAnno(kk,vv['meta'],\
            highlights=vv.get('highlights',{}),\
            notes=vv.get('notes',{}))
        result[kk]=annoii

    return result


def getOtherDocs(db,folderid,annodocids,verbose=True):
    '''Get a list of doc meta-data not in annotation list.

    <annodocids>: list, doc documentId.
    Deprecated. No longer in use.
    '''

    folderdocids=getFolderDocList(db,folderid)
    if not set(annodocids).issubset(set(folderdocids)):
        raise Exception("Exception")
        
    #------Docids in folder and not in annodocids------
    otherdocids=set(folderdocids).difference((annodocids))
    otherdocids=list(otherdocids)
    otherdocids.sort()

    #------------------Get meta data------------------
    result=[]
    for ii in otherdocids:
        docii=getMetaData(db,ii)
        #docii['path']=getFilePath(db,ii) #Local file path, can be None
        #docii['folder']=foldername
        result.append(docii)

    return result


#---------Get a list of doc meta-data not in annotation list----------
def getOtherCanonicalDocs(db,alldocids,annodocids,verbose=True):
    '''Get a list of doc meta-data not in annotation list.

    <annodocids>: list, doc documentId.
    Deprecated, no longer in use.
    '''

    #------Docids in folder and not in annodocids------
    otherdocids=set(alldocids).difference((annodocids))
    otherdocids=list(otherdocids)

    #------------------Get meta data------------------
    result=[]
    for ii in otherdocids:
        docii=getMetaData(db,ii)
        #docii['path']=getFilePath(db,ii) #Local file path, can be None
        docii['folder']='Canonical'
        result.append(docii)

    return result


#----------Get a list of docids from a folder--------------
def getFolderDocList(db,folderid,verbose=True):
    '''Get a list of docids from a folder

    Update time: 2018-07-28 20:11:09.
    '''

    query=\
    '''SELECT Documents.id
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       WHERE (DocumentFolders.folderid=%s)
    ''' %folderid

    ret=db.execute(query)
    data=ret.fetchall()
    docids=[ii[0] for ii in data]
    docids.sort()
    return docids



def getCanonicals(db,verbose=True):

    query=\
    '''SELECT Documents.id
       FROM Documents
       LEFT JOIN DocumentFolders
           ON DocumentFolders.documentId=Documents.id
       WHERE (DocumentFolders.folderId IS NULL)
    '''

    ret=db.execute(query)
    data=ret.fetchall()
    return [int(ii[0]) for ii in data]


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

    # get all folders with id, name, parentid
    query=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
    '''
    # get folder by name
    query1=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
       WHERE (Folders.name="%s")
    '''%folder

    #-----------------Get all folders-----------------
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    df=dict([(ii[0],ii[1:]) for ii in data])

    allfolderids=[ii[0] for ii in data]

    #---------------Select target folder---------------
    if folder is None:
        folderids=allfolderids
    if type(folder) is str:
        folderids=db.execute(query1).fetchall()
        folderids=[ii[0] for ii in folderids]
    elif isinstance(folder, (tuple,list)):
        # get folder from gui
        #seldf=df[(df.folderid==folder[0]) & (df.folder==folder[1])]
        #folderids=fetchField(seldf,'folderid')
        folderids=[folder[0]]

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

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getParentId=lambda df,id: df[id][1]
    results=[]

    for idii in df:
        fii,pii=df[idii]
        cid=idii
        while True:
            pid=getParentId(df,cid)
            if pid==-1 or pid==0:
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

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getFolderName=lambda df,id: df[id][0]
    getParentId=lambda df,id: df[id][1]

    folder=getFolderName(df,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=getParentId(df,cid)
        if pid==-1 or pid==0:
            break
        else:
            pfolder=getFolderName(df,pid)
            folder=u'%s/%s' %(pfolder,folder)
        cid=pid

    return folderid,folder


def extractAnnos(annotations,action,verbose):
    '''Extract texts and attach meta to annotations.

    <annotations>: dict, key: docid, value: DocAnno objs.
    <action>: list, actions from cli arguments.

    Return <annotations2>: dict, similar structure as <annotations> but
                           with highlight texts extracted.
           <faillist>: list, paths of failed pdfs.
    '''

    #------ Check if pdftotext is available--------
    if extracthl2.checkPdftotext():
        has_pdftotext=True
    else:
        has_pdftotext=False

    faillist=[]
    annotations2={}  #keys: docid, values: extracted annotations

    #-----------Loop through documents---------------
    num=len(annotations)
    docids=annotations.keys()

    for ii,idii in enumerate(docids):
        annoii=annotations[idii]
        hlii=[]
        ntii=[]

        #------Loop through attached files in a doc------
        for fjj, annojj in annoii.file_annos.items():

            fnamejj=annojj.filename
            # When a doc has no attachment, use title instead of filename
            if fnamejj is None: fnamejj=annojj.meta['title']
            if verbose:
                printNumHeader('Processing file:',ii+1,num,3)
                printInd(fnamejj,4)

            if 'm' in action:
                try:
                    if has_pdftotext:
                        if verbose:
                            printInd('Retrieving highlights using pdftotext ...',4,prefix='# <Menotexport>:')
                        hltexts=extracthl2.extractHighlights2(fjj,annojj,
                                'pdftotext',verbose)
                    else:
                        if verbose:
                            printInd('Retrieving highlights using pdfminer ...',4,prefix='# <Menotexport>:')
                        hltexts=extracthl2.extractHighlights2(fjj,annojj,
                                'pdfminer',verbose)
                except:
                    faillist.append(fnamejj)
                    hltexts=[]
            else:
                hltexts=[]

            if 'n' in action:
                if verbose:
                    printInd('Retrieving notes...',4,prefix='# <Menotexport>:')
                try:
                    nttexts=extractnt.extractNotes(fjj,annojj,verbose)
                except:
                    faillist.append(fnamejj)
                    nttexts=[]
            else:
                nttexts=[]

            #------------Attach ori texts to notes------------
            nttexts=extractnt.attachRefTextsToNotes(nttexts,hltexts)

            hlii.extend(hltexts)
            ntii.extend(nttexts)

        annoii.highlights=hlii
        annoii.notes=ntii
        annotations2[idii]=annoii

    return annotations2,faillist


def processDocs(db,outdir,docids,foldername,allfolders,action,\
        separate,iszotero,verbose):
    '''Process files/docs.

    <db>: sqlite database.
    <outdir>: str, output directory path.
    <docids>: list of ints, ids of docs to process.
    <foldername>: string, sub-folder name under <outdir> to save outputs.
    <allfolders>: bool, user chooses to process all folders or one folder.
    <action>: list, possible elements: m, n, p, b, r, t
    <separate>: bool, whether save one output for each file or all files.
    <iszotero>: bool, whether exported .bib is reformated to cater to zotero
                import or not.

    Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
    Update time: 2018-08-06 21:42:27.
    '''

    exportfaillist=[]
    annofaillist=[]
    bibfaillist=[]
    risfaillist=[]

    ishighlight=False
    isnote=False
    if 'm' in action or 'p' in action:
        ishighlight=True
    if 'n' in action or 'p' in action:
        isnote=True

    #----------Get meta data for docs----------
    doc_meta={}
    for idii in docids:
        doc_meta[idii]=getMetaData(db,idii)

    #------------Get raw annotation data------------
    annotations={}
    for idii in docids:
        if ishighlight:
            annotations = getHighlights(db,idii,annotations)
        if isnote:
            annotations = getNotes(db,idii,annotations)
            annotations = getDocNotes(db,idii,annotations)

    if len(annotations)==0:
        printHeader('No annotations found in folder: %s' %foldername,2)
        # Need to add 'r', right?
        if 'b' not in action and 'p' not in action and 'r' not in action:
            return exportfaillist,annofaillist,bibfaillist,risfaillist
    else:
        #----------Populate meta data for docs----------
        for idii in annotations.keys():
            annotations[idii]['meta']=doc_meta[idii]

        #---------------Reformat annotations---------------
        annotations=reformatAnno(annotations)

    #------Get other docs without annotations------
    otherdocs=[doc_meta[idii] for idii in docids if idii not in\
            annotations.keys()]

    #--------Make subdir using folder name--------
    outdir_folder=os.path.join(outdir,foldername)
    if not os.path.isdir(outdir_folder):
        makedirs(outdir_folder)

    #-------------------Export PDFs-------------------
    if 'p' in action:
        #-----------Export PDFs with annotations-----------
        if len(annotations)>0:
            if verbose:
                printHeader('Exporting annotated PDFs ...',2)
            flist=exportpdf.exportAnnoPdf(annotations,\
                    outdir_folder,verbose)
            exportfaillist.extend(flist)
    
        #--------Copy other PDFs to target location--------
        if len(otherdocs)>0:
            if verbose:
                printHeader('Exporting un-annotated PDFs ...',2)
            flist=exportpdf.copyPdf(otherdocs,outdir_folder,verbose)
            exportfaillist.extend(flist)

    #----------Extract annotations from PDFs----------
    if len(annotations)>0:
        if verbose:
            printHeader('Extracting annotations from PDFs ...',2)
        annotations,flist=extractAnnos(annotations,action,verbose)
        annofaillist.extend(flist)
        # NOTE beyond this point things in <annotations> have changed:
        # key: docid as before. value: DocAnno as before, 
        # but DocAnno now has highlights and notes attributes which are
        # both lists of extracthl2.Anno objs

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
            # <bibfolder> is the folder to save .bib file, which is <outdir>
            # if <allfolders> is True, or <outdir>/<folder_tree> otherwise.
            flist=export2bib.exportAnno2Bib(annotations,outdir,\
                bibfolder,allfolders,isfile,iszotero,verbose)
            bibfaillist.extend(flist)

        #------Export other docs without annotations------
        if len(otherdocs)>0:
            flist=export2bib.exportDoc2Bib(otherdocs,outdir,\
                bibfolder,allfolders,isfile,iszotero,verbose)
            bibfaillist.extend(flist)

    #----------Export meta and anno to ris file----------
    if 'r' in action:

        if verbose:
            printHeader('Exporting meta-data and annotations to .ris file...',2)

        risfolder=outdir if allfolders else outdir_folder
        isfile=True if 'p' in action else False

        #-----------Export docs with annotations-----------
        if len(annotations)>0:
            # <outdir> is the base folder to save outputs, specified by user
            # <bibfolder> is the folder to save .bib file, which is <outdir> if <allfolders> is True,
            # or <outdir>/<folder_tree> otherwise.
            flist=export2ris.exportAnno2Ris(annotations,outdir,\
                risfolder,allfolders,isfile,iszotero,verbose)
            risfaillist.extend(flist)

        #------Export other docs without annotations------
        if len(otherdocs)>0:
            flist=export2ris.exportDoc2Ris(otherdocs,outdir,\
                risfolder,allfolders,isfile,iszotero,verbose)
            risfaillist.extend(flist)


    return exportfaillist,annofaillist,bibfaillist,risfaillist


def processCanonicals(db,outdir,annotations,docids,allfolders,action,\
        separate,iszotero,verbose):
    '''Process files/docs in a folder.

    <db>: sqlite database.
    <outdir>: str, output directory path.
    <annotations>: dict, keys: documentId; values: highlights, notes and meta.
                   See doc in getHighlights().
    <docids>: list, docids of canonical docs.
    <allfolders>: bool, user chooses to process all folders or one folder.
    <action>: list, possible elements: m, n, e, b.
    <separate>: bool, whether save one output for each file or all files.
    <iszotero>: bool, whether exported .bib is reformated to cater to zotero import or not.

    Deprecated, no longer in use.
    '''
    
    exportfaillist=[]
    annofaillist=[]
    bibfaillist=[]
    risfaillist=[]

    ishighlight=False
    isnote=False
    if 'm' in action or 'p' in action:
        ishighlight=True
    if 'n' in action or 'p' in action:
        isnote=True

    #------------Get raw annotation data------------
    for ii,idii in enumerate(docids):
        if ishighlight:
            annotations=getHighlights(db,annotations,folderid=None,foldername=None,filterdocid=idii)
        if isnote:
            annotations=getNotes(db,annotations,folderid=None,foldername=None,filterdocid=idii)
            annotations=getDocNotes(db,annotations,folderid=None,foldername=None,filterdocid=idii)

    if len(annotations)==0:
        print('\n# <Menotexport>: No annotations found among Canonical docs.')
        if 'b' not in action and 'p' not in action:
            return exportfaillist,annofaillist,bibfaillist,risfaillist
    else:
        #---------------Reformat annotations---------------
        annotations=reformatAnno(annotations)

    #------Get other docs without annotations------
    otherdocs=getOtherCanonicalDocs(db,docids,annotations.keys())

    #--------Make subdir using folder name--------
    outdir_folder=os.path.join(outdir,'Canonical-My library')
    if not os.path.isdir(outdir_folder):
        #os.makedirs(outdir_folder)
        makedirs(outdir_folder)

    #-------------------Export PDFs-------------------
    if 'p' in action:
        if len(annotations)>0:
            if verbose:
                printHeader('Exporting annotated PDFs ...',2)
            flist=exportpdf.exportAnnoPdf(annotations,\
                    outdir_folder,verbose)
            exportfaillist.extend(flist)
    
        #--------Copy other PDFs to target location--------
        if len(otherdocs)>0:
            if verbose:
                printHeader('Exporting un-annotated PDFs ...',2)
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
            flist=export2bib.exportAnno2Bib(annotations,outdir,\
                bibfolder,allfolders,isfile,iszotero,verbose)
            bibfaillist.extend(flist)

        #------Export other docs without annotations------
        if len(otherdocs)>0:
            flist=export2bib.exportDoc2Bib(otherdocs,outdir,\
                bibfolder,allfolders,isfile,iszotero,verbose)
            bibfaillist.extend(flist)

    #----------Export meta and anno to ris file----------
    if 'r' in action:

        if verbose:
            printHeader('Exporting meta-data and annotations to .ris file...',2)

        risfolder=outdir if allfolders else outdir_folder
        isfile=True if 'p' in action else False

        #-----------Export docs with annotations-----------
        if len(annotations)>0:
            # <outdir> is the base folder to save outputs, specified by user
            # <bibfolder> is the folder to save .bib file, which is <outdir> if <allfolders> is True,
            # or <outdir>/<folder_tree> otherwise.
            flist=export2ris.exportAnno2Ris(annotations,outdir,\
                risfolder,allfolders,isfile,iszotero,verbose)
            risfaillist.extend(flist)

        #------Export other docs without annotations------
        if len(otherdocs)>0:
            flist=export2ris.exportDoc2Ris(otherdocs,outdir,\
                risfolder,allfolders,isfile,iszotero,verbose)
            risfaillist.extend(flist)


    return exportfaillist,annofaillist,bibfaillist,risfaillist


def matchDOI(db):
    '''Not currently used'''
    query=\
    '''SELECT Documents.note
            FROM Documents
            WHERE (Documents.note IS NOT NULL)
    '''

    ret=db.execute(query)
    aa=ret.fetchall()

    pattern=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
            re.DOTALL|re.UNICODE)
    for ii in aa:
        m=pattern.match(ii[0])
        if m is not None:
            print ii[0],m.groups()

    return




#----------------Main----------------
def main(dbfin,outdir,action,folder,separate,iszotero,verbose=True):

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

    # get docids for doc ids that not in any folder
    if folder is None:
        canonical_doc_ids=getCanonicals(db)

    if len(folderlist)==0 and len(canonical_doc_ids)==0:
        printHeader('It looks like no docs are found in the library. Quit.')
        return 1

    #---------------Process--------------------------
    exportfaillist=[]
    annofaillist=[]
    bibfaillist=[]
    risfaillist=[]

    #---------------Loop through folders---------------
    if len(folderlist)>0:
        for ii,folderii in enumerate(folderlist):
            fidii,fnameii=folderii
            if verbose:
                printNumHeader('Processing folder: "%s"' %fnameii,\
                        ii+1,len(folderlist),1)

            #----------Get docids for docs in folder----------
            docidsii=getFolderDocList(db,fidii)

            exportfaillistii,annofaillistii,bibfaillistii,risfaillistii=\
                processDocs(db,outdir,docidsii,fnameii,allfolders,action,
                separate,iszotero,verbose)

            exportfaillist.extend(exportfaillistii)
            annofaillist.extend(annofaillistii)
            bibfaillist.extend(bibfaillistii)
            risfaillist.extend(risfaillistii)

    #---------------Process canonical docs ------------
    if folder is None and len(canonical_doc_ids)>0:
        if verbose:
            printHeader('Processing docs under "My Library"')

        exportfaillistii,annofaillistii,bibfaillistii,risfaillistii=\
                processDocs(db,outdir,canonical_doc_ids,'My Library',
                    allfolders,action,separate,iszotero,verbose)

        exportfaillist.extend(exportfaillistii)
        annofaillist.extend(annofaillistii)
        bibfaillist.extend(bibfaillistii)
        risfaillist.extend(risfaillistii)

        printHeader('NOTE that docs not belonging to any folder is saved to directory : "Canonical-My Library"')

    #-----------------Close connection-----------------
    if verbose:
        printHeader('Drop connection to database:')
    db.close()

    #------------------Print summary------------------
    exportfaillist=list(set(exportfaillist))
    annofaillist=list(set(annofaillist))
    bibfaillist=list(set(bibfaillist))
    risfaillist=list(set(risfaillist))

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

    if len(risfaillist)>0:
        printHeader('Failed to export to .ris files:',2)
        for failii in risfaillist:
            printInd(failii,2)

    if len(exportfaillist)==0 and len(annofaillist)==0 and len(bibfaillist)==0 and\
            len(risfaillist)==0:
        if verbose:
            printHeader('All done.',2)

    #-----------------Remove tmp file-----------------
    if os.path.exists('tmp.txt'):
	os.remove('tmp.txt')


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
            Can be used with -m, -n, -b and -r''')
    parser.add_argument('-m', '--markup', dest='action',\
            action='append_const', \
            const='m',\
        help='''Export highlights to a txt file: highlights.txt.
            Can be used with -p, -n, -b and -r.
                If used with -n, highlights and notes are combined
                in annotations.txt.''')
    parser.add_argument('-n', '--note', dest='action',\
            action='append_const', \
            const='n',\
        help='''Export notes to a txt file: notes.txt.
            Can be used with -p, -m, -b and -r.
                If used with -m, highlights and notes are combined
                in annotations.txt.''')
    parser.add_argument('-b', '--bib', dest='action',\
            action='append_const', \
            const='b',\
        help='''Export all meta-data and annotations to .bib files.
            Can be used with -p, -m, -n and -r.
            If a folder is specified via the -f (--folder) option,
            save the .bib file into a sub-directory named after <folder>.
            If choose to process all folders, save the .bib file
            to <outdir>.''')
    parser.add_argument('-r', '--ris', dest='action',\
            action='append_const', \
            const='r',\
        help='''Export meta-data and annotations to .ris files.
            Can be used with -p, -m, -n and -b.
            If a folder is specified via the -f (--folder) option,
            save the .ris file into a sub-directory named after <folder>.
            If choose to process all folders, save the .ris file
            to <outdir>.''')

    parser.add_argument('-f', '--folder', dest='folder',\
            type=str, default=None, help='''Select a Mendeley folder to process.
            If not given, process all folders in the library. In such case,
            the folder structure will be preserved by creating sub-directories.''')

    parser.add_argument('-s', '--separate', action='store_true',\
            help='''Export annotations to a separate txt file
            for each PDF.
            Default to export all file annotations to a single file.''')
    parser.add_argument('-z', '--zotero', action='store_true',\
            default=False,\
            help='''Exported .bib or .ris file has slightly different formating
            to facilitate import into Zotero.
            Only works when -b and/or -r are toggled.''')

    parser.add_argument('-t', '--template', dest='action',
            action='append_const',
            const='t',
            help='''**Feature in progress**.
            Use custom template to format the exported annotations.
            The template file is /menotexport_install_folder/annotation_template.py.
            See instructions in that file on how to modify template.
            ''')

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
            args.separate,args.zotero,args.verbose)







