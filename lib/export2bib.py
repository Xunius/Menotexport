'''Export meta-data and annotations from documents in Mendeley to .bib file.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-06-22 16:25:15.
'''

import os
import platform
#import tools
import re
from pylatexenc import latexencode

import logging
logging.basicConfig()



#------------------------Parse file path entry------------------------
def parseFilePath(path,baseoutdir,folder,iszotero,verbose=True):
    '''Parse file path entry

    '''
    #path_re=re.compile('^/(.*)',re.UNICODE)
    basedir,filename=os.path.split(path)
    basename,ext=os.path.splitext(filename)

    #if basedir=='/pseudo_path':
    #    return ''

    abpath=os.path.join(baseoutdir,folder)
    abpath=os.path.join(abpath,filename)
    abpath=os.path.abspath(abpath)


    if iszotero:
        #result=path_re.sub(':\\1',result)  #Necessary?
        # Make the path recognizable by zotero on windows
        if platform.system().lower()=='windows':
            pathsplit=abpath.split(':')
            drive=pathsplit[0]
            pathnodrive=''.join(pathsplit[1:])
            abpath='file\\:///%s\\:%s' %(drive,pathnodrive)
        result='%s:%s:%s' %(filename,abpath,ext[1:])
    else:
        #result=path_re.sub(':\\1',result)  #Necessary?
        result='%s:%s' %(abpath,ext[1:])

    return result


#-----------------------Parse document meta-data-----------------------
def parseMeta(metadict,basedir,folder,isfile,iszotero,verbose=True):
    '''Parse document meta-data

    metadict
    '''

    def getField(doc,field,default=''):
        return doc[field] or default
    
    page_re=re.compile('(.*?)-(.*)', re.UNICODE)
    def _subDash(match):
        return '%s--%s' %(match.group(1),match.group(2))

    #--------------------Get header--------------------
    doctype=getField(metadict,'type','article')
    if doctype==u'JournalArticle':
        doctype='article'  #Necessary?
    citekey=getField(metadict,'citationkey','citationkey')

    #-------------------Get authors-------------------
    first=metadict['firstnames']
    last=metadict['lastname']
    if first is None or last is None:
        authors=''
    if type(first) is not list and type(last) is not list:
        authors='%s, %s' %(last, first)
    else:
        authors=['%s, %s' %(ii[0],ii[1]) for ii in zip(last,first)]
        authors=' and '.join(authors)
    authors=latexencode.utf8tolatex(authors)
    
    string='@%s{%s,\n' %(doctype,citekey)
    entries=['author = {%s}' %authors,]

    #--------------Populate other fields--------------
    gotkeywords=False

    for kk,vv in metadict.items():
        if vv is None:
            continue
        if kk in ['type','firstnames','lastname','docid']:
            continue
        if kk in ['year','month','day']:
            # Convert float to int to str
            try:
                vv=str(int(vv))
            except:
                # vv is nan
                continue

        if kk=='publication' and doctype=='article':
            kk='journal'
        if kk=='pages':
            vv=page_re.sub(_subDash,vv)
        if kk=='path':
            if not isfile:
                continue
            if not isinstance(vv,list) and not isinstance(vv,tuple):
                vv=[vv,]
            vv=[parseFilePath(ii,basedir,folder,iszotero) for\
                    ii in vv]
            # proper way of joining multiple paths?
            vv='}, {'.join(vv)
            vv=u'{%s}' %vv

            if vv=='':
                continue
            else:
                kk='file'

        #--------------Parse unicode to latex--------------
        if type(vv) is list:
            fieldvv=[latexencode.utf8tolatex(ii) for ii in vv]
        else:
            # Leave file path alone
            if kk!='file':
                fieldvv=latexencode.utf8tolatex(vv)
            else:
                fieldvv=vv

        #----------Add tags to keywords if iszotero----------
        if iszotero and (kk=='tags' or kk=='keywords') and not gotkeywords:
            #keywords=getField(metadict,'keywords',[])
            # avoid keywords for sbaross
            keywords=[]
            if type(keywords) is not list:
                keywords=[keywords,]
            tags=getField(metadict,'tags',[])
            if type(tags) is not list:
                tags=[tags,]
            keywords.extend(tags)
	    keywords=list(set(keywords))
            fieldvv=[latexencode.utf8tolatex(ii) for ii in keywords]
            kk='keywords'
            gotkeywords=True

        #----------------Parse annotations----------------
        #if kk=='annote':
        if kk in ['notes', 'highlights']:
            #if type(fieldvv) is not list:
                #fieldvv=[fieldvv,]
            if len(fieldvv)==0:
                continue

            # For import to zotero, separate annotes
            if iszotero:
                for ii in fieldvv:
                    entrykk='%s = { %s }' %('annote',ii)
                    entries.append(entrykk)
            else:
                fieldvv=['{ %s }' %ii for ii in fieldvv]
                fieldvv=u', '.join(fieldvv)
                #entrykk='%s = {%s}' %(kk, fieldvv)
                entrykk='%s = {%s}' %('annote', fieldvv)
                entries.append(entrykk)

        #--------------------All others--------------------
        else:
            if type(fieldvv) is list:
                fieldvv=u', '.join(fieldvv)
            entrykk='%s = {%s}' %(kk, fieldvv)
            entries.append(entrykk)

    entries=',\n'.join(entries)
    string=string+entries+'\n}\n'
    string=string.encode('ascii','replace')

    return string


#--------------Export documents with annotations to .bib--------------
def exportAnno2Bib(annodict,basedir,outdir,allfolders,isfile,iszotero,verbose=True):
    '''Export documents with annotations to .bib

    <annodict>: dict, key: docid, value: menotexport.DocAnno objs.
    '''

    #----------------Loop through docs----------------
    doclist=[]

    for idii,annoii in annodict.items():
        metaii=annoii.meta
        hlii=annoii.highlights
        ntii=annoii.notes
        #annotexts=[]
        hltexts=[]
        nttexts=[]

        #------------------Get highlights------------------
        if len(hlii)>0:
            for hljj in hlii:
                #annotexts.append('> %s' %hljj.text)
                hltexts.append('> %s' %hljj.text)

        #------------------Get notes------------------
        if len(ntii)>0:
            for ntjj in ntii:
                #annotexts.append('- %s' %ntjj.text)
                nttexts.append('- %s' %ntjj.text)

        #metaii['annote']=annotexts
        metaii['notes']=nttexts
        metaii['highlights']=hltexts
        doclist.append(metaii)

    #----------------------Export----------------------
    faillist=exportDoc2Bib(doclist,basedir,outdir,\
            allfolders,isfile,iszotero,verbose)

    return faillist


#-------------Export documents without annotations to .bib-------------
def exportDoc2Bib(doclist,basedir,outdir,allfolders,isfile,iszotero,verbose=True):
    '''Export documents without annotations to .bib

    <doclist>: list of meta data dists.
    '''

    if allfolders:
        fileout='Mendeley_lib.bib'
        folder=''
    else:
        folder=os.path.split(outdir)[-1]
        fileout='Mendeley_lib_%s.bib' %folder

    abpath_out=os.path.join(outdir,fileout)

    #----------------Loop through docs----------------
    faillist=[]

    for docii in doclist:
        try:
            bibdata=parseMeta(docii,basedir,folder,isfile,iszotero)
            with open(abpath_out, mode='a') as fout:
                fout.write(bibdata)
        except:
            faillist.append(docii['title'])

    return faillist


