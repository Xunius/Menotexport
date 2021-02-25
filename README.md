# Menotexport

**Menotexport (Mendeley-Note-Export) extracts and exports highlights, notes and PDFs from your Mendeley database**

### IMPORTANT NOTE:

It seems that Mendeley has decided to put an encryption in version 1.19 on the database file from which various information (your highlights, notes, all metadata of the documents) is retrieved by this tool.

Some relavent info on this:

* [zotero forum](https://www.zotero.org/support/kb/mendeley_import)
* [Mendeley release note](https://www.mendeley.com/release-notes/v1_19)
* [a blog sharing a workaround](https://hk.saowen.com/a/2238ee56dccb0df24eb98973c499f19ebdf1058e36ea713689b049c32563a9db)
* [issue report](https://github.com/Xunius/Menotexport/issues/25)

I have little experience handling sqlite data encryption/decryption. So if anyone can offer any suggestion it will be greatly appreciated, including any advises on potential legal issues distributing a tool like this that bypasses their encryption.

Also if you encounter an error when trying to run this tool on your local database file:
```
# <Menotexport>: Failed to recoganize the given database file.
file is not a database
```

before we figure out an easy to bypass this, please consider backing up your database file, and trying an older version of Mendeley before 1.19. Sorry for the trouble.

**Update 2020-10-09**: Here is a method suggested by a user to decrypt the sqlite database file: https://eighty-twenty.org/2018/06/13/mendeley-encrypted-db. See also this [issue report](https://github.com/Xunius/Menotexport/issues/25).

**Update 2021-02-25**: Here is some [tips for migration to Zenodo](https://github.com/Xunius/Menotexport/issues/35), thanks for the inputs from **pboley**.

### More rants

I thought I messed up my sync, but no, it appears to be a much larger scale issue with Mendeley: lots of people are losing their PDFs after syncing. See [this twitter](https://twitter.com/mendeleysupport/status/1002557134519840769?lang=en) and [their support page](https://service.elsevier.com/app/answers/detail/a_id/27709/supporthub/mendeley/p/10941/).

I was trying their re-activation workaround, but guess what, they say that sync setting is deprecated in my version (1.17.10) and I need to upgrade to the latest, which encrypts your LOCAL data. WTF Mendeley?!

Lesson learnt: backup your data regularly, and better still, ditch Mendeley.

## What does this do?

Menotexport is a simple python solution to help extract and export annotations (highlighted
texts, sticky notes and notes) you made in the build-in PDF reader of Mendeley, bulk-export
PDFs with annotations, and bulk-export meta-data with annotations to .bib or .ris file.

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
Mendeley, open that PDF in the Mendeley PDF reader, go to `Files` -> `Export PDF
with annotations`. However to export all your collections, this has to be repeated
manually for each individual PDF in your library. To make it worse, the annotations
exported in this manner are saved as static texts and are not editable.

This tool can bulk export all PDFs with annotations while keeping your Mendeley
folder structure, and the annotations are readable and editable by other PDF
softwares.  PDFs with no annotations are simply copied to the target location, so you have the
complete library structure.

### 2. Extract annotation texts.

To extract texts from the highlights, sticky notes and notes ("General notes" in the right-hand
side-bar) in a PDF, other than Copy-n-Paste one by one, some softwares offer
an automated solution.

*skim* on OSX has the functionality to produce a summary of all annotations.

Some versions of *Foxit Reader* can do that (on windows, not on the Linux version, not sure about Mac).

Pro versions of *Adobe Reader* **may** have that too.

Most of the PDF readers in Linux do not have that functionality. (Please let me know if you find one).

This tool could extract the texts from the highlights and notes in the documents in Mendeley
to a plain text file, and format the information in a sensible structure using markdown syntax.

### 3. Export libray to .bib file.

Exporting to .bib is natively supported in Mendeley, by going to `Tools` -> `Options` -> `Bibtex`. There
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
	- day
	- publisher
	- series
	- type
	- keywords
	- read            # Read or not
	- favourite       # Marked as Favourite or starred in Mendeley
	- tags            # Tags added to a document
	- file            # Location of the attached PDF on local disk
	- folder          # Folder name in the Mendeley library

## Some other features

### 1. Export preserves sub-folder structures

Mendeley supports embedded folder
structures and is properly addressed by this tool: the exported PDFs, and
their corresponding "file" entries in the exported .bib (or .ris) file now
reflect the folder structure (empty folders are omitted,
embedded folders are processed recursively).

You are allowed to create folders with the same name in Mendeley, so long as
they appear in different parent folders. In case you did do so, they will be
labelled differently in the GUI version: e.g. "folderA", "folder1/folderA" and
"folder2/folderA" are used to distinguish these three "folderA"s.

### 2. Highlight colors in Mendeley

Mendeley 1.16.1 introduces 7 more highlight colors, these are replicated in the exported PDFs.

### 3. Extra utility to help improve accuracy in highlight extractions;

Two text extracting utilities (*pdfminer* and *pdftotext*) are used to extract
highlighted texts from PDFs. The user can choose to install the relevant utility
to enable the *pdftotext* functions (installation details see below) to create
better outputs than the default *pdfminer* results. The cost is an
extra dependency to satisfy (see below), and a slight drop in execution speed.
However, this new feature is optional: if you don't care about highlight
extraction or don't have *pdftotext* available on the system, it will fall back
to the *pdfminer*-only solution.

### 4. Zotero-ready output format

Use the "-z" flag (command-line version), or toggle the "For import to Zotero" option (GUI
version) to re-format the exported .bib file, making it suitable to import into
Zotero. Therefore to migrate over to Zotero, specify "Export PDFs", "Extract
highlights", "Extract notes" and "Export to .bib" (by giving a "-pmnb" flag),
process a folder or the entire Mendeley library, then point the "import"
function of Zotero to the exported .bib file. Document entries with meta-data,
notes (highlighted texts + notes), tags and the attached PDFs (if they exist)
will be added.

### 5. Export to .ris format.

Export meta-data and annotations to .ris file. If `-z` flag is toggled, the
output can be properly recognized by Zotero, and a migration to Zotero via the
.ris approach can be achieved by a process with `-pnmrz` options.

### 6. Custom template formatting for exported annotations.

Annotations (notes+highlights) can be formatted in the way you like.

In the `lib` folder there is a file `annotation_template.py` which contains a working
example template to format the output of the exported annotations.

To use custom template:

* in command line: add the `-t` option.
* in GUI: toggle the "use custom template (experimental)" button.

Currently, these variables are available in building a template:

* text : content for a note, or highlighted texts for a highlight.
* page : page number of the note/highlight in the PDF file (not necessarily the same as printed out at the page margin).
* title: title of the document.
* tags : tag list.
* ctime: creation time.
* author : author(s) of the document.
* note_author: author(s) of the annotation.
* citationkey: citation key.
* num : an integer id of the note/highlight, counting restarts in each document.

Put any of them in curly brackets to use them, e.g. `{title}`. NOTE no spaces in brackets. More instructions can be found in the template file.

For deeper modification of the output formatting, you can hack into this file: `/lib/exportannotation.py`.


## Installation

### 1. Install via `conda`.

For command line or GUI usage on Linux (64bit), recommend installing using *conda*:

```
conda create -n menotexport python=2.7
source activate menotexport
conda install -c guangzhi menotexport
```

For the installation of *conda* (*Anaconda* or a lighter-weight version: *Miniconda*), see their [official site](https://www.continuum.io/downloads).

### 2. Pre-build binary GUI for Windows

For Windows 7 and Windows 10 (64bit) (**version 1.4, updated on 08-July-2017**), download `menotexport-gui-win7-win10.zip` from Google Drive: https://drive.google.com/open?id=0B8wpnLHH0j1hTTM5cTE2TXg2b1k, unpack, then launch `menotexport-gui.exe`.

Version 1.4.4 (uploaded 10-Nov-2017, not fully tested yet, please provide feedbacks if this works correctly): https://drive.google.com/open?id=1rd-mOKspare4bkKWEMmm-2uwH04p-sIq.

Version 1.5.1 (uploaded 04-Sept-2018, not fully tested): https://drive.google.com/open?id=1v-f2Gfryzy__RUkF9c0aD1GXTuBJPpyv


### 3. Install the dependencies and use source code

If all above approaches fail:


- For command line or GUI usage on Linux or Mac or Win, download the zip and
  unzip to any folder. Make sure you have all the dependencies listed below and
  Python 2.7.

- NOTE that Windows user may need to manually update their sqlite3 dll. If you
  encounter the following error when connecting to the sqlite dataset:

```
Failed to recoganize the given database file.
file is encrypted or is not a database
```

Then download the latest version of *sqlite3* from [here](https://www.sqlite.org/download.html), and copy the `sqlite3.dll` file to the `DLLs` folder in your python installation directory. Note that if you have your python environment set up using *Anaconda*, be sure to copy to the `DLLs` folder in the specific env folder.



## Usage

**NOTE: If you obtained this tool before 2016-04-15, I've made some changes that make it behave differently.**

### Command line

```
python menotexport.py [-h] [-p] [-m] [-n] [-b] [-r] [-s] [-z] [-f folder] dbfile outputdir
```

where

- `-h`: Show help messages.
- `-p`: Bulk export PDFs.
- `-m`: Extract markups (highlighted texts), also affects the outputs of the `-b` option.
- `-n`: Extract notes (sticky notes and side-bar notes), also affects the outputs of the `-b` option.
- `-b`: Export to .bib file.
- `-r`: Export to .ris file.
- `-s`: Save extracted texts to a separate txt file for each PDF. Default to
      save all texts to a single file.
- `-z`: Re-format the exported .bib and/or .ris file to a format suitable to import into Zotero. Only works when `-b` and/or `-r` are toggled.
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

- If `-p` or `-n`, your sticky notes will be placed in the exported PDFs at
  the same locations as in Mendeley.  If the document has side-bar notes (aka
  "General note"), they will be transfered to
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
save annotations + meta-data to .bib file in a suitable format to import into Zotero:


```
python menotexport.py -pmnbz <dbfile> <outputdir>
```

### GUI

Launch `menotexport-gui.py` (or `menotexport-gui.exe`), select the Mendeley
database file and an output folder. Select the actions to perform (see above),
then *start*.


## Caveats and further notes


- **NOTE** that if your folders contain "/" in theirs names, it will trigger an error. Please remove "/" before using this tool.
- The bulk PDF export works with **quite good** accuracy, most highlights and notes are
  reproduced as they should be. **NOTE** that users have reported mis-alignments in highlighted texts
  when the exported PDF is opened in *Qiqqa*, I'm not sure it's more due to *Qiqqa* or this tool.
- Note extraction works with **quite good** accruacy.
- **Highlight extraction accuracy is compromised**. Not all texts are correctly extracted,
  and the order they appear in the output
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
  your Evernote account.
- To batch upload to **Evernote**, check out this repo: [txt2evernote](https://github.com/Xunius/txt2evernote).
- "Canonical documents", which are documents saved in Mendeley's "My Library" (kind of the root folder) but not belonging to any user created folder, the results are saved to a directory "Canonical-My Library".
- To help managing papers on local disk, I'm experimenting some [bash script tools](https://github.com/Xunius/doc_manage).
- Check out [papis](https://github.com/papis/papis): Powerful and highly extensible command-line based document and bibliography manager.
- A note for myself: when building the windows exe, downgrade setuptools to 19.2, use pandas=0.16, don't use pyinstaller inside anaconda otherwise the result package will be 10x bigger, may need to install pyinstaller from its git.

## Dependencies

Developed in python2.7. **NOT** compatible with python3+ yet.

1. It requires the following python packages:

    - PyPDF2
    - sqlite3
    - pdfminer (NOTE: version 2014+ is needed, the one in the Ubuntu repository has been out of date at the time of writing. Please check to make sure. If you get an error of "ImportError: No module named pdfdocument", you probably got an older version.)
    - BeautifulSoup4

2. **(Optional but recommended)** For better performances in highlight extraction, it further requires the *pdftotext* software.

    - Linux: *pdftotext* comes with most popular Linux distros. In case you need to install it:

        ```
        sudo apt-get install poppler-utils
        ```

    - Windows: Download the *poppler* package from [here](http://blog.alivate.com.au/poppler-windows/), unpack to any folder, then add the path to the `pdftotext.exe` file (e.g. `D:\Downloads\poppler-0.44_x86\poppler-0.44\bin`) to your PATH environmental variable. How to do this is system version dependent, please google. NOTE that the *pdftotext* in the *xpdf* package for Windows does not work: it doesn't have coordinate-based portion extraction.

It further incorporates (with minor adjustments) the pdfannotation.py file from
the [Menextract2pdf](https://github.com/cycomanic/Menextract2pdf) project.

It further incorporates (with no adjustments) the pylatexenc module from
the [pylatexenc](https://github.com/phfaist/pylatexenc) project.


## Platform/OS

The software is tested on Linux and Windows 7, 10. Should also run on Mac.



## Versions

* 1.5.1: Remove pandas dependency. Fix author list error.
* 1.5.0: Documents with more than 1 attactments (e.g. supplementary materials) are properly exported. Fix side-bar notes (aka "General notes") fetching problem.
* 1.4.4: Add custom annotation templation support (not mature yet). Fix auto-renaming function fixed.
* 1.4: Add export to .ris format.
"Canonical documents", which are documents saved in Mendeley's "My Library" (kind of the root folder) but not belonging to any user created folder, are now properly processed, and the results are saved to a directory "Canonical-My Library".
* 1.3: Call *pdftotext* to work with *pdfminer* for better highlight extraction, if *pdftotext* not available, fall back         to old approach. Some other improvements in highlight extraction. Add special formatting of the .bib file for           Zotero import.
* 1.2: Works with subfolders. If a folder is chosen to process, also includes all subfolders.
	   Replicates the 8 different highlight colors introduced in Mendeley 1.16.1 version, in the exported PDFs.
* 1.1: Added export of non-annotated PDFs and export to .bib.
* 1.0: Added GUI and Windows version
* 0.1: First release

## Licence

The script is distributed under the GPLv3. The pdfannotations.py file is
LGPLv3. pylatexenc is under MIT license.

## Related projects

* [Meitingtrunk: reference manager with a similar interface to Mendeley](https://github.com/Xunius/MeiTingTrunk)
* [Mendeley2Zotero](https://github.com/flinz/mendeley2zotero)
* [Adios_Mendeley](https://github.com/rdiaz02/Adios_Mendeley)
* [Menextract2pdf](https://github.com/cycomanic/Menextract2pdf)
* [txt2evernote](https://github.com/Xunius/txt2evernote)
* [tagextract](https://github.com/Xunius/tagextract)
* [doc_manage](https://github.com/Xunius/doc_manage)

