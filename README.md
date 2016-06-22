# Menotexport

**Menotexport (Mendeley-Note-Export) extracts and exports highlights, notes and PDFs from your Mendeley database**

## What does this do?

Menotexport is a simple python solution to help extracts and exports annotations (highlighted
texts, sticky notes and notes) you made in the build-in PDF reader of Mendeley, bulk-export
PDFs with annotations, and bulk-export meta-data with annotations to .bib file.

*Mendeley is a desktop and web program for managing and sharing research
papers.* It offers free desktop clients for Windows, OSX and Linux. But the
software is not open source, and their support team has been real slow in responding
to customers feature requests, some of which has been proposed by many for YEARS.
This tool aims at solving the following:

### 1. Bulk export annotated PDFs.

Annotations (highlights and notes) made inside Mendeley are saved not directly onto
the relevant PDFs, but to a separate database file. Therefore these annotations can
not be viewered in other PDF readers other than Mendeley itself.

The native but awkward solution to export a PDF with its annotations is: in
Mendeley, open that PDF in the Mendeley PDF reader, go to Files -> Export PDF
with annotations. However to export all your collections, this has to be repeated
manually for each individual PDF in your library. To make it worse, the annotations
exported in this manner are **NOT** editable: they are saved as static texts, you can't even
delete a sticky note.

This tool can bulk export all PDFs with annotations while keeping your Mendeley
folder structure, and the annotations are readable and editable by other PDF
softwares. ~~NOTE that PDFs with no annotations are not exported.~~ PDFs with
no annotations are simply copied to the target location, so you have the
complete library structure.

### 2. Extract annotation texts.

To extract texts from the highlights, sticky notes and notes (in the right-hand
side-bar) in a PDF, other than Copy-n-Paste one by one, some softwares offer
an automated solution.

*skim* on OSX has the functionality to produce a summary of all annotations.

Some versions of *Foxit Reader* can do that (on windows, not on the Linux version, not sure about Mac).

Pro versions of *Adobe Reader* **may** have that too.

Most of the PDF readers in Linux do not have that functionality. (Let me know if you find one).

This tool could extract the texts from the highlights and notes in the documents in Mendeley
to a plain text file, and format the information in a sensible structure using markdown syntax.

### 3. Export libray to .bib file.

Exporting to .bib is natively supported in Mendeley, by going to Tools -> Options -> Bibtex. There
you can specify exporting the whole library to a single file or in a per-folder manner. However, your
whole annotations won't be included. This tool helps you pack-up as much information as possible to
a .bib file, which might be helpful for people who want to migrate to another management tool without
loosing too much efforts put into Mendeley.

Fields that are exported to a .bib entry (as long as they are present in your Mendeley document record):

	- citationkey
	- authors
	- year
	- title
	- publication
	- volume
	- issue
	- pages
	- doi
	- abstract
	- arxivId
	- chapter
	- country
	- city
	- edition
	- institution
	- isbn
	- issn
	- month
	- publisher
	- series
	- type
	- read            # Read or not
	- favourite       # Marked as Favourite or starred in Mendeley 
	- tags            # Tags added to a document
	- file            # Location of the attached PDF on local disk 
	- folder          # Folder name in the Mendeley library

### 4. Updates in v1.2: perserves sub-folder structures and adds new highlight colors

Thanks to user feedbacks I realized that Mendeley supports embedded folder structures. This feature
is now properly addressed in the new update: the exported PDFs, and their corresponding "file" entries in the
exported .bib file now reflect the folder structure in Mendeley library (empty folders are omitted, embedded folders are processed recursively).

You are allowed to create folders with same name in Mendeley, so long as they appear in different parent folders. In case you did do so, they will be labelled differently in the GUI version: e.g. "folderA", "folder1/folderA" and "folder2/folderA" are used to distinguish these three "folderA"s. 

Mendeley 1.16.1 introduces 7 more highlight colors, these are replicated in the exported PDFs.

### **NEW** Updates in v1.3: improves accuracy in highlight extractions.

The new version uses two text extracting utilities (*pdfminer* and *pdftotext*) to extract highlighted texts from PDFs, and creates much better outputs than the previous *pdfminer*-only version. The cost is an extra dependency to satisfy (see below), and a slight drop in execution speed. However, this new feature is optional: if you don't care about highlight extraction or don't have *pdftotext* available on the system, it will fall back to the *pdfminer*-only solution.



## Installation

- For command line or GUI usage on Linux or Mac or Win, download the zip and unzip to any folder. Make sure you have all the dependencies listed below and Python 2.7.

- NOTE that Windows user may need to manually update their sqlite3 dll. If you encounter the following error when connecting to the sqlite dataset:

```
Failed to recoganize the given database file.
file is encrypted or is not a database
```

Then download the latest version of *sqlite3* from [here](https://www.sqlite.org/download.html), and copy the `sqlite3.dll` file to the `DLLs` folder in your python installation directory. Note that if you have your python environment set up using *Anaconda*, be sure to copy to the `DLLs` folder in the specific env folder.

- For Windows specific GUI (**OUTDATED**), only need to get the `Menotexport-win64.zip` file. Download from dropbox: https://www.dropbox.com/s/64267kqvmlemaz8/menotexport-win64.rar?dl=0



## Usage

**NOTE: If you obtained this tool before 2016-04-15, I've made some changes that make it behave differently.**

### Command line

```
python menotexport.py [-h] [-p] [-m] [-n] [-b] [-s] [-f folder] dbfile outputdir
```

where

- `-h`: Show help messages.
- `-p`: Bulk export PDFs (including PDFs with annotations and those without annotations as well).
- `-m`: Extract markups (highlighted texts), also affects the outputs of the `-b` option.
- `-n`: Extract notes (sticky notes and side-bar notes), also affects the outputs of the `-b` option.
- `-b`: Export to .bib file. 
- `-s`: Save extracted texts to a separate txt file for each PDF. Default to
      save all texts to a single file.
- `-f`: Select to process only a Mendeley folder. Note this is case sensitive and match has to be literal.
        If not given, process all folders in the Mendeley library.
- `dbfile`: Absolute path to the Mendeley database file. In Linux systems default location is
  `~/.local/share/data/Mendeley\ Ltd./Mendeley\ Desktop/your_email@www.mendeley.com.sqlite`
- `outputdir`: folder to save outputs. The Mendeley library folder structure will be preserved by
   creating sub-directories using folder names under `outputdir`.

- If `-s`, texts for each PDF is saved to `Anno_PDFTITLE.txt` (if both `-m` and
`-n` are given), or to `Highlights_PDFTITLE.txt` or `Notes_PDFTITLE.txt` (if
either `-m` or `-n` is given).

- If not `-s`, save extracted texts from all PDFs to `Mendeley_annotations.txt`
(if both `-m` and `-n` are given), or to `Mendeley_highlights.txt` or
`Mendeley_notes.txt` (if either `-m` or `-n` is given). 

- If not `-s`, also generate another txt `Mendeley_annotations_by_tags.txt` where
information is grouped by tags.

- If `-p` and `-n`, your sticky notes will be placed in the exported PDFs at
  the same locations as in Mendeley.  If the document has side-bar notes (those
  you created in the right-hand side-bar in Mendeley), it will be transfered to
  the exported PDF as a sticky note at the top-left corner of the 1st page.
  All sticky notes are editable and deletable, but the formatting (bold,
  itatlic or underline) are gone.

- If `-b` and `-m`, a field `annote` will be created in each entry in the .bib
  file, containing the highlighted texts in the PDF (use with caution, see
  below). Similarly `-b` with `-n` will include the notes in `annote` (even if
  the document doesn't have a PDF attached to it, you can still make notes in
  the side-bar). Giving `-m` and `-n` will include both.

- If `-b` and `-p`, a field `file` will be created in each entry (those that
  have attached PDFs) in the .bib file, containing the path to the exported PDF,
  in the exported location:
  `outputdir/folder/PDF_FILE.pdf`.


Example:

To bulk export, extract and save to separate txt files:

```
python menotexport.py -pmns <dbfile> <outputdir>
```

To bulk export all PDFs and extract all annotations in Mendeley folder "Tropical_Cyclones" and save extracted annotations to a single file: 

```
python menotexport.py -pmn -f "Tropical_Cyclones" <dbfile> <outputdir>
```

To bulk export all PDFs, extract all annotations in all Mendeley folders, and
save annotations + meta-data to .bib file:


```
python menotexport.py -pmnb <dbfile> <outputdir>
```

### GUI

Launch `menotexport-gui.py` (or `menotexport-gui.exe`), select the Mendeley database file and an output folder. Select the actions to perform (see above), then *start*. 


## Caveats and further notes

- The bulk PDF export works with **quite good** accuracy, most highlights and notes are
  reproduced as they should be. **NOTE** that users have reported mis-alignments in highlighted texts
  when the exported PDF is opened in *Qiqqa*, I'm not sure it's more due to *Qiqqa* or this tool.
- Note extraction works with **quite good** accruacy.
- **Highlight extraction accuracy is compromised**, due to the inherent nature of the PDF
  format. Not all texts are correctly extracted, and the order they appear in the output
  may not be exactly the same as in the PDFs (top-down, left-right). The performance tends to get
  particularly chaotic when the highlights cover some non-roman characters (e.g. Greek letters or math
  symbols). DO proof read afterwards.
- Due to non-satisfactory performance in the highlights extraction, you probably want to exclude that from
  the exported .bib file entries. To do that, just don't toggle the `-m` option when using `-b`. The highlights
  will be replicated in the exported PDFs even if `-m` is not given.
- Highlighted texts from a single "block" of texts are treated as one record/entry. A "block" of
  texts is a continuous chunk of texts in the PDF, could be a whole paragraph, a single
  line separated from others, or a single isolated word. 
- Citationkeys and tags are added to the extracted texts in the save .txt files to facilitate further information
  processes, both can be editted in Mendeley.
- If choose to save all annotations to a single file, the programme also re-structure the extracted texts
  and organize them by their tags before saving to a separate file. Pieces of texts from a PDF that isn't taged are given a tag of @None.
- This is not necessarily a bug but might be worth noting: if you choose to process all the Mendeley folders and export the PDFs, the duplicated files in different folders will be duplicated on the disk as well, therefore taking up multiples of disk spaces. Similarly the .bib file may contain duplicated entries, with different "folder" and "file" fields.
- Sometimes your edits inside Mendeley may not be saved immediately to the database file. In such cases just reboot Mendeley. No needed to reboot Menotexport (if you are using the GUI), as each time you press the "start" button it will issue a new connection to the database.
- Possible follow-ups one can do: re-format the extracted txts to PDFs, docs or sync into
  your Evernote account, will probably implement these in a later version.
- To batch upload to **Evernote**, check out this repo: [txt2evernote](https://github.com/Xunius/txt2evernote).


## Dependencies

Developed in python2.7. **NOT** compatible with python3+ (*pdfminer* doesn't support python3).

It requires the following python packages:
- PyPDF2
- sqlite3
- pandas
- pdfminer (NOTE: version 2014+ is needed)
- numpy
- BeautifulSoup4

**(Optional but recommended)** For better performances in highlight extraction, it further requires the *pdftotext* software.

- Linux: *pdftotext* comes with most popular Linux distros. In case you need to install it: 

    sudo apt-get install poppler-utils
    
- Windows: Download the *poppler* package from [here](http://blog.alivate.com.au/poppler-windows/), unpack to any folder, then add the path to the `pdftotext.exe` file (e.g. `D:\Downloads\poppler-0.44_x86\poppler-0.44\bin`) to your PATH environmental variable. How to do this is system version dependent, please google. NOTE that the *pdftotext* in the *xpdf* package for Windows does not work: it doesn't have coordinate-based portion extraction.

It further incorporates (with minor adjustments) the pdfannotation.py file from
the [Menextract2pdf](https://github.com/cycomanic/Menextract2pdf) project.

It further incorporates (with no adjustments) the pylatexenc module from
the [pylatexenc](https://github.com/phfaist/pylatexenc) project.


## Platform/OS

The software is tested on Linux and Windows 10 (**the win-GUI version is outdated**). Should also run on Mac.



## Versions

* 0.1: First release
* 1.0: Added GUI and Windows version
* 1.1: Added export of non-annotated PDFs and export to .bib.
* 1.2: Works with subfolders. If a folder is chosen to process, also includes all subfolders.
	   Replicates the 8 different highlight colors introduced in Mendeley 1.16.1 version, in the exported PDFs.
* 1.3: Call *pdftotext* to work with *pdfminer* for better highlight extraction, if *pdftotext* not available, fall back         to old approach. Some other improvements in highlight extraction.


## Licence

The script is distributed under the GPLv3. The pdfannotations.py file is
LGPLv3. pylatexenc is under MIT license.

## Related projects

* [Mendeley2Zotero](https://github.com/flinz/mendeley2zotero)
* [Adios_Mendeley](https://github.com/rdiaz02/Adios_Mendeley)
* [Menextract2pdf](https://github.com/cycomanic/Menextract2pdf)
* [txt2evernote](https://github.com/Xunius/txt2evernote)
* [tagextract](https://github.com/Xunius/tagextract)

