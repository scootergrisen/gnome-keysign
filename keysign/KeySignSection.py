#!/usr/bin/env python
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2016 Tobias Mueller <muelli@cryptobitch.de>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.

import logging
import sys

from gi.repository import Gtk

from .KeyPresent import KeyPresentPage
from . import Keyserver
from .KeysPage import KeysPage
from .SignPages import KeyDetailsPage
from .gpgmh import get_public_key_data

log = logging.getLogger(__name__)


class KeySignSection(Gtk.VBox):

    def __init__(self):
        '''Initialises the section which lets the user
        choose a key to be signed by other person.
        '''
        super(KeySignSection, self).__init__()

        self.log = logging.getLogger(__name__)

        # these are needed later when we need to get details about
        # a selected key
        self.keysPage = KeysPage()
        self.keysPage.connect('key-selection-changed',
            self.on_key_selection_changed)
        self.keysPage.connect('key-selected', self.on_key_selected)
        self.keyDetailsPage = KeyDetailsPage()


        # set up notebook container
        self.notebook = Gtk.Notebook ()
        self.notebook.append_page (self.keysPage, None)

        self.key_present_page_index = None

        self.notebook.set_show_tabs (False)

        self.pack_start(self.notebook, True, True, 0)

        # this will hold a reference to the last key selected
        self.last_selected_key = None

        # When obtaining a key is successful,
        # it will save the key data in this field
        self.received_key_data = None

        self.keyserver = None


    def construct_key_present_page(self, fingerprint):
        kpp = KeyPresentPage(fingerprint)
        vbox = Gtk.VBox ()

        # create back button
        self.backButton = Gtk.Button('Back')
        self.backButton.set_image(Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON))
        self.backButton.set_always_show_image(True)
        self.backButton.connect('clicked', self.on_button_clicked)

        # We place the button at the top, but that might not be the
        # smartest thing to do. Feel free to rearrange
        # FIXME: Consider a GtkHeaderBar for the application
        vbox.pack_start (self.backButton, False, False, 0)
        vbox.pack_start (kpp, True, True, 10)
        self.key_present_page_index = self.notebook.append_page (vbox, None)
        vbox.show_all()
        return kpp


    def destruct_key_present_page(self):
        self.notebook.remove_page(self.key_present_page_index)


    def on_key_selection_changed(self, pane, keyid):
        '''This callback is attached to the signal which is emitted
        when the user changes their selection in the list of keys
        '''
        pass


    def on_key_selected(self, pane, fingerprint):
        '''This is the callback for when the user has committed
        to a key, i.e. the user has made a selection and wants to
        advance the program.
        '''
        log.debug('User selected key %s', fingerprint)
        keydata = get_public_key_data(fingerprint)
        self.log.debug("Keyserver switched on! Serving key with fpr: %s",
                       fingerprint)
        self.setup_server(keydata, fingerprint)

        self.switch_to_key_present_page(fingerprint)


    def switch_to_key_present_page(self, fingerprint):
        '''This switches the notebook to the page which
        presents the information that is needed to securely
        transfer the keydata, i.e. the fingerprint and its barcode.
        '''
        key_present_page = self.construct_key_present_page(fingerprint)
        self.notebook.next_page()
        # This is more of a crude hack. Once the next page is presented,
        # the back button has the focus. This is not desirable because
        # you will go back when accidentally pressing space or enter.
        key_present_page.fingerprintLabel.grab_focus()
        # FIXME: we better use set_current_page, but that requires
        # knowing which page our desired widget is on.
        # FWIW: A headerbar has named pages.
        

    def on_next_button_clicked(self, button):
        '''A helper for legacy reasons to enable a next button
        
        All it does is retrieve the selection from the TreeView and
        call the signal handler for when the user committed to a key
        '''
        name, email, keyid = self.keysPage.get_items_from_selection()
        return self.on_key_selected(button, keyid)
        

    def on_button_clicked(self, button):

        page_index = self.notebook.get_current_page()

        if button == self.backButton:

            if page_index == 1:
                self.log.debug("Keyserver switched off")
                self.stop_server()
                self.destruct_key_present_page()

            self.notebook.prev_page()


    def setup_server(self, keydata, fingerprint):
        """
        Starts the key-server which serves the provided keydata and
        announces the fingerprint as TXT record using Avahi
        """
        self.log.info('Serving now')
        self.log.debug('About to call %r', Keyserver.ServeKeyThread)
        self.keyserver = Keyserver.ServeKeyThread(str(keydata), fingerprint)
        self.log.info('Starting thread %r', self.keyserver)
        self.keyserver.start()
        self.log.info('Finsihed serving')
        return False


    def stop_server(self):
        self.keyserver.shutdown()
