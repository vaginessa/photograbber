#!/usr/bin/python
from Tkinter import *
from tkMessageBox import *
from facebook import Facebook
import tkDirectoryChooser
import downloader
import sys

class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack(fill=BOTH, expand=1)
        if sys.platform == 'win32':
            self.master.iconbitmap(default='img/pg.ico')
        self.createWidgets()

    def createWidgets(self):
        # menubar
        mb = Menu(self.master)
        self.master.configure(menu=mb)

        filemenu=Menu(mb,tearoff=0)
        mb.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="About", command=self.aboutmsg)
        filemenu.add_command(label="Quit", command=self.quit)

        # select folder
        imga = PhotoImage(file="img/1.ppm")
        self.bFolder = Button(self, image=imga, command=self.opendir)
        self.bFolder.image = imga
        self.bFolder.pack()

        # display selected folder
        self.lFolder = Label(self)

        # login button
        imgb = PhotoImage(file="img/2.ppm")
        self.bLogin = Button(self, image=imgb, command=self.fblogin)
        self.bLogin.image = imgb

        # download button
        imgc = PhotoImage(file="img/3.ppm")
        self.bDownload = Button(self, image=imgc, command=self.download)
        self.bDownload.image = imgc

        # display download status
        self.lDownload = Label(self)

        # quit button
        imgd = PhotoImage(file="img/4.ppm")
        self.bQuit = Button(self, image=imgd, command=self.quit)
        self.bQuit.image = imgd


    # display about information
    def aboutmsg(self):
        showinfo("About PhotoGrabber", "Developed by Tommy Murphy:\n"
            + "eat.ourbunny.com\n\n"
            + "Facebook API:\ngithub.com/sciyoshi/pyfacebook\n\n"
            + "Icons:\neveraldo.com/crystal")

    # destination button event
    def opendir(self):
        # ask for a directory
        self.directory = tkDirectoryChooser.askdirectory()

        # show the fb login button
        if self.directory != "":
            self.bFolder["state"]=DISABLED
            self.lFolder["text"]=self.directory
            self.lFolder.pack(fill=X)
            self.bLogin.pack()

    # login button event
    def fblogin(self):
        #api_key and secret_key
        try:
            self.facebook = Facebook('227fe70470173eca69e4b38b6518fbfd', '6831060776f620cc2588fd053250cabb')
            self.facebook.auth.createToken()
            self.facebook.login()
        except Exception, e:
            self.error(e)

        #show download button
        self.bLogin["state"]=DISABLED
        self.bDownload.pack()

    # download button event
    def download(self):
        self.bDownload["state"]=DISABLED
        self.bDownload.pack()

        try:
            self.facebook.auth.getSession()
        except Exception, e:
            self.error(e)

        # download
        dl = downloader.FBDownloader(self.directory, self.facebook,
                self.update_status, self.error)
        dl.start()

        self.lDownload["text"] = "Beginning Download..."
        self.lDownload.pack()

    # update download status function
    def update_status(self, index, total):
        self.lDownload["text"] = str(index) + " of " + str(total)
        self.lDownload.pack()

        if index==total:
            self.bQuit.pack()

    # oops an error happened!
    def error(self, e):
        showinfo("OH NOES ERROR!", "There was a problem, please try again!\n\n"
                + str(e))
        self.quit()

app = Application()
app.master.title("PhotoGrabber")
app.master.resizable(width=FALSE, height=FALSE)
app.mainloop()
