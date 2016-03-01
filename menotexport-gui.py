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
'''



import sys
from ttk import Style,Combobox
from tkFileDialog import askopenfilename, askdirectory
import tkMessageBox
import menotexport
import Queue
import threading
import time
import sqlite3
import pandas as pd
if sys.version_info[0]>=3:
    import tkinter as tk
    from tkinter import Frame
else:
    import Tkinter as tk
    from Tkinter import Frame


stdout=sys.stdout


'''
class WorkThread(threading.Thread):
    def __init__(self,name,parent,q,lock):
        threading.Thread.__init__(self)
        self.name=name
        self.q=q
        self.parent=parent
        self.lock=lock

        self.exit=self.parent.exit
        print('start thread')

    def run(self):

        while not self.exit:
            self.lock.acquire()
            if not self.q.empty():
                ins=self.q.get()
                self.lock.release()
                if ins=='go':
                    #print('start run thread')
                    self.parent.psgo()
                elif ins=='stop':
                    pass
                    #print('Stop run thread')
            else:
                self.lock.release()
'''





class Redirector(object):
    def __init__(self,text_box):
        self.text_box=text_box

    def write(self,string):
        #self.text_box.update_idletasks()
        self.text_box.insert(tk.END,'# '+string)
        self.text_box.see(tk.END)
        self.text_box.update()


class MainFrame(Frame):
    def __init__(self,parent):
        Frame.__init__(self,parent)

        self.parent=parent
        self.width=700
        self.height=400
        self.title='Menotexport v1.0'

        self.initUI()

        self.hasdb=False
        self.hasout=False
        self.hasaction=False

        self.path_frame=self.addPathFrame()
        self.action_frame=self.addActionFrame()
        self.message_frame=self.addMessageFrame()
        sys.stdout=Redirector(self.text)

        '''
        self.exit=False
        self.queue=Queue.Queue(5)
        self.qlock=threading.Lock()
        self.workthread=WorkThread('workthread',self,self.queue,\
                self.qlock)
        '''



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
        self.style.theme_use('default')

        self.pack(fill=tk.BOTH,expand=True)
        self.centerWindow()

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
        print('Output folder: %s' %dirname)

        self.hasout=True
        self.checkReady()


    def openFile(self):
        self.db_entry.delete(0,tk.END)
        ftypes=[('sqlite files','*.sqlite'),('ALl files','*')]
        filename=askopenfilename(filetypes=ftypes)
        self.db_entry.insert(tk.END,filename)
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
            self.menfolders=['All',]+folders
            self.foldersmenu['values']=tuple(self.menfolders)
            self.menfolder.set('All')
            db.close()

            self.hasdb=True
            self.checkReady()
        except:
            print('Failed to recoganize the given database file.') 





    
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
        self.isseparate=tk.IntVar()

        self.check_export=tk.Checkbutton(frame,text='Export PDFs',\
                variable=self.isexport,command=self.doExport)

        self.check_highlight=tk.Checkbutton(frame,\
                text='Extract highlights',\
                variable=self.ishighlight,command=self.doHighlight)

        self.check_note=tk.Checkbutton(frame,\
                text='Extract notes',\
                variable=self.isnote,command=self.doNote)

        self.check_separate=tk.Checkbutton(frame,\
                text='Save separately',\
                variable=self.isseparate,command=self.doSeparate,\
                state=tk.DISABLED)

        frame.columnconfigure(0,weight=1)

        self.check_export.grid(row=0,column=1,padx=8,sticky=tk.W)
        self.check_highlight.grid(row=0,column=2,padx=8,sticky=tk.W)
        self.check_note.grid(row=0,column=3,padx=8,sticky=tk.W)
        self.check_separate.grid(row=0,column=4,padx=8,sticky=tk.W)

        #---------------------2nd row---------------------
        subframe=Frame(frame)
        subframe.grid(row=1,column=0,columnspan=5,sticky=tk.W+tk.E,\
                pady=5)

        #-------------------Folder options-------------------
        folderlabel=tk.Label(subframe,text='Mendeley folder:',\
                bg='#bbb')
        folderlabel.pack(side=tk.LEFT, padx=8)

        self.menfolder=tk.StringVar()
        self.menfolder.set('All')
        self.menfolders=['All',]
        self.foldersmenu=Combobox(subframe,textvariable=\
                self.menfolder,values=self.menfolders,state='readonly')
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
            action.append('e')
        if self.ishighlight.get()==1:
            action.append('m')
        if self.isnote.get()==1:
            action.append('n')
        if self.isseparate.get()==1:
            separate=True
        else:
            separate=False
            
        if 'e' in action or 'm' in action or 'n' in action:
            '''
            self.qlock.acquire()
            self.queue.put('go')
            self.qlock.release()

            self.workthread.start()
            #self.workthread.join()
            '''
            self.db_button.configure(state=tk.DISABLED)
            self.out_button.configure(state=tk.DISABLED)
            self.start_button.configure(state=tk.DISABLED)
            self.help_button.configure(state=tk.DISABLED)
            self.foldersmenu.configure(state=tk.DISABLED)
            self.check_export.configure(state=tk.DISABLED)
            self.check_highlight.configure(state=tk.DISABLED)
            self.check_note.configure(state=tk.DISABLED)
            self.check_separate.configure(state=tk.DISABLED)
	    self.messagelabel.configure(text='Message (working...)')

            folder=None if self.menfolder=='All' else [self.menfolder,]
            menotexport.main(dbfile,outdir,action,folder,True,\
                            True,separate,True)

            #--------------------After run--------------------
            self.db_button.configure(state=tk.NORMAL)
            self.out_button.configure(state=tk.NORMAL)
            self.start_button.configure(state=tk.NORMAL)
            self.help_button.configure(state=tk.NORMAL)
            self.foldersmenu.configure(state='readonly')
            self.check_export.configure(state=tk.NORMAL)
            self.check_highlight.configure(state=tk.NORMAL)
            self.check_note.configure(state=tk.NORMAL)
            self.check_separate.configure(state=tk.NORMAL)
	    self.messagelabel.configure(text='Message')

    
    def stop(self):
        self.exit=True
        self.qlock.acquire()
        self.queue.put('stop')
        self.qlock.release()
        

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
    root=tk.Tk()
    mainframe=MainFrame(root)
    mainframe.pack()
    root.mainloop()

if __name__=='__main__':
    main()


