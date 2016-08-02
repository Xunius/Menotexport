'''Export meta-data and annotations from documents in Mendeley to .ris file.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-06-23 08:37:36.
'''

import os
import platform
import tools
import re
from pylatexenc import latexencode


TYPE_DICT={'Report': 'RPRT',\
           'JournalArticle': 'JOUR',\
           'Book': 'BOOK',\
           'BookSection': 'CHAP',\
           'ConferenceProceedings': 'CONF',\
           'Generic': 'GEN',\
           'Bill': 'BILL',\
           'Case': 'CASE',\
           'ComputerProgram': 'COMP',\
           'EncyclopediaArticle': 'ENCYC',\
           'Film': 'VIDEO',\
           'Hearing': 'HEAR',\
           'MagazineArticle': 'MGZN',\
           'NewspaperArticle': 'NEWS',\
           'Patent': 'PAT',\
           'Statute': 'STAT',\
           'Thesis': 'THES',\
           'WebPage': 'ELEC',\
           'WorkingPaper': 'MANSCPT'}

KEYWORD_DICT={'title': 'TI',\
              'issue': 'IS',\
              'publication': ['JF','JO','T2'],\
              'volume': 'VL',\
              'doi': 'DO',\
              'abstract': 'AB',\
              'edition': 'ET',\
              'ISBN': 'SN',\
              'isbn': 'SN',\
              'ISSN': 'SN',\
              'issn': 'SN',\
              'publisher': 'PB',\
              'keywords': 'KW',\
              'path': 'L1',\
              'annote': 'N1',\
              'editor': 'ED'}



#------------------------Parse file path entry------------------------
def parseFilePath(path,baseoutdir,folder,iszotero,verbose=True):
    '''Parse file path entry

    '''
    path_re=re.compile('^/(.*)',re.UNICODE)
    basedir,filename=os.path.split(path)
    basename,ext=os.path.splitext(filename)

    if basedir=='/pseudo_path':
        return ''

    abpath=os.path.join(baseoutdir,folder)
    abpath=os.path.join(abpath,filename)
    abpath=os.path.abspath(abpath)

    '''
    if iszotero:
        #result=path_re.sub(':\\1',result)  #Necessary?
        # Make the path recognizable by zotero on windows
        if platform.system().lower()=='windows':
            pathsplit=abpath.split(':')
            drive=pathsplit[0]
            pathnodrive=''.join(pathsplit[1:])
            abpath='file\\:///%s\\:%s' %(drive,pathnodrive)
        #result='%s:%s:%s' %filename,abpath,ext[1:])
        result=abpath
    else:
        #result=path_re.sub(':\\1',result)  #Necessary?
    '''
    result=abpath

    return result



#-----------------------Parse document meta-data-----------------------
def parseMeta(metadict,basedir,isfile,iszotero,verbose=True):
    '''Parse document meta-data

    metadict
    '''

    def getField(doc,field,default=''):
        return doc[field] or default
    
    page_re=re.compile('(.*?)-(.*)', re.UNICODE)
    def _subDash(match):
        return '%s--%s' %(match.group(1),match.group(2))

    #--------------------Get type--------------------
    doctype=getField(metadict,'type','JournalArticle')
    doctype=TYPE_DICT[doctype]

    entries=['TY - %s' %doctype,]

    #-------------------Get authors-------------------
    first=metadict['firstnames']
    last=metadict['lastname']
    if first is None or last is None:
        authors=''
    if type(first) is not list and type(last) is not list:
        authors='%s, %s' %(last, first)
        authors=[authors,]
    else:
        authors=['%s, %s' %(ii[0],ii[1]) for ii in zip(last,first)]

    for ii in authors:
        entries.append('AU - %s' %ii)
    #authors=latexencode.utf8tolatex(authors)
    
    #---------------------Get time---------------------
    year=getField(metadict,'year','')
    month=getField(metadict,'month','')
    day=getField(metadict,'day','')
    time=[]
    for ii in [year,month,day]:
        try:
            ii=str(int(ii))
        except:
            # vv is nan
            ii=''
        time.append(ii)
    if year!='':
	entries.append('PY - %s' %time[0])
    time='%s/%s/%s/' %(time[0],time[1],time[2])
    entries.append('DA - %s' %time)
    entries.append('Y1 - %s' %time)

    #--------------------Get pages--------------------
    pages=getField(metadict,'pages','')
    if pages!='':
        pmatch=page_re.match(pages)
        if pmatch is None:
            #entries.append('SP - %s' %str(pages))
            entries.append('SP - %s' %tools.deu(pages))
        else:
            #entries.append('SP - %s' %str(pmatch.group(1)))
            #entries.append('EP - %s' %str(pmatch.group(2)))
            entries.append('SP - %s' %tools.deu(pmatch.group(1)))
            entries.append('EP - %s' %tools.deu(pmatch.group(2)))

    #-----------------Get city/country-----------------
    loc=u''
    city=getField(metadict,'city','')
    country=getField(metadict,'country','')
    if city!='':
        loc=u'%s, %s' %(loc,city)
    if country!='':
        loc=u'%s, %s' %(loc,country)
    if len(loc)>0:
        entries.append('CY - %s' %loc)

    #--------------Populate other fields--------------
    gotkeywords=False

    for kk,vv in metadict.items():
        if vv is None:
            continue
        if kk in ['type','firstnames','lastname','docid','year','month',\
                'day','pages','city','country']:
            continue

        #------------------Get file path------------------
        if kk=='path':
            if not isfile:
                continue
            vv=parseFilePath(vv,basedir,metadict['folder'],iszotero)
            if vv=='':
                continue

        #----------Add tags to keywords if iszotero----------
        if iszotero and (kk=='tags' or kk=='keywords') and not gotkeywords:
            keywords=getField(metadict,'keywords',[])
            if type(keywords) is not list:
                keywords=[keywords,]
            tags=getField(metadict,'tags',[])
            if type(tags) is not list:
                tags=[tags,]
            keywords.extend(tags)
	    keywords=list(set(keywords))
            kk='keywords'
            vv=keywords
            gotkeywords=True

	#-----------Specifiy issn and isbn-----------------
	if kk.lower()=='issn':
	    vv='issn %s' %vv
	if kk.lower()=='isbn':
	    vv='isbn %s' %vv

        #--------------------All others--------------------
        kk=KEYWORD_DICT.get(kk,None)
        if kk is None:
            continue
        if type(kk) is not list:
            kk=[kk,]
        if type(vv) is not list:
            vv=[vv,]

        for kii in kk:
            for vjj in vv:
                entries.append('%s - %s' %(kii,vjj))

    entries.append('ER -\n')
    string='\n'.join(entries)
    string=string+'\n'
    string=tools.enu(string)

    return string



#--------------Export documents with annotations to .ris--------------
def exportAnno2Ris(annodict,basedir,outdir,allfolders,isfile,iszotero,verbose=True):
    '''Export documents with annotations to .ris

    '''

    #----------------Loop through docs----------------
    doclist=[]

    for idii,annoii in annodict.items():
        metaii=annoii.meta
        hlii=annoii.highlights
        ntii=annoii.notes
        annotexts=[]

        #------------------Get highlights------------------
        if len(hlii)>0:
            for hljj in hlii:
                annotexts.append('> %s' %hljj.text)

        #------------------Get notes------------------
        if len(ntii)>0:
            for ntjj in ntii:
                annotexts.append('- %s' %ntjj.text)

        metaii['annote']=annotexts
        doclist.append(metaii)

    #----------------------Export----------------------
    faillist=exportDoc2Ris(doclist,basedir,outdir,\
            allfolders,isfile,iszotero,verbose)

    return faillist

    

#-------------Export documents without annotations to .ris-------------
def exportDoc2Ris(doclist,basedir,outdir,allfolders,isfile,iszotero,verbose=True):
    '''Export documents without annotations to .bib

    '''

    if allfolders:
        fileout='Mendeley_lib.ris'
    else:
        folder=os.path.split(outdir)[-1]
        fileout='Mendeley_lib_%s.ris' %folder

    abpath_out=os.path.join(outdir,fileout)

    #----------------Loop through docs----------------
    faillist=[]

    for docii in doclist:
        risdata=parseMeta(docii,basedir,isfile,iszotero)
        with open(abpath_out, mode='a') as fout:
            fout.write(risdata)
        #faillist.append(docii['title'])

    return faillist


