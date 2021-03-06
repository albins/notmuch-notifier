#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Albin Stjerna, 2011
# Licenced under the GPLv3 or later.

import gtk, time, gobject, subprocess, json, textwrap, os
from threading import Thread

#gtk.gdk.threads_init()
gobject.threads_init()

class NotmuchMonitor():
    def __init__(self, qrs):
        self.statusicon = gtk.StatusIcon()
        self.statusicon.connect("popup-menu", self.right_click_event)

        # self.db = notmuch.Database()
        
        # # TODO get these from config file:
        self.qstrs = qrs

        # self.queries = map (lambda q: (q, notmuch.Query(self.db, q)), self.qstrs)

        
        self.quit = False

        self.nm_thread = Thread(target=self.poll_notmuch).start()
        
    def right_click_event(self, icon, button, time):
        menu = gtk.Menu()

        about = gtk.MenuItem("About")
        quit = gtk.MenuItem("Quit")
        
        about.connect("activate", self.show_about_dialog)
        quit.connect("activate", gtk.main_quit)
        
        menu.append(about)
        menu.append(quit)
        menu.show_all()
        
        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.statusicon)
        
    def show_about_dialog(self, widget):
		about_dialog = gtk.AboutDialog()
		
		about_dialog.set_destroy_with_parent(True)
		about_dialog.set_name("Notmuch notifier")
		about_dialog.set_version("0.1")
		about_dialog.set_authors(["Albin Stjerna"])
		
		about_dialog.run()
		about_dialog.destroy()

    def update_status(self, new_mail, tooltip):
        if new_mail:
            self.statusicon.set_from_icon_name("mail-unread")
            #self.statusicon.set_blinking(True)
        else:
            self.statusicon.set_from_icon_name("mail-read")
            #self.statusicon.set_blinking(False)

        self.statusicon.set_tooltip(tooltip)

    def on_error(self, message):
        md = gtk.MessageDialog(self, 
                               gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
                               gtk.BUTTONS_CLOSE, "Error loading file")
        md.run()
        md.destroy()

    def poll_notmuch(self):
        while not self.quit:
            #print "in loop"

            result = ""
            new_mail = False
            for q in self.qstrs:
                answer = []
                hits = 0
                subjects = ""
                p = subprocess.Popen(["notmuch", "search", "--format=json", q],
                                     stdout=subprocess.PIPE,
                                     stderr = subprocess.PIPE)

                stdout, stderr = p.communicate()
                if stderr:
                    error_dialog("Notmuch binary returned error: %s" % stderr)
                    #self.quit = True
                    #exit()
                answer = json.loads(stdout)
                wrapper = textwrap.TextWrapper(width=50,
                                               initial_indent="\t",
                                               subsequent_indent="\t\t")
                if answer:
                    for a in answer:
                        hits += a['matched']
                        subjects += wrapper.fill(a['subject']) + "\n"
                                                
                result += "%s: %d" % (q, hits)
                if hits > 0:
                    new_mail = True
                    result += "\n%s" % subjects
                result = result + "\n"

            gobject.idle_add(self.update_status, new_mail, result.strip())
        
            #print "sleeping"
            time.sleep(2)

def error_dialog(message, paren=None):
    md = gtk.MessageDialog(parent=paren,
                           type=gtk.MESSAGE_ERROR,
                           flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                           message_format=message,
                           buttons = gtk.BUTTONS_OK)
    md.run()
    md.destroy()


CONFIG_DIR = os.path.expanduser("~/.config/notmuch-notifier")
if not os.path.exists(CONFIG_DIR):
    os.mkdir(CONFIG_DIR)

if not os.path.exists(os.path.join(CONFIG_DIR, "queries")):
    print "Error: can't find configuration file"
    error_dialog("Error: can't find configuration file in %s." % CONFIG_DIR)
    exit
else:
    qs = []
    with open(os.path.join(CONFIG_DIR, "queries")) as f:
        for line in f:
            if len(line.strip()) > 0:
                qs.append(line.strip())

    if qs == []:
        print "Error: no parsable queries found in config file"
        error_dialog("Error: can't find configuration file")
        exit
    nm = NotmuchMonitor(qs)
    gtk.main()
    nm.quit = True
