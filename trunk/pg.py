#!/usr/bin/python
from Tkinter import *
from tkMessageBox import *
from facebook import Facebook
import tkDirectoryChooser
import downloader
import sys, traceback

class Application(Frame):
    def __init__(self, master=None, debug=False):
        Frame.__init__(self, master)
        self.master.title("PhotoGrabber")
        self.master.resizable(width=FALSE, height=FALSE)
        self.master.protocol("WM_DELETE_WINDOW", self.quit_wrapper) #press quit
        self.pack(fill=BOTH, expand=1)
        # fix icon on windows
        if sys.platform == 'win32':
            self.master.iconbitmap(default='img/pg.ico')
        # print debug info
        self.debug = debug
        # downloading thread
        self.dl = None
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

        # logged in button
        imgcreep = PhotoImage(file="img/creepon.ppm")
        self.bCreep = Button(self, image=imgcreep, command=self.creep)
        self.bCreep.image = imgcreep

        # list of friends
        self.pFrame = Frame(self)
        self.sb = Scrollbar(self.pFrame, orient=VERTICAL)
        self.lbPeople = Listbox(self.pFrame, yscrollcommand=self.sb.set,
                                selectmode=SINGLE)
        self.sb.config(command=self.lbPeople.yview)
        # check boxes
        self.default_cb = Checkbutton(self.pFrame,
                                      text="All tagged photos of the user")
        self.default_cb.select()
        self.default_cb["state"]=DISABLED
        self.default_cb.pack(fill=X)
        self.full_albums = BooleanVar()
        self.full_cb = Checkbutton(self.pFrame,
                             text="Entire album if it contains a tagged photo",
                             var=self.full_albums)
        self.full_cb.pack(fill=X)
        self.user_albums = BooleanVar()
        self.user_cb = Checkbutton(self.pFrame,
                                   text="Albums uploaded by the user",
                                   var=self.user_albums)
        self.user_cb.pack(fill=X)
        self.extras = BooleanVar()
        self.extras_cb = Checkbutton(self.pFrame,
                                     text="Comments and tagging information",
                                     var=self.extras)
        self.extras_cb.pack(fill=X)
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
            + "Contributions from Bryce Boe:\n"
            + "bryceboe.com\n\n"
            + "Facebook API:\ngithub.com/sciyoshi/pyfacebook\n\n"
            + "Icons:\neveraldo.com/crystal")

    # login button event
    def fblogin(self):
        # api_key and secret_key
        try:
            self.facebook = Facebook('227fe70470173eca69e4b38b6518fbfd',
                                     '6831060776f620cc2588fd053250cabb')
            self.facebook.auth.createToken()
            self.facebook.login()
        except Exception, e:
            self.error(e)

        # hide login button
        self.bLogin["state"]=DISABLED
        self.bLogin.pack_forget()
        # select a user button
        self.bCreep.pack(fill=X)

    # load the list of friends
    def creep(self):
        try:
            self.facebook.auth.getSession()

            q = ''.join(['SELECT uid, name FROM user WHERE uid IN ',
                         '(SELECT uid2 FROM friend WHERE uid1 = %(name)s) ',
                         'OR uid=%(name)s']) % {"name":self.facebook.uid}
            self.people = self.facebook.fql.query(q)
            self.people.sort()

            for person in self.people :
                name = person['name']
                self.lbPeople.insert(END, name)

            me = dict(uid=self.facebook.uid,name="Myself")
            self.lbPeople.insert(0, "Myself")
            self.people.insert(0,me)

            # show the list of people
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

        # show the fb login butto
        if self.directory != "":
            self.lbPeople["state"]=DISABLED
            self.full_cb["state"]=DISABLED
            self.user_cb["state"]=DISABLED
            self.extras_cb["state"]=DISABLED

            # check listbox selection
            if len(item) == 1:
                uid = self.people[int(item[0])]['uid']
            else:
                uid = self.facebook.uid

            # make dictonary of friends
            friends = dict((x['uid'], x['name']) for x in self.people)

            # download
            self.dl = downloader.FBDownloader(self.directory, uid, friends,
                                              self.full_albums.get(),
                                              self.user_albums.get(),
                                              self.extras.get(),
                                              self.facebook,
                                              self.update_status,
                                              self.error,
                                              self.remote_exit)
            self.dl.start()

            self.bDownload["state"] = DISABLED
            self.lDownload["text"] = ''.join(["Collecting photo list... ",
                                              "(this may take a while)"])
            self.lDownload.pack()

    # update download status function - callback from thread
    def update_status(self, index, total):
        self.lDownload["text"] = '%s of %s' % (index, total)
        self.lDownload.pack()

        if index==total:
            self.bQuit.pack()

    # oops an error happened! - callback from thread
    def error(self, e, pgExit=True):
        if self.debug:
            sys.stderr.write(str(e) + "\n")
            traceback.print_exc()

        # some errors dont require GUI intervention
        if not pgExit:
            return

        # others do
        showinfo("OH NOES ERROR!", "There was a problem, please try again!\n\n"
                + str(e))
        self.quit()

    # handle requeest to exit - callback from thread
    def remote_exit(self):
        print "remote exit called!"
        self.quit() # destroy widgets

    # quit button event
    def do_quit(self):
        self.bQuit["state"] = DISABLED
        self.quit()

    # window manager quit - callback from UI
    def quit_wrapper(self):
        #if self.dl and askokcancel('Quit','Do you really want to quit?'):
        if self.dl:
            self.dl._thread_terminated = True
            if self.debug:
                sys.stderr.write('Waiting for download thread to terminate\n')
            while self.dl.isAlive():
                if self.debug:
                    sys.stderr.write('.')
                    sys.stderr.flush()
                self.dl.join(1)
            self.dl = None
            if self.debug:
                sys.stderr.write('\n')
                sys.stderr.flush()
        self.quit()

def main(debug=False):
    app = Application(debug=debug)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        if app.dl: app.dl._thread_terminated = True
    if app.dl: app.dl.join()

if __name__ == '__main__':
    main(debug = len(sys.argv) > 1)
