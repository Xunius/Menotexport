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
from tools import printHeader, printInd, printNumHeader


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
            - Page: page number (ordinal)
            - Colour: highlight colour
    
    -----------------------------------------------------
    # Title of another PDF

        > Highlighted text line 1
          Highlighted text line 2
          Highlighted text line 3
          ...
            
            - @citationkey
            - Tags: @tag1, @tag2, @tag3...
            - Ctime: creation time
            - Page: page number (ordinal)
            - Colour: highlight colour

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
\t\t- Page: {4}
\t\t- Color: {5}
'''.format(*map(conv,[hlstr, hljj.citationkey,\
    tagstr, hljj.ctime, hljj.page, hljj.color]))

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
\t\t- Page: {4}
\t\t- Color: {5}
'''.format(*map(conv,[ntstr, ntjj.citationkey,\
    tagstr, ntjj.ctime, ntjj.page, ntjj.color]))

                #outstr=outstr.encode('ascii','replace')
                outstr=outstr.encode('utf8','replace')
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
            _exportAnnoFile(abpath_out,annoii)
        except:
            annofaillist.append(basenameii)
            continue

    return annofaillist



