'''Export meta-data and annotations from documents in Mendeley to .bib file.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-13 15:40:08.
'''

import os
import tools
import re
from pylatexenc import latexencode



#------------------------Parse file path entry------------------------
def parseFilePath(path,outdir,folder,verbose=True):
    '''Parse file path entry

    '''
    path_re=re.compile('^/(.*)',re.UNICODE)
    basedir,filename=os.path.split(path)
    basename,ext=os.path.splitext(filename)

    if basedir=='/pseudo_path':
        return ''

    result=os.path.join(outdir,folder)
    result=os.path.join(result,filename)
    #result=path_re.sub(':\\1',result)  #Necessary?
    result='%s:%s' %(result,ext[1:])

    return result


    

    



#-----------------------Parse document meta-data-----------------------
def parseMeta(metadict,basedir,isfile,verbose=True):
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
    for kk,vv in metadict.items():
        if vv is None:
            continue
        if kk in ['type','firstnames','lastname','docid']:
            continue
        if kk in ['year','month']:
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
            vv=parseFilePath(vv,basedir,metadict['folder'])
            if vv=='':
                continue
            else:
                kk='file'

        #--------------Parse unicode to latex--------------
        if type(vv) is list:
            fieldvv=[latexencode.utf8tolatex(ii) for ii in vv]
            if kk=='annote':
                fieldvv=['{%s}' %ii for ii in fieldvv]
            fieldvv=u', '.join(fieldvv)
        else:
            fieldvv=latexencode.utf8tolatex(vv)

        entrykk='%s = {%s}' %(kk, fieldvv)
        entries.append(entrykk)

    entries=',\n'.join(entries)
    string=string+entries+'\n}\n'
    string=string.encode('ascii','replace')

    return string

        



#--------------Export documents with annotations to .bib--------------
def exportAnno2Bib(annodict,outdir,allfolders,isfile,verbose=True):
    '''Export documents with annotations to .bib

    annolist,outdir
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
    faillist=exportDoc2Bib(doclist,outdir,allfolders,isfile,verbose)

    return faillist

    




#-------------Export documents without annotations to .bib-------------
def exportDoc2Bib(doclist,outdir,allfolders,isfile,verbose=True):
    '''Export documents without annotations to .bib

    doclist,outdir
    '''

    if allfolders:
        fileout='Mendeley_lib.bib'
        basedir=outdir
    else:
        basedir,folder=os.path.split(outdir)
        fileout='Mendeley_lib_%s.bib' %folder

    abpath_out=os.path.join(outdir,fileout)

    #----------------Loop through docs----------------
    faillist=[]

    for docii in doclist:
        bibdata=parseMeta(docii,basedir,isfile)
        with open(abpath_out, mode='a') as fout:
            fout.write(bibdata)
        #faillist.append(docii['title'])

    return faillist


