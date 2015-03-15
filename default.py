#
#  Kodi PBX Addon
#      Fron-end (Kodi) side
#      This script is the User Interface
#
#
#  Copyright (C) 2012 hmronline@gmail.com 
#  http://kodi-pbx-addon.googlecode.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

# Script constants
__addon__       = "Kodi PBX Addon"
__addon_id__    = "script.kodi-pbx-addon"
__author__      = "hmronline"
__url__         = "http://code.google.com/p/kodi-pbx-addon/"
__version__     = "1.14.0"

# Modules
import sys, os
import xbmc, xbmcaddon, xbmcgui
import re, traceback
import urllib, urlparse, urllib2, xml.dom.minidom
import time

DATEFORMAT = xbmc.getRegion('dateshort')
TIMEFORMAT = xbmc.getRegion('meridiem')

xbmc.log("[%s]: Version %s Dateformat '%s', Timeformat '%s'\n" % (__addon__,__version__, DATEFORMAT, TIMEFORMAT))

# Get environment OS
__os__          = os.environ.get( "OS", "win32" )
xbmc.log("[%s]: XBMC for %s\n" % (__addon__,__os__))

__language__    = xbmcaddon.Addon(__addon_id__).getLocalizedString
CWD             = xbmcaddon.Addon(__addon_id__).getAddonInfo('path')
RESOURCE_PATH   = os.path.join(CWD, "resources" )

sys.path.append(os.path.join(RESOURCE_PATH,'lib'))
from Asterisk.Manager import Manager
import Asterisk.Manager, Asterisk.Util

ACTION_EXIT_SCRIPT  = (9,10,247,275,61467,216,257,61448,)

#############################################################################################################
def log(msg):
    try:
        xbmc.log("[%s]: %s\n" % (__addon__,str(msg)))
    except:
        pass

def date_format(stamp):
    date_time = time.localtime(stamp)
    localdate = time.strftime(DATEFORMAT, date_time)
    return localdate

def time_format(stamp):
    date_time = time.localtime(stamp)

    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M%p', date_time)
    else:
        localtime = time.strftime('%H:%M:%S', date_time)
    return localtime

def duration_format(stamp):
    date_time = time.gmtime(stamp)

    duration = time.strftime('%H:%M:%S', date_time)
    dur = ""
    sp = 1
    for n in range(0, len(duration)):
        char = duration[n]
        if (char != "0" and char != ":"):
            sp = 0
        
        if (sp == 1):
            dur = dur + " "
        else:
            dur = dur + char

    return dur

#############################################################################################################
class MainGUI(xbmcgui.WindowXML):

    def __init__(self,*args,**kwargs):
        log("__init__()")
        xbmcgui.WindowXML.__init__(self)

    #####################################################################################################
    def onInit(self):
        log("> onInit()")
        settings = xbmcaddon.Addon(__addon_id__)
        DEBUG = settings.getSetting("xbmc_debug")
        del settings
        if (DEBUG == "true"):
            self.DEBUG = True
        else:
            self.DEBUG = False
        dialog = xbmcgui.DialogProgress()
        # Starting...
        dialog.create(__addon__,__language__(30061))
        try:
            # Skin Setup...
            dialog.update(25,__language__(30062))
            self.skinSetup()
            # Fetching Asterisk Info...
            dialog.update(50,__language__(30063))
            self.getInfo()
            # Displaying Asterisk Info...
            dialog.update(75,__language__(30064))
            self.showInfo()
            # Done...
            dialog.update(100,__language__(30065))
        except:
            xbmc_notification = unicode(str(sys.exc_info()[1]))
            xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','kodi-pbx-addon.png'))
            log(">> Notification: " + xbmc_notification)
            xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")
        dialog.close()
        del dialog
        log(">> Done.")

    #####################################################################################################
    def skinSetup(self):
        log("> skinSetup()")
        if (__os__ == 'xbox'): xbmcgui.lock()
        self.getControl(110).setLabel(__language__(30101))  # CDR toggle button
        self.getControl(111).setLabel(__language__(30102))  # VM toggle button
        self.getControl(109).setLabel(__language__(30107))  # Refresh button
        self.getControl(108).setLabel(__language__(30108))  # Dialer button
        self.getControl(112).setLabel(__language__(30103))  # Settings button
        self.getControl(140).setLabel(__language__(30130))  # CDR - start
        self.getControl(141).setLabel(__language__(30116))  # CDR - channel
        self.getControl(142).setLabel(__language__(30112))  # CDR - src
        self.getControl(143).setLabel(__language__(30115))  # CDR - clid
        self.getControl(144).setLabel(__language__(30113))  # CDR - dst
        self.getControl(145).setLabel(__language__(30125))  # CDR - disposition
        self.getControl(146).setLabel(__language__(30123))  # CDR - duration
        self.getControl(161).setLabel(__language__(30159))  # VM - origtime
        self.getControl(162).setLabel(__language__(30157))  # VM - callerid
        self.getControl(163).setLabel(__language__(30155))  # VM - priority
        self.getControl(164).setLabel(__language__(30151))  # VM - origmailbox
        self.getControl(165).setLabel(__language__(30162))  # VM - duration
        if (__os__ == 'xbox'): xbmcgui.unlock()

    #####################################################################################################
    def getInfo(self):
        log("> getInfo()")
        settings = xbmcaddon.Addon(__addon_id__)
        manager_host_port = settings.getSetting("asterisk_manager_host"),int(settings.getSetting("asterisk_manager_port"))
        manager_user = settings.getSetting("asterisk_manager_user")
        manager_pass = settings.getSetting("asterisk_manager_pass")
        asterisk_vm_mailbox = settings.getSetting("asterisk_vm_mailbox")
        asterisk_vm_context = settings.getSetting("asterisk_vm_context")
        str_url = settings.getSetting("asterisk_info_url")
        del settings
        pbx = Manager(manager_host_port,manager_user,manager_pass)
        asterisk_version = str(pbx.Command("core show version")[1])
        asterisk_series = asterisk_version[9:12]
        del pbx
        log(">> Asterisk " + asterisk_series)
        if (DEBUG): log(">> " + asterisk_version)
        str_url = str_url +"?vm&cdr&mailbox="+ asterisk_vm_mailbox
        str_url = str_url +"&vmcontext="+ asterisk_vm_context
        if (self.DEBUG):
            log(">> " + str_url)
        f = urllib.urlopen(str_url)
        self.dom = xml.dom.minidom.parse(f)
        if (self.DEBUG):
            log(self.dom.toxml())
        f.close()
        del f

    #####################################################################################################
    def showInfo(self):
        log("> showInfo()")
        backend_version = "unknown"
        backend_error_msg = ""
        for node in self.dom.getElementsByTagName('version'):
            backend_version = node.firstChild.data
        options = {"cdr":120,"vm":121}
        if (__os__ == 'xbox'): xbmcgui.lock()
        for option in options.keys():
            self.getControl(options[option]).reset()
            # Parse CDR/VM XML content
            # Error Messages
            for node in self.dom.getElementsByTagName(option +'_error'):
                for childNode in node.childNodes:
                    if (childNode.nodeName != "#text"):
                        if (childNode.firstChild):
                            backend_error_msg = childNode.firstChild.data
            # CDR/VM content
            for node in self.dom.getElementsByTagName(option):
                listitem = xbmcgui.ListItem()
                for childNode in node.childNodes:
                    if (childNode.nodeName != "#text"):
                        if (childNode.firstChild):
                            prop = childNode.firstChild.data
                            if (childNode.nodeName == "start"):
                                prop = date_format(float(prop)) + " " +  time_format(float(prop))
                            if (childNode.nodeName == "duration"):
                                prop = duration_format(float(prop))
                            if (childNode.nodeName == "origtime"):
                                prop = date_format(float(prop)) + " " +  time_format(float(prop))
                            log(">> childNode.nodeName " + childNode.nodeName)
                            listitem.setProperty(childNode.nodeName, prop)
                        else:
                            listitem.setProperty(childNode.nodeName,"")
                self.getControl(options[option]).addItem(listitem)
                del listitem
        if (__os__ == 'xbox'): xbmcgui.unlock()
        del self.dom
        if (backend_error_msg != ""):
            log(">> Received error from Back-end!: " + backend_error_msg)
            xbmc_notification = unicode("Back-end says:" + backend_error_msg)
            xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','kodi-pbx-addon.png'))
            log(">> Notification: " + xbmc_notification)
            xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")
        if (backend_version != __version__):
            log(">> Version mismatch!: Frontend is " + __version__ + " while Backend is " + backend_version)
            xbmc_notification = unicode("You have to update the backend!")
            xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','kodi-pbx-addon.png'))
            log(">> Notification: " + xbmc_notification)
            xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")

    #####################################################################################################
    def onAction(self,action):
        if (self.DEBUG):
            log("> onAction(" + str(action.getButtonCode()) + "," + str(action.getId()) + ")")
        try:
            if (action and (action.getButtonCode() in ACTION_EXIT_SCRIPT or action.getId() in ACTION_EXIT_SCRIPT)):
                self.close()
                del self.vm_player
        except:
            log(">> Seems Kodi PlayerControls were closed...")

    def onClick(self,controlId):
        if (self.DEBUG):
            log("> onClick(" + str(controlId) + ")")
        # Initiate outgoing call
        if (controlId == 120):
            number_to_call = self.getControl(120).getSelectedItem().getProperty("src")
            if (number_to_call != ""):
                dialog = xbmcgui.Dialog()
                if (dialog.yesno(__addon__,__language__(30104) + " '" + number_to_call + "'?")):
                    self.make_outgoing_call(number_to_call)
                del dialog
        # Play Voice Mail
        elif (controlId == 121):
            recindex = self.getControl(121).getSelectedItem().getProperty("recindex")
            if (recindex != ""):
                dialog = xbmcgui.Dialog()
                if (dialog.yesno(__addon__,__language__(30105))):
                    self.play_voice_mail(recindex)
                else:
                    # Callback
                    del dialog
                    number_to_call = self.getControl(121).getSelectedItem().getProperty("callerid")
                    number_to_call = number_to_call.split('<')[0]
                    if (number_to_call != ""):
                        dialog = xbmcgui.Dialog()
                        if (dialog.yesno(__addon__,__language__(30104) + " '" + number_to_call + "'?")):
                            self.make_outgoing_call(number_to_call)
                del dialog
        # Refresh
        elif (controlId == 109):
            self.onInit()
        # Dialer
        elif (controlId == 108):
            dialer = xbmcgui.Dialog()
            number_to_call = dialer.numeric(0,__language__(30108))
            if (number_to_call != ""):
                self.make_outgoing_call(number_to_call)
            del dialer
        # Settings
        elif (controlId == 112):
            settings = xbmcaddon.Addon(__addon_id__)
            settings.openSettings()
            del settings
            self.onInit()

    def onFocus(self,controlId):
        pass

    #####################################################################################################
    def make_outgoing_call(self,number_to_call):
        log("> make_outgoing_call()")
        settings = xbmcaddon.Addon(__addon_id__)
        manager_host_port = settings.getSetting("asterisk_manager_host"),int(settings.getSetting("asterisk_manager_port"))
        pbx = Manager(manager_host_port,settings.getSetting("asterisk_manager_user"),settings.getSetting("asterisk_manager_pass"))
        pbx.Originate(settings.getSetting("asterisk_outbound_extension"),settings.getSetting("asterisk_outbound_context"),number_to_call,1)
        del pbx
        del settings
        log(">> Done.")

    #####################################################################################################
    def play_voice_mail(self,recindex):
        log("> play_voice_mail()")
        settings = xbmcaddon.Addon(__addon_id__)
        audio_format = ["wav","gsm","mp3","WAV"]
        asterisk_vm_format = audio_format[int(settings.getSetting("asterisk_vm_format"))]
        self.url_vm = settings.getSetting("asterisk_info_url") +"?recindex="+ recindex
        self.url_vm = self.url_vm +"&mailbox="+ settings.getSetting("asterisk_vm_mailbox")
        self.url_vm = self.url_vm +"&vmcontext="+ settings.getSetting("asterisk_vm_context")
        self.url_vm = self.url_vm +"&format="+ asterisk_vm_format
        del settings
        self.vm_player = VoiceMailPlayer(xbmc.PLAYER_CORE_DVDPLAYER,function=self.voice_mail_ended)
        self.xbmc_player = xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER)
        listitem = xbmcgui.ListItem('VoiceMail')
        listitem.setInfo(type='music',infoLabels={'title':recindex,'genre':audio_format,'artist':'Voice Mail','album':'Kodi PBX Addon'})
        self.xbmc_player.play(self.url_vm, listitem)
        del listitem
        del self.xbmc_player
        xbmc.executebuiltin("XBMC.ActivateWindow(playercontrols)")

    #####################################################################################################
    def voice_mail_ended(self):
        log("> voice_mail_ended()")
        del self.vm_player
        settings = xbmcaddon.Addon(__addon_id__)
        asterisk_mwi_clean = False
        if (settings.getSetting("asterisk_mwi_clean") == "true"):
            asterisk_mwi_clean = True
        del settings
        if (self.url_vm != ""):
            dialog = xbmcgui.Dialog()
            if (dialog.yesno(__addon__,__language__(30106))):
                # Delete Voice Mail
                self.delete_voice_mail()
                self.onInit()
            elif (asterisk_mwi_clean):
                # Store Voice Mail (Updates MWI)
                self.store_voice_mail()
                self.onInit()
            del dialog
            self.url_vm = ""

    #####################################################################################################
    def store_voice_mail(self):
        log("> store_voice_mail()")
        if (self.url_vm != ""):
            self.url_vm = self.url_vm +"&store"
            if (self.DEBUG):
                log(">> " + self.url_vm)
            f = urllib.urlopen(self.url_vm)
            f.close()
            del f

    #####################################################################################################
    def delete_voice_mail(self):
        log("> delete_voice_mail()")
        if (self.url_vm != ""):
            self.url_vm = self.url_vm +"&delete"
            if (self.DEBUG):
                log(">> " + self.url_vm)
            f = urllib.urlopen(self.url_vm)
            f.close()
            del f
            

#############################################################################################################
class VoiceMailPlayer(xbmc.Player):
    def __init__(self,*args,**kwargs):
        xbmc.Player.__init__(self)
        self.function = kwargs["function"]

    #####################################################################################################
    def onPlayBackStopped(self):
        self.function()

    #####################################################################################################
    def onPlayBackEnded(self):
        self.function()


#############################################################################################################
class FirstTimeGUI(xbmcgui.Window):

    def __init__(self):
        log("__init__()")
        settings = xbmcaddon.Addon(__addon_id__)
        DEBUG = settings.getSetting("xbmc_debug")
        del settings
        if (DEBUG == "true"):
            self.DEBUG = True
        else:
            self.DEBUG = False
        dialog = xbmcgui.ControlTextBox(1,1,600,600,"font12","0xFFFFFFFF")
        msg = ""
        for i in range(1,10):
            msg = msg + __language__(30170 + i) + "\n"
        self.addControl(dialog)
        dialog.setText(msg)
        log(">> Done.")

    #####################################################################################################
    def onAction(self,action):
        if (self.DEBUG):
            log("> onAction()")
        settings = xbmcaddon.Addon(__addon_id__)
        settings.openSettings()
        del settings
        self.close()



#################################################################################################################
 # Starts here
#################################################################################################################

try:
    log("PATH: "+ CWD)
    log("Launching GUI...")
    settings = xbmcaddon.Addon(__addon_id__)
    first_time_use = settings.getSetting("first_time_use")
    settings.setSetting("first_time_use","false")
    DEBUG = settings.getSetting("xbmc_debug")
    del settings
    if (first_time_use == "true"):
        ui = FirstTimeGUI()
    else:
        ui = MainGUI("main_gui.xml",CWD,"Default")
    ui.doModal()
except:
    xbmc_notification = unicode(str(sys.exc_info()[1]))
    xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','kodi-pbx-addon.png'))
    log(">> Notification: " + xbmc_notification)
    xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")
try:
    del ui
    log("EXIT!")
    sys.modules.clear()
except:
    pass
