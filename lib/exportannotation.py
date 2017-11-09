'''Export annotations from documents in Mendeley.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-04-12 22:09:38.
'''

import os
from textwrap import TextWrapper
import tools
from tools import printInd, printNumHeader
import annotation_template as atemp

TEMPLATE_EXCEPT_MESSAGE='''\

    Template formatting error.
    Please check your template file 'annoteation_template.py',
    and make sure that the variable name spellings are correct.
    Note that variable names are case sensitive.

'''

#------------------Export annotations in a single PDF------------------
def _exportAnnoFile(abpath_out,anno,verbose=True):
    '''Export annotations in a single PDF

    <abpath_out>: str, absolute path to output txt file.
    <anno>: list, in the form [file_path, highlight_list, note_list].
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

    hlii=anno.highlights
    ntii=anno.notes

    try:
        titleii=hlii[0].title
    except:
        titleii=ntii[0].title

    outstr=u'\n\n{0}\n# {1}'.format(int(80)*'-',conv(titleii))

    with open(abpath_out, mode='a') as fout:
        #outstr=outstr.encode('ascii','replace')
        outstr=outstr.encode('utf8','replace')
        fout.write(outstr)

        #-----------------Write highlights-----------------
        if len(hlii)>0:

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

                #outstr=outstr.encode('ascii','replace')
                outstr=outstr.encode('utf8','replace')
                fout.write(outstr)

        #-----------------Write notes-----------------
        if len(ntii)>0:

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

                #outstr=outstr.encode('ascii','replace')
                outstr=outstr.encode('utf8','replace')
                fout.write(outstr)

        


#------------------Export annotations in a single PDF------------------
def _exportAnnoFileTemplated(abpath_out,anno,verbose=True):
    '''Export annotations in a single PDF

    <abpath_out>: str, absolute path to output txt file.
    <anno>: list, in the form [file_path, highlight_list, note_list].
            highlight_list and note_list are both lists of
            Anno objs (see extracthl.py), containing highlights
            and notes in TEXT format with metadata. To be distinguished
            with FileAnno objs which contains texts coordinates.
            if highlight_list or note_list is [], no such info
            in this PDF.

    Function takes annotations from <anno> and output to the target txt file
    in a cumstom designed format. Template is taken from annotation_template.py.

    Update time: 2017-11-09 10:28:19.
    '''

    conv=lambda x:unicode(x)

    wrapper=TextWrapper()
    wrapper.width=atemp.WRAP_EACH_ENTRY-len(atemp.INDENT_EACH_ENTRY)
    wrapper.initial_indent=''
    wrapper.subsequent_indent=atemp.INDENT_EACH_ENTRY

    '''
    wrapper2=TextWrapper()
    #wrapper2.width=80-7
    wrapper2.width=atemp.WRAP_EACH_ENTRY-len(atemp.INDENT_EACH_ENTRY)
    wrapper2.initial_indent=''
    #wrapper2.subsequent_indent='\t\t'
    wrapper2.subsequent_indent=atemp.WRAP_EACH_ENTRY-len(atemp.INDENT_EACH_ENTRY)
    '''

    hls=anno.highlights
    nts=anno.notes

    try:
        titleii=hls[0].title
    except:
        titleii=nts[0].title

    #outstr=u'\n\n{0}\n# {1}\n\n'.format(int(80)*'-',conv(titleii))
    outstr=u'''\
------------------------------------------------------------------
{0}

'''.format(conv(titleii))


    def getFieldsDict(ntjj):
        dictjj={}
        dictjj['text']=wrapper.fill(ntjj.text)
        dictjj['page']=wrapper.fill(str(ntjj.page))
        dictjj['title']=wrapper.fill(ntjj.title)
        tagsjj=', '.join(['@'+kk for kk in ntjj.tags])
        dictjj['tags']=wrapper.fill(tagsjj)
        dictjj['ctime']=wrapper.fill(str(ntjj.ctime))
        dictjj['author']=wrapper.fill(ntjj.author)
        dictjj['note_author']=wrapper.fill(ntjj.note_author)
        dictjj['citationkey']=wrapper.fill(ntjj.citationkey)
        dictjj['num']=wrapper.fill(str(ntjj.num))

        if hasattr(ntjj,'ori_text'):
            dictjj['ori_text']=wrapper.fill(ntjj.ori_text)

        #for kk,vv in dictjj.items():
            #dictjj[kk]=wrapper.fill(str(vv))

        return dictjj

    with open(abpath_out, mode='a') as fout:
        #outstr=outstr.encode('ascii','replace')
        outstr=outstr.encode('utf8','replace')
        fout.write(outstr)

        nts_with_hl=[ntii for ntii in nts if hasattr(ntii,'ori_text')]
        nts_without_hl=list(set(nts).difference(nts_with_hl))
        nts_with_hl_texts=[ntii.ori_text for ntii in nts_with_hl]
        hls_without_nt=[]
        for ii,hlii in enumerate(hls):
            if hlii.text not in nts_with_hl_texts:
                hls_without_nt.append(hlii)

        #-----------Write notes with highlights-----------
        if len(nts_with_hl)>0:
            fout.write(u'''\
---------------------------
# Highlights linked with comments

''')

            #-------------Loop through notes-------------
            # Re-number notes
            for ii,ntii in enumerate(nts_with_hl):
                ntii.num=ii+1

            for ntjj in nts_with_hl:

                dictjj=getFieldsDict(ntjj)
                try:
                    ntjjstr=atemp.HIGHLIGHT_NOTE_ENTRY_TEMPLATE.format(**dictjj)
                except:
                    print TEMPLATE_EXCEPT_MESSAGE
                ntjjstr=ntjjstr.encode('utf8','replace')
                fout.write(ntjjstr)

        #------------------Write comments------------------
        if len(nts_without_hl)>0:
            #fout.write('# Comments\n')
            fout.write(u'''\
---------------------------
# Comments

''')

            #-------------Loop through notes-------------
            # Re-number notes
            for ii,ntii in enumerate(nts_without_hl):
                ntii.num=ii+1

            for ntjj in nts_without_hl:

                dictjj=getFieldsDict(ntjj)
                try:
                    ntjjstr=atemp.NOTE_ONLY_ENTRY_TEMPLATE.format(**dictjj)
                except:
                    print TEMPLATE_EXCEPT_MESSAGE
                ntjjstr=ntjjstr.encode('utf8','replace')
                fout.write(ntjjstr)

        #-----------------Write highlights-----------------
        if len(hls_without_nt)>0:
            #fout.write(' # Highlights\n')
            fout.write(u'''\
---------------------------
# Highlights

''')

            #-------------Loop through highlights-------------
            # Re-number highlights
            for ii,ntii in enumerate(hls_without_nt):
                ntii.num=ii+1

            for hljj in hls_without_nt:

                dictjj=getFieldsDict(hljj)
                try:
                    ntjjstr=atemp.HIGHLIGHT_ONLY_ENTRY_TEMPLATE.format(**dictjj)
                except:
                    print TEMPLATE_EXCEPT_MESSAGE
                ntjjstr=ntjjstr.encode('utf8','replace')
                fout.write(ntjjstr)
        

    
#--------------------Export highlights and/or notes--------------------
def exportAnno(annodict,outdir,action,separate,verbose=True):
    '''Export highlights and/or notes to txt file

    <annodict>: dict, keys: doc ids,
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
        abpath_out=tools.autoRename(abpath_out)

        if verbose:
            printInd('Exporting all annotations to:',3)
            printInd(abpath_out,4)

    #----------------Loop through files----------------
    annofaillist=[]

    num=len(annodict)
    docids=annodict.keys()

    for ii,idii in enumerate(docids):

        annoii=annodict[idii]
        fii=annoii.path
        basenameii=os.path.basename(fii)
        fnameii=os.path.splitext(basenameii)[0]

        if verbose:
            printNumHeader('Exporting annos in file',ii+1,num,3)
            printInd(fnameii,4)

        #---------Get individual output if needed---------
        if separate:
            if 'm' in action and 'n' not in action:
                fileout='Highlights_%s.txt' %fnameii
            elif 'n' in action and 'm' not in action:
                fileout='Notes_%s.txt' %fnameii
            elif 'm' in action and 'n' in action:
                fileout='Anno_%s.txt' %fnameii
            abpath_out=os.path.join(outdir,fileout)
            abpath_out=tools.autoRename(abpath_out)

            if verbose:
                printInd('Exporting annotations to:',3)
                printInd(abpath_out,4)

        #----------------------Export----------------------
        try:
            # Use custom template formatting
            if 't' in action:
                _exportAnnoFileTemplated(abpath_out,annoii)
            # Use default formatting
            else:
                _exportAnnoFile(abpath_out,annoii)
        except:
            annofaillist.append(basenameii)
            continue

    return annofaillist



