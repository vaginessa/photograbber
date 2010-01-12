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

        # login button
        imglogin = PhotoImage(file="img/login.ppm")
        self.bLogin = Button(self, image=imglogin, command=self.fblogin)
        self.bLogin.image = imglogin
        self.bLogin.pack()

        # logged in button & list
        imgcreep = PhotoImage(file="img/creepon.ppm")
        self.bCreep = Button(self, image=imgcreep, command=self.creep)
        self.bCreep.image = imgcreep
        self.pFrame = Frame(self)
        self.sb = Scrollbar(self.pFrame, orient=VERTICAL)
        self.lbPeople = Listbox(self.pFrame, yscrollcommand=self.sb.set, selectmode=SINGLE)
        self.sb.config(command=self.lbPeople.yview)
        self.sb.pack(side=RIGHT, fill=Y)
        self.lbPeople.pack(side=RIGHT, fill=BOTH, expand=1)

        # download button
        imgdownload = PhotoImage(file="img/download.ppm")
        self.bDownload = Button(self, image=imgdownload, command=self.download)
        self.bDownload.image = imgdownload

        # display download status
        self.lDownload = Label(self)

        # quit button
        imgquit = PhotoImage(file="img/quit.ppm")
        self.bQuit = Button(self, image=imgquit, command=self.do_quit)
        self.bQuit.image = imgquit


    # display about information
    def aboutmsg(self):
        showinfo("About PhotoGrabber", "Developed by Tommy Murphy:\n"
            + "eat.ourbunny.com\n\n"
            + "Facebook API:\ngithub.com/sciyoshi/pyfacebook\n\n"
            + "Icons:\neveraldo.com/crystal")

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
        self.bLogin.pack_forget()
        self.bCreep.pack(fill=X)

    # choose who to creep on
    def creep(self):
        try:
            self.facebook.auth.getSession()
            self.people = self.facebook.fql.query("SELECT uid, name FROM user WHERE uid IN (SELECT uid2 FROM friend WHERE uid1 = " + str(self.facebook.uid) +  ")")

            me = dict(uid=self.facebook.uid,name="Myself")
            self.people.sort()

            for person in self.people :
                name = person['name']
                self.lbPeople.insert(END, name)

            self.lbPeople.insert(0, "Myself")
            self.people.insert(0,me)

            self.pFrame.pack(fill=X)

        except Exception, e:
            self.error(e)

        self.bCreep["state"]=DISABLED
        self.bDownload.pack()


    # download button event
    def download(self):
        # get listbox selection before directory prompt
        item = self.lbPeople.curselection()
        # ask for a directory
        self.directory = tkDirectoryChooser.askdirectory()

        # show the fb login button
        if self.directory != "":
            self.lbPeople["state"]=DISABLED

            # check listbox selection
            if len(item) == 1:
                uid = self.people[int(item[0])]['uid']
                self.dl_name = self.people[int(item[0])]['name']
            else:
                uid = self.facebook.uid
                self.dl_name = "Myself"

            # download
            dl = downloader.FBDownloader(self.directory, uid, self.facebook,
                    self.update_status, self.error)
            dl.start()

            self.bDownload["state"] = DISABLED
            self.lDownload["text"] = "Beginning Download..."
            self.lDownload.pack()

    # update download status function
    def update_status(self, index, total):
        self.lDownload["text"] = str(index) + " of " + str(total)
        self.lDownload.pack()

        if index==total:
            self.bQuit.pack()
            self.dl_total = str(total)

    # oops an error happened!
    def error(self, e):
        showinfo("OH NOES ERROR!", "There was a problem, please try again!\n\n"
                + str(e))
        self.quit()

    # quit button event
    def do_quit(self):
        self.bQuit["state"] = DISABLED
        my_message = ( "(Your Name) downloaded " + self.dl_total +
                       " pictures of " + self.dl_name + " with PhotoGrabber!" )
        try:
            if askokcancel("Quit", "Would you like to post the following story to your wall... This might be both hilarious and embarassing for you...\n\n \"" + my_message + "\""):
                self.facebook.request_extended_permission("publish_stream")

                if askokcancel("Quit", "Press OK to post or CANCEL to quit."):
                    self.facebook.stream.publish(
                            message = "downloaded " + self.dl_total +
                                        " pictures of " + self.dl_name +
                                        " with PhotoGrabber!",
                            attachment = '{"name":"PhotoGrabber","href":"http://www.facebook.com/apps/application.php?id=139730900025","description":"This app lets you download pictures from Facebook."}')
            self.quit()
        except Exception, e:
            self.error(e)

app = Application()
app.master.title("PhotoGrabber")
app.master.resizable(width=FALSE, height=FALSE)
app.mainloop()
