#!/usr/bin/python
'''
GUI for Menotexport.py


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

Update time: 2016-02-28 22:09:28.
Update time: 2016-03-03 20:38:29.
Update time: 2016-04-15 13:13:31.
'''



import sys,os
from ttk import Style,Combobox
from tkFileDialog import askopenfilename, askdirectory
import tkMessageBox
import menotexport
import Queue
import threading
import sqlite3
import pandas as pd
if sys.version_info[0]>=3:
    import tkinter as tk
    from tkinter import Frame
else:
    import Tkinter as tk
    from Tkinter import Frame


stdout=sys.stdout


class Redirector(object):
    def __init__(self,q):
        self.q=q

    def write(self,string):
        self.q.put(string)

    '''
    def flush(self):
        with self.q.mutex:
            self.q.queue.clear()
    '''

class WorkThread(threading.Thread):
    def __init__(self,name,exitflag,stateq):
        threading.Thread.__init__(self)
        self.name=name
        self.exitflag=exitflag
        self._stop=threading.Event()
        self.stateq=stateq

    def run(self):
        print('\nStart processing...')
        if not self._stop.is_set():
            menotexport.main(*self.args)
            self.stateq.put('done')

    def stop(self):
        self.exitflag=True
        self._stop.set()





class MainFrame(Frame):
    def __init__(self,parent,stdoutq):
        Frame.__init__(self,parent)

        self.parent=parent
        self.width=750
        self.height=450
        self.title='Menotexport v1.1'
        self.stdoutq=stdoutq

        self.initUI()

        self.hasdb=False
        self.hasout=False
        self.hasaction=False
        self.exit=False

        self.path_frame=self.addPathFrame()
        self.action_frame=self.addActionFrame()
        self.message_frame=self.addMessageFrame()
        self.printStr()

        self.stateq=Queue.Queue()
        #self.workproc=Pool(1)




    def centerWindow(self):
        sw=self.parent.winfo_screenwidth()
        sh=self.parent.winfo_screenheight()
        x=(sw-self.width)/2
        y=(sh-self.height)/2
        self.parent.geometry('%dx%d+%d+%d' \
                %(self.width,self.height,x,y))


    def initUI(self):
        self.parent.title(self.title)
        self.style=Style()
        #Choose from default, clam, alt, classic
        self.style.theme_use('alt')
        self.pack(fill=tk.BOTH,expand=True)
        self.centerWindow()


    def printStr(self):
        while self.stdoutq.qsize() and self.exit==False:
            try:
                msg=self.stdoutq.get()
                self.text.update()
                self.text.insert(tk.END,msg)
                self.text.see(tk.END)
            except Queue.Empty:
                pass
        self.after(100,self.printStr)


    def checkReady(self):
        if self.isexport.get()==1 or self.ishighlight.get()==1\
                or self.isnote.get()==1:
            self.hasaction=True
        else:
            self.hasaction=False

        if self.hasdb and self.hasout and self.hasaction:
            self.start_button.configure(state=tk.NORMAL)
            print('Menotexport Ready.')
        else:
            self.start_button.configure(state=tk.DISABLED)


    def addPathFrame(self):
        frame=Frame(self)
        frame.pack(fill=tk.X,expand=0,side=tk.TOP,padx=8,pady=5)

        frame.columnconfigure(1,weight=1)

        #------------------Database file------------------
        label=tk.Label(frame,text='Mendeley Data file:',\
                bg='#bbb')
        label.grid(row=0,column=0,\
                sticky=tk.W,padx=8)

        self.db_entry=tk.Entry(frame)
        self.db_entry.grid(row=0,column=1,sticky=tk.W+tk.E,padx=8)

        self.db_button=tk.Button(frame,text='Open',command=self.openFile)
        self.db_button.grid(row=0,column=2,padx=8,sticky=tk.E)

        hint='''
Default location on Linux:
~/.local/share/data/Mendeley\ Ltd./Mendeley\ Desktop/your_email@www.mendeley.com.sqlite
Default location on Windows:
C:\Users\Your_name\AppData\Local\Mendeley Ltd\Mendeley Desktop\your_email@www.mendeley.com.sqlite'''

        hint_label=tk.Label(frame,text=hint,\
                justify=tk.LEFT,anchor=tk.NW)
        hint_label.grid(row=1,column=0,columnspan=3,\
                sticky=tk.W,padx=8)

        #--------------------Output dir--------------------
        label2=tk.Label(frame,text='Output folder:',\
                bg='#bbb')
        label2.grid(row=2,column=0,\
                sticky=tk.W,padx=8)

        self.out_entry=tk.Entry(frame)
        self.out_entry.grid(row=2,column=1,sticky=tk.W+tk.E,padx=8)
        self.out_button=tk.Button(frame,text='Choose',command=self.openDir)
        self.out_button.grid(row=2,column=2,padx=8,sticky=tk.E)
        


    def openDir(self):
        self.out_entry.delete(0,tk.END)
        dirname=askdirectory()
        self.out_entry.insert(tk.END,dirname)
        if len(dirname)>0:
            print('Output folder: %s' %dirname)
            self.hasout=True
            self.checkReady()


    def openFile(self):
        self.db_entry.delete(0,tk.END)
        ftypes=[('sqlite files','*.sqlite'),('ALL files','*')]
        initialdir='~/.local/share/data/Mendeley Ltd./Mendeley Desktop'
        initialdir=os.path.expanduser(initialdir)
        if os.path.isdir(initialdir):
            filename=askopenfilename(filetypes=ftypes,initialdir=initialdir)
        else:
            filename=askopenfilename(filetypes=ftypes)
        self.db_entry.insert(tk.END,filename)
        if len(filename)>0:
            print('Database file: %s' %filename)
            self.probeFolders()


    def probeFolders(self):
        dbfile=self.db_entry.get()
        try:
            db=sqlite3.connect(dbfile)
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
            ret=db.execute(query)
            data=ret.fetchall()
            df=pd.DataFrame(data=data,columns=['title',\
                    'folerid','name'])
            fetchField=lambda x, f: x[f].unique().tolist()
            folders=fetchField(df,'name')
            folders.sort()
            folders.remove(None)

            self.menfolderlist=['All',]+folders
            self.foldersmenu['values']=tuple(self.menfolderlist)
            self.foldersmenu.current(0)
            db.close()

            self.hasdb=True
            self.checkReady()

        except Exception as e:
            print('Failed to recoganize the given database file.') 
            print(e)





    
    def addActionFrame(self):

        frame=Frame(self,relief=tk.RAISED,borderwidth=1)
        frame.pack(fill=tk.X,side=tk.TOP,\
                expand=0,padx=8,pady=5)

        label=tk.Label(frame,text='Actions:',bg='#bbb')
        label.grid(row=0,column=0,sticky=tk.W,padx=8)

        #---------------Action checkbuttons---------------
        self.isexport=tk.IntVar()
        self.ishighlight=tk.IntVar()
        self.isnote=tk.IntVar()
        self.isbib=tk.IntVar()
        self.isseparate=tk.IntVar()

        self.check_export=tk.Checkbutton(frame,text='Export PDFs',\
                variable=self.isexport,command=self.doExport)

        self.check_highlight=tk.Checkbutton(frame,\
                text='Extract highlights',\
                variable=self.ishighlight,command=self.doHighlight)

        self.check_note=tk.Checkbutton(frame,\
                text='Extract notes',\
                variable=self.isnote,command=self.doNote)

        self.check_bib=tk.Checkbutton(frame,\
                text='Export .bib',\
                variable=self.isbib,command=self.doBib)

        self.check_separate=tk.Checkbutton(frame,\
                text='Save separately',\
                variable=self.isseparate,command=self.doSeparate,\
                state=tk.DISABLED)

        frame.columnconfigure(0,weight=1)

        self.check_export.grid(row=0,column=1,padx=8,sticky=tk.W)
        self.check_highlight.grid(row=0,column=2,padx=8,sticky=tk.W)
        self.check_note.grid(row=0,column=3,padx=8,sticky=tk.W)
        self.check_bib.grid(row=0,column=4,padx=8,sticky=tk.W)
        self.check_separate.grid(row=0,column=5,padx=8,sticky=tk.W)

        #---------------------2nd row---------------------
        subframe=Frame(frame)
        subframe.grid(row=1,column=0,columnspan=6,sticky=tk.W+tk.E,\
                pady=5)

        #-------------------Folder options-------------------
        folderlabel=tk.Label(subframe,text='Mendeley folder:',\
                bg='#bbb')
        folderlabel.pack(side=tk.LEFT, padx=8)

        self.menfolder=tk.StringVar()
        self.menfolderlist=['All',]
        self.foldersmenu=Combobox(subframe,textvariable=\
                self.menfolder,values=self.menfolderlist,state='readonly')
        self.foldersmenu.current(0)
        self.foldersmenu.bind('<<ComboboxSelected>>',self.setfolder)
        self.foldersmenu.pack(side=tk.LEFT,padx=8)

        
        #-------------------Quit button-------------------
        quit_button=tk.Button(subframe,text='Quit',\
                command=self.quit)
        quit_button.pack(side=tk.RIGHT,padx=8)

        #-------------------Stop button-------------------
        '''
        self.stop_button=tk.Button(subframe,text='Stop',\
                command=self.stop)
        self.stop_button.pack(side=tk.RIGHT,padx=8)
        '''
                
        #-------------------Start button-------------------
        self.start_button=tk.Button(subframe,text='Start',\
                command=self.start,state=tk.DISABLED)
        self.start_button.pack(side=tk.RIGHT,pady=8)

        #-------------------Help button-------------------

        self.help_button=tk.Button(subframe,text='Help',\
                command=self.showHelp)
        self.help_button.pack(side=tk.RIGHT,padx=8)



    def setfolder(self,x):
        self.foldersmenu.selection_clear()
        self.menfolder=self.foldersmenu.get()
        self.foldersmenu.set(self.menfolder)
        if self.menfolder=='All':
            print('Work on all folders.')
        else:
            print('Select Mendeley folder: '+str(self.menfolder))



    def doExport(self):
        if self.isexport.get()==1:
            print('Export annotated PDFs.')
        else:
            print('Dont export annotated PDFs.')

        self.checkReady()



    def doHighlight(self):
        if self.ishighlight.get()==1:
            print('Extract highlighted texts.')
            self.check_separate.configure(state=tk.NORMAL)
        else:
            print('Dont extract highlighted texts.')
            if self.isnote.get()==0:
                self.check_separate.configure(state=tk.DISABLED)
        self.checkReady()

    def doNote(self):
        if self.isnote.get()==1:
            print('Extract notes.')
            self.check_separate.configure(state=tk.NORMAL)
        else:
            print('Dont extract notes.')
            self.check_separate.state=tk.DISABLED
            if self.ishighlight.get()==0:
                self.check_separate.configure(state=tk.DISABLED)
        self.checkReady()

    def doBib(self):
        if self.isbib.get()==1:
            print('Export to .bib file.')
        else:
            print('Dont export .bib file.')
        self.checkReady()

    def doSeparate(self):
        if self.isseparate.get()==1:
            print('Save annotations separately.')
        else:
            print('Save all annotations to single file.')



    def showHelp(self):
        helpstr='''
Menotexport v1.0\n\n
- Export PDFs: Bulk export PDFs with annotations to <output folder>.\n
- Extract highlights: Extract highlighted texts and output to a txt file in <output folder>.\n
- Extract highlights: Extract notes and output to a txt file in <output folder>.\n
- Save separately: If on, save each PDF's annotations to a separate txt.\n
- See README.md for more info.\n
'''

        tkMessageBox.showinfo(title='Help', message=helpstr)
        print(self.menfolder.get())




    def start(self):
        dbfile=self.db_entry.get()
        outdir=self.out_entry.get()
        action=[]
        if self.isexport.get()==1:
            action.append('p')
        if self.ishighlight.get()==1:
            action.append('m')
        if self.isnote.get()==1:
            action.append('n')
        if self.isbib.get()==1:
            action.append('b')
        if self.isseparate.get()==1:
            separate=True
        else:
            separate=False
            
        if 'p' in action or 'm' in action or 'n' in action or 'b' in action:
            self.db_button.configure(state=tk.DISABLED)
            self.out_button.configure(state=tk.DISABLED)
            self.start_button.configure(state=tk.DISABLED)
            self.help_button.configure(state=tk.DISABLED)
            self.foldersmenu.configure(state=tk.DISABLED)
            self.check_export.configure(state=tk.DISABLED)
            self.check_highlight.configure(state=tk.DISABLED)
            self.check_note.configure(state=tk.DISABLED)
            self.check_bib.configure(state=tk.DISABLED)
            self.check_separate.configure(state=tk.DISABLED)
	    self.messagelabel.configure(text='Message (working...)')

            folder=None if self.menfolder=='All' else self.menfolder

            args=[dbfile,outdir,action,folder,separate,True]

            self.workthread=WorkThread('work',False,self.stateq)
            self.workthread.deamon=True

            self.workthread.args=args
            self.workthread.start()
            self.reset()
            '''
            self.workproc.apply_async(menotexport.main,args,\
                    callback=self.reset)
            self.workproc.join()
            '''



    def reset(self):
        while self.stateq.qsize() and self.exit==False:
            try:
                msg=self.stateq.get()
                if msg=='done':
                    self.db_button.configure(state=tk.NORMAL)
                    self.out_button.configure(state=tk.NORMAL)
                    self.start_button.configure(state=tk.NORMAL)
                    self.help_button.configure(state=tk.NORMAL)
                    self.foldersmenu.configure(state='readonly')
                    self.check_export.configure(state=tk.NORMAL)
                    self.check_highlight.configure(state=tk.NORMAL)
                    self.check_note.configure(state=tk.NORMAL)
                    self.check_bib.configure(state=tk.NORMAL)
                    self.check_separate.configure(state=tk.NORMAL)
                    self.messagelabel.configure(text='Message')
                    return
            except Queue.Empty:
                pass
        self.after(100,self.reset)


    
    def stop(self):
        #self.workthread.stop()
        pass
        

    def addMessageFrame(self):
        frame=Frame(self)
        frame.pack(fill=tk.BOTH,side=tk.TOP,\
                expand=1,padx=8,pady=5)

        self.messagelabel=tk.Label(frame,text='Message',bg='#bbb')
        self.messagelabel.pack(side=tk.TOP,fill=tk.X)

        self.text=tk.Text(frame)
        self.text.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
        self.text.height=10

        scrollbar=tk.Scrollbar(self.text)
        scrollbar.pack(side=tk.RIGHT,fill=tk.Y)

        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)

        



def main():

    stdoutq=Queue.Queue()
    sys.stdout=Redirector(stdoutq)

    root=tk.Tk()
    mainframe=MainFrame(root,stdoutq)
    mainframe.pack()

    root.mainloop()


if __name__=='__main__':
    main()


