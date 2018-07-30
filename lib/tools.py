'''
Utility functions.

Update time: 2016-03-24 11:11:46.
'''
import os
import re



def deu(text):
    if isinstance(text,str):
        return text.decode('utf8','replace')
    else:
        return text


def enu(text):
    if isinstance(text,unicode):
        return text.encode('utf8','replace')
    else:
        return text


def printHeader(s, level=1, length=70, prefix='# <Menotexport>:'):
    from textwrap import TextWrapper

    decs={1: '=', 2: '-', 3: '.'}
    indents={1: 0, 2: 4, 3: 8}

    dec=decs[level]
    ind=indents[level]
    indstr=' '*int(ind)

    wrapper=TextWrapper()
    wrapper.width=length-ind
    wrapper.initial_indent=indstr
    wrapper.subsequent_indent=indstr

    #-------------Get delimiter line-------------
    hline='%s%s' %(' '*int(ind),dec*int(length-ind)) 

    #--------------------Wrap texts--------------------
    strings=wrapper.wrap('%s %s' %(prefix,s))

    #----------------------Print----------------------
    try:
        print('\n'+hline)
    except:
        print('\n'+hline.encode('ascii','replace'))
    for ss in strings:
        try:
            print(ss)
        except:
            print(ss.encode('ascii','replace'))
    #print(hline)

    return


def printNumHeader(s, idx, num, level=1, length=70, prefix='# <Menotexport>:'):
    from textwrap import TextWrapper

    decs={1: '=', 2: '-', 3: '.'}
    indents={1: 0, 2: 4, 3: 8}

    dec=decs[level]
    ind=indents[level]
    indstr=' '*int(ind)

    wrapper=TextWrapper()
    wrapper.width=length-ind
    wrapper.initial_indent=indstr
    wrapper.subsequent_indent=indstr

    #-------------Get delimiter line-------------
    decl=int((length-ind-2-len(str(idx))-len(str(num)))/2.)
    decl=decl*dec

    hline1='%s%s %d/%d %s' %(' '*int(ind),decl,idx,num,decl) 
    #hline2='%s%s' %(' '*int(ind),dec*int(length-ind)) 

    #--------------------Wrap texts--------------------
    strings=wrapper.wrap('%s %s' %(prefix,s))

    #----------------------Print----------------------
    try:
        print('\n'+hline1)
    except:
        print('\n'+hline1.encode('ascii','replace'))
    for ss in strings:
        try:
            print(ss)
        except:
            print(ss.encode('ascii','replace'))
    #print(hline2)

    return


def printInd(s, level=1, length=70, prefix=''):
    from textwrap import TextWrapper
    indents={1: 0, 2: 4, 3: 8, 4: 12, 5: 16}

    ind=indents[level]
    indstr=' '*int(ind)

    wrapper=TextWrapper()
    wrapper.width=length
    wrapper.initial_indent=indstr
    wrapper.subsequent_indent=indstr

    string=wrapper.fill('%s %s' %(prefix,s))
    try:
        print('\n'+string)
    except:
        print('\n'+string.encode('ascii','replace'))

    return 


def readFile(abpath_in,verbose=True):
    '''Read in text file and store data

    <abpath_in>: str, absolute path to input txt.
    '''

    if not os.path.exists(abpath_in):
        raise Exception("\n# <readFile>: Input file not found.")

    if verbose:
        print('\n# <readFile>: Open input file:')
        print(abpath_in)
        print('\n# <readFile>: Reading lines...')
        
    lines=[]

    with open(abpath_in, 'r') as fin:
        for line in fin:
            lines.append(deu(line))
    lines=u''.join(lines)

    if verbose:
        print('# <readFile>: Got all data.')

    return lines


def getAuthorList(meta_dict):
    '''Get author list string from annotation metadata dict'''

    first=meta_dict['firstnames']
    last=meta_dict['lastname']
    if first is None or last is None:
        authors=''
    if type(first) is not list and type(last) is not list:
        authors='%s, %s' %(last, first)
    else:
        authors=['%s, %s' %(ii[0],ii[1]) for ii in zip(last,first)]
        authors=' and '.join(authors)

    return authors


def autoRename(abpath):
    '''Auto rename a file to avoid overwriting an existing file

    <abpath>: str, absolute path to a folder or a file to rename.
    
    Return <newname>: str, new file path.
    If no conflict found, return <abpath>;
    If conflict with existing file, return renamed file path,
    by appending "_(n)".
    E.g. 
        n1='~/codes/tools/send2ever.py'
        n2='~/codes/tools/send2ever_(4).py'
    will be renamed to
        n1='~/codes/tools/send2ever_(1).py'
        n2='~/codes/tools/send2ever_(5).py'
    '''

    def rename_sub(match):
        base=match.group(1)
        delim=match.group(2)
        num=int(match.group(3))
        return '%s%s(%d)' %(base,delim,num+1)

    if not os.path.exists(abpath):
        return abpath

    folder,filename=os.path.split(abpath)
    basename,ext=os.path.splitext(filename)
    # match filename
    rename_re=re.compile('''
            ^(.+?)       # File name
            ([- _])      # delimiter between file name and number
            \\((\\d+)\\) # number in ()
            (.*)         # ext
            $''',\
            re.X)

    newname='%s_(1)%s' %(basename,ext)
    while True:
        newpath=os.path.join(folder,newname)

        if not os.path.exists(newpath):
            break
        else:
            if rename_re.match(newname):
                newname=rename_re.sub(rename_sub,newname)
                newname='%s%s' %(newname,ext)
            else:
                raise Exception("Exception")
                
    newname=os.path.join(folder,newname)
    return newname


def saveFile(abpath_out,text,overwrite=True,verbose=True):

    if os.path.isfile(abpath_out):
        if overwrite:
            os.remove(abpath_out)
        else:
            abpath_out=autoRename(abpath_out)

    if verbose:
        print('\n# <saveFile>: Saving result to:')
        print(abpath_out)

    with open(abpath_out, mode='a') as fout:
        fout.write(enu(text))

    return
        


def makedirs(path):
    '''Make dir and remove invalid windows path characters

    ':' is illegal in Mac and windows. Strategy: remove, although legal in Linux.
    '''
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except WindowsError:
            drive,remain=os.path.splitdrive(path)
            remain=re.sub(r'[<>:"|?*]','_',remain)
            remain=remain.strip()
            path=os.path.join(drive,remain)
            if not os.path.exists(path):
                os.makedirs(path)

    return
