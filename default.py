#!/usr/bin/python
# -*- coding: utf-8 -*-

# Import PyXBMCt module.
import pyxbmct

import calendar
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from datetime import datetime

#import shutil
import re
import os
import json

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

# Enable or disable Estuary-based design explicitly
pyxbmct.skin.estuary = True

# Set plugin variables
__addon__         = xbmcaddon.Addon()
__addon_id__      = __addon__.getAddonInfo('id')
__addon_name__    = __addon__.getAddonInfo('name')
__addon_path__    = __addon__.getAddonInfo('path')
__profile__       = __addon__.getAddonInfo('profile')

__setting__       = __addon__.getSetting
__localize__      = __addon__.getLocalizedString

__list_bg__       = os.path.join(__addon_path__, 'resources', 'media', 'background.png')
__texture_nf__    = os.path.join(__addon_path__, 'resources', 'media', 'texture-nf.png')

__dialog_bg__     = os.path.join(__addon_path__, 'resources', 'skins', 'Default', 'media', 'background2.png')

__screen_width__  = 1280
__screen_height__ = 720

__dlg_width__     = 880
__dlg_height__    = 600
__dlg_offset__    = 45

# Position and size of overlay window to show image or video content (not in fullscreen mode).
# For video playback in overlay mode use exactly these values in player.xml located in resources/skins/Default/720p
__overlay__       = {
                        'x':     (__screen_width__ - __dlg_width__) // 2 ,                    # = (1280 - 880) //2       = 200
                        'y':     (__screen_height__ - __dlg_height__) // 2 + __dlg_offset__,  # = (720 - 600) // 2 + 45  = 105
                        'width':  __dlg_width__  ,                                            #                          = 880
                        'height': __dlg_height__ - __dlg_offset__                             # = 600 - 45               = 555
                    }
__fullscreen__    = {
                        'x':      0,
                        'y':      0,
                        'width':  __screen_width__,
                        'height': __screen_height__
                    }

# Localization
dlgTitle      = __localize__(33000)         # 'Dahua Cam Playback'
dlgFileType   = __localize__(33001)         # 'Dateityp:'
dlgCalMonth   = __localize__(33002)         # 'Kalendermonat:'
dlgCalYear    = __localize__(33003)         # 'Kalenderjahr:'
dlgItems      = __localize__(33004)         # 'Aufnahmen:'
dlgStartTime  = __localize__(33005)         # 'Startzeit:'
dlgEndTime    = __localize__(33006)         # 'Endzeit:'
dlgFileSize   = __localize__(33007)         # 'Dateigröße:'
dlgErrState   = __localize__(33008)         # 'Fehlerstatus:'
dlgLocStore   = __localize__(33009)         # 'SD-Karte:'
dlgHWInfo     = __localize__(33010)         # 'HW-Info:'
dlgBtnClose   = __localize__(33011)         # 'Beenden'
dlgBtnPlay    = __localize__(33012)         # 'Abspielen'
dlgBtnLive    = __localize__(33019)         # 'Live'
dlgBtnShow    = __localize__(33018)         # 'Anzeigen'
dlgBtnSave    = __localize__(33013)         # 'Sichern'
dlgStatus     = __localize__(33014)         # '{}% von {} MB belegt'
dlgError      = __localize__(33015)         # 'Ein Fehler ist aufgetreten'
dlgRecordType = __localize__(33016)         # 'Aufnahmetyp'
dlgStorage    = __localize__(33017)         # 'Speicher'
dlgHint       = __localize__(34001)         # "Zur Wiedergabe/Anzeige der Datei 'Play' drücken"
dlgSelect     = __localize__(34002)         # "Auswahl:"
dlgWeekDays   = [
                    __localize__(33020),
                    __localize__(33021),
                    __localize__(33022),
                    __localize__(33023),
                    __localize__(33024),
                    __localize__(33025),
                    __localize__(33026)
                ] # ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

if sys.version_info.major < 3:
    INFO = xbmc.LOGNOTICE
else:
    INFO = xbmc.LOGINFO
DEBUG = xbmc.LOGDEBUG


def log(message,loglevel=INFO):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)


def translatePath(path):
    if sys.version_info.major < 3:
        return xbmc.translatePath(path).decode()
    else:
        return xbmcvfs.translatePath(path)

# Settings
settings = os.path.join(translatePath(__profile__), 'settings.xml')

__cam_name__  = None         # 'DahuaCam'
__cam_ip__    = None         # '10.10.10.10'
__cam_usr__   = None         # 'admin'
__cam_pwd__   = None         # 'admin'

if not xbmcvfs.exists(settings):
    xbmc.executebuiltin('Addon.OpenSettings(' + __addon_id__ + ')')

__cam_name__  = __setting__('name')
__cam_ip__    = __setting__('ipaddress')
__cam_usr__   = __setting__('username')
__cam_pwd__   = __setting__('password')

if not __cam_name__ or not __cam_ip__:
    raise SystemExit

__tmpdir__ = os.path.join(translatePath(__profile__), 'tmp') # '/home/kodi/tmp'

# Advanced Settings
__dlddir__ = __setting__('savedir')
if not __dlddir__:
    __dlddir__ = translatePath(__profile__)
    __addon__.setSetting(id='savedir', value=__dlddir__)

__timeout__          = int(__setting__('timeout'))                 # 10
__media_timeout__    = int(__setting__('media_timeout'))           # 50
__fullscreen_mode__  = bool(__setting__('fullscreen') == 'true')   # False
__notify__           = bool(__setting__('notify') == 'true')       # True
__substream__        = int(__setting__('substream'))               # 0 # = Main Stream

# Useful Definitions
ACTION_PLAY          = 79

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK      = 92
ACTION_STOP          = 13
ACTION_BACKSPACE     = 110

SCALE = 2


class VideoPlayer(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(VideoPlayer, self).__init__(*args, **kwargs)

        self.filename = kwargs.get('filename', None)

        self._player = xbmc.Player()
        self._monitor = xbmc.Monitor()

    def onInit(self):
        if self.filename:
            self.play_video()

    def play_video(self):
        #self._player = xbmc.Player()
        self._player.play(self.filename, windowed=True)

        xbmc.sleep(200) #500

        #self._monitor = xbmc.Monitor()
        while self._player.isPlaying():
            if self._monitor.waitForAbort(1):
                log('Abort requested.')
                raise SystemExit

        self.close()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_STOP, ACTION_BACKSPACE):
            xbmc.sleep(200)

            if self._player.isPlaying():
               self._player.stop()

            self.close()


class ImageViewer(xbmcgui.WindowDialog):
    def __init__(self, x, y, width, height, filename):
        self.background = xbmcgui.ControlImage(x, y, width, height, __dialog_bg__)
        self.addControl(self.background)

        #if width/height < 16/9: # height is too big for 16/9 => fix height and adjust y position
        #    w = width
        #    h = (width * 9) // 16
        #    y = y + ((height - h) // 2)
        #else:
        #    h = height
        #    w = (height * 16) // 9
        #    x = x + ((width - w) // 2)
        #self.image = xbmcgui.ControlImage(x, y, w, h, filename)
        self.image = xbmcgui.ControlImage(x, y, width, height, filename, aspectRatio=SCALE)
        self.addControl(self.image)

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_STOP, ACTION_BACKSPACE): 
            self.close()


class DahuaCamPlayback(pyxbmct.AddonDialogWindow):
    BLUE  = '0xFF7ACAFE'
    RED   = '0xFFFF0000'
    WHITE = '0xFFFFFFFF'
    GREY  = '0xAAFFFFFF'

    MEDIA_FINDER_CREATE = 'http://{}/cgi-bin/mediaFileFind.cgi?action=factory.create'
    MEDIA_FINDER_FINDFILE = 'http://{}/cgi-bin/mediaFileFind.cgi?action=findFile&object={}' + \
        '&condition.Channel={}&condition.StartTime={}&condition.EndTime={}' + \
        '&condition.Types[0]={}' + \
        '&condition.Flags[0]=Event'
        #'&condition.Events[0]=AlarmLocal&condition.Events[1]=VideoMotion'
    #MEDIA_FINDER_FINDFILE = 'http://{}/cgi-bin/mediaFileFind.cgi?action=findFile&object={}&condition.Channel={}&condition.StartTime={}&condition.EndTime={}&condition.Types[0]={}'
        # http://<server>/cgi-bin/mediaFileFind.cgi?action=findFile
        #    &object=<objectId>
        #    &condition.Channel=<ChannelNo>
        #    &condition.StartTime=<start>
        #    &condition.EndTime=<end>
        # Optional:
        #    &condition.Dirs[0]=<dir>
        #    &condition.Types[0]=<type>
        #    &condition.Flags[0]=<flag>
        #    &condition.Events[0]=<event>
        #    &condition.VideoStream= <stream>
        # Input Arguments:
        #   objectId = objectId created from mediaFileFinder
        #   channel  = 1, ...
        #   start    = 'YYYY-MM-DD HH:MM:SS'
        #   end      = 'YYYY-MM-DD HH:MM:SS'
        # Optional Arguments:
        #   type     = ('dav', 'jpg', 'mp4')
        #   dir      = ('/mnt/dvr/sda0', '/mnt/dvr/sda1')
        #   flag     = ('Timing', 'Manual', 'Marker', 'Event', 'Mosaic', 'Cutout')
        #   event    = ('AlarmLocal', 'VideoMotion', 'VideoLoss', 'VideoBlind', 'Traffic*')
        #   stream   = ('Main', 'Extra1', 'Extra2', 'Extra3')
    MEDIA_FINDER_FINDNEXT = 'http://{}/cgi-bin/mediaFileFind.cgi?action=findNextFile&object={}&count={}'
    MEDIA_FINDER_CLOSE = 'http://{}/cgi-bin/mediaFileFind.cgi?action=close&object={}'
    MEDIA_FINDER_DESTROY = 'http://{}/cgi-bin/mediaFileFind.cgi?action=destroy&object={}'
    STORAGE_INFO = 'http://{}/cgi-bin/storageDevice.cgi?action=getDeviceAllInfo'
    SYSTEM_INFO = 'http://{}/cgi-bin/magicBox.cgi?action=getSystemInfo'
    LOADFILE = 'http://{}/cgi-bin/RPC_Loadfile{}'
    LIVESTREAM = 'rtsp://{}:{}@{}:554/cam/realmonitor?channel=1&subtype={}'

    def __init__(self, name, ip, user, password):
        # You need to call base class' constructor.
        super(DahuaCamPlayback, self).__init__(dlgTitle)
        # Set the window width, height and the grid resolution: 18 rows, 15 columns.
        self.setGeometry(__dlg_width__, __dlg_height__, 18, 15)

        self._monitor = xbmc.Monitor()
        self._player  = xbmc.Player()

        self.cams = []

        self.cam = {
            'Name':     name,
            'IPAddr':   ip,
            'User':     user,
            'Password': password
            }

        self.cams.append(self.cam)
        self.active_cam = 0
        self.session = None

        self.button_cam = []

        self.date = {
            'Day':      datetime.now().day,
            'Month':    datetime.now().month,
            'Year':     datetime.now().year
            }

        self.month_offset = 0

        self.label_info   = {}
        self.label_system = {}
        self.button_cal   = []

        self.items = []
        self.type  = 'mp4'

        self.selectedPosition = -1

        log('Addon started.')
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

        # placeControl(obj, row, column, rowspan=, columnspan=)

        label = pyxbmct.Label(dlgFileType, textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER_Y) #LEFT)
        self.placeControl(label, 1, 1, columnspan=2)

        self.radio_jpg = pyxbmct.RadioButton('jpg', noFocusTexture=__texture_nf__, textOffsetX=35)
        self.placeControl(self.radio_jpg, 1, 3, columnspan=2)
        self.connect(self.radio_jpg, self.set_type('jpg'))

        self.radio_mp4 = pyxbmct.RadioButton('mp4', noFocusTexture=__texture_nf__, textOffsetX=20)
        self.placeControl(self.radio_mp4, 1, 5, columnspan=2)
        self.connect(self.radio_mp4, self.set_type('mp4'))

        self.radio_mp4.setSelected(True)

        # Create a text label.
        label = pyxbmct.Label(dlgCalMonth, textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 3, 1, columnspan=3)

        self.button_mprev = pyxbmct.Button('<')
        self.placeControl(self.button_mprev, 4, 1)
        self.connect(self.button_mprev, self.set_month('-')) # self.month_prev)

        self.label_month = pyxbmct.Label(str(self.date['Month']), textColor=self.BLUE, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_month, 4, 2)

        self.button_mnext = pyxbmct.Button('>')
        self.placeControl(self.button_mnext, 4, 3)
        self.connect(self.button_mnext, self.set_month('+')) # self.month_next)

        # Create a text label.
        label = pyxbmct.Label(dlgCalYear, textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 3, 5, columnspan=3)

        self.button_yprev = pyxbmct.Button('<')
        self.placeControl(self.button_yprev, 4, 5)
        self.connect(self.button_yprev, self.set_year('-')) # self.year_prev)

        self.label_year = pyxbmct.Label(str(self.date['Year']), textColor=self.BLUE, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_year, 4, 6)

        self.button_ynext = pyxbmct.Button('>')
        self.placeControl(self.button_ynext, 4, 7)
        self.connect(self.button_ynext, self.set_year('+')) # self.year_next)

        # Create a text label.
        label = pyxbmct.Label(dlgItems, textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
        # Place the label on the window grid.
        self.placeControl(label, 1, 10, columnspan=3)

        label = pyxbmct.Label(dlgStartTime[:-1], font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 2, 8, columnspan=2)

        label = pyxbmct.Label(dlgRecordType[:-1], font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 2, 10, columnspan=2)

        label = pyxbmct.Label(dlgStorage[:-1], font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_RIGHT)
        self.placeControl(label, 2, 12, columnspan=2)

        self.list_bg = pyxbmct.Image(__list_bg__)
        self.placeControl(self.list_bg, 3, 8, rowspan=9, columnspan=6)
        self.list = pyxbmct.List(_space=-1, _itemTextXOffset=-3, _itemTextYOffset=-1, _alignmentY=0, buttonTexture=__texture_nf__, selectedColor=self.BLUE) #XBFONT_LEFT
        self.placeControl(self.list, 3, 8, rowspan=10, columnspan=6)
        # Connect the list to a function to display which list item is selected.
        self.connect(self.list, self.update_info)

        #self.label_total= pyxbmct.Label(str(len(self.items)), alignment=pyxbmct.ALIGN_CENTER)
        self.label_total= pyxbmct.Label(str(self.list.size()), textColor=self.BLUE, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_total, 1, 13)

        self.image_preview = pyxbmct.Image('', aspectRatio=2)
        self.placeControl(self.image_preview, 12, 8, rowspan=3, columnspan=5)
        self.image_preview.setVisible(False)

        self.label_info['txtStartTime'] = pyxbmct.Label(dlgStartTime, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['txtStartTime'], 12, 8, columnspan=2)

        self.label_info['StartTime'] = pyxbmct.Label('', font='font10', textColor=self.BLUE, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['StartTime'], 12, 10, columnspan=3)

        self.label_info['txtEndTime'] = pyxbmct.Label(dlgEndTime, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['txtEndTime'], 13, 8, columnspan=2)

        self.label_info['EndTime'] = pyxbmct.Label('', font='font10', textColor=self.BLUE, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['EndTime'], 13, 10, columnspan=3)

        self.label_info['txtFileSize'] = pyxbmct.Label(dlgFileSize, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['txtFileSize'], 14, 8, columnspan=2)

        self.label_info['FileSize'] = pyxbmct.Label('', font='font10', textColor=self.BLUE, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_info['FileSize'], 14, 10, columnspan=3)

        for col, day in enumerate(dlgWeekDays):
            label = pyxbmct.Label(day, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER)
            self.placeControl(label, 5, 1 + col)

        for row in range(6):
            for col in range(7):
                button_cal = pyxbmct.Button('')
                self.placeControl(button_cal, 6 + row, 1 + col)
                self.connect(button_cal, self.set_day(row * 7 + col))
                self.button_cal.append(button_cal)

        self.label_system['txtErrState'] = pyxbmct.Label(dlgErrState, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['txtErrState'], 12, 1, columnspan=2)

        self.label_system['ErrState'] = pyxbmct.Label('', font='font10', textColor=self.RED, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['ErrState'], 12, 3, columnspan=5)

        self.label_system['txtLocStore'] = pyxbmct.Label(dlgLocStore, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['txtLocStore'], 13, 1, columnspan=2)

        self.label_system['LocStore'] = pyxbmct.Label('', font='font10', textColor=self.BLUE, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['LocStore'], 13, 3, columnspan=5)

        self.label_system['txtHWInfo'] = pyxbmct.Label(dlgHWInfo, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['txtHWInfo'], 14, 1, columnspan=2)

        self.label_system['HWInfo'] = pyxbmct.Label('', font='font10', textColor=self.BLUE, alignment=pyxbmct.ALIGN_LEFT|pyxbmct.ALIGN_CENTER_Y)
        self.placeControl(self.label_system['HWInfo'], 14, 3, columnspan=5)

        # Create the 'Close' button.
        self.button_close = pyxbmct.Button(dlgBtnClose)
        self.placeControl(self.button_close, 16, 1, rowspan=2, columnspan=2)
        self.connect(self.button_close, self.close)

        label = pyxbmct.Label(dlgSelect, font='font10', textColor=self.GREY, alignment=pyxbmct.ALIGN_CENTER_X)
        self.placeControl(label, 15, 4, columnspan=4)

        for i in range(4):
            button_cam = pyxbmct.Button(str(i + 1), textColor=self.BLUE if i == self.active_cam else self.WHITE)
            self.placeControl(button_cam, 16, 4 + i, rowspan=2)
            self.connect(button_cam, self.set_cam(i))
            button_cam.setEnabled(True if i < len(self.cams) else False)
            self.button_cam.append(button_cam)

        self.update_system()

        tid = self.label_total.getId()

        # Create the 'Play' button.
        self.button_play = pyxbmct.Button(dlgBtnPlay)
        self.placeControl(self.button_play, 16, 8, rowspan=2, columnspan=2)
        self.button_play.setEnableCondition('Integer.IsGreater(Control.GetLabel('+ str(tid) +'),0)')
        self.connect(self.button_play, self.play)

        # Create the 'Download' button.
        self.button_dnld = pyxbmct.Button(dlgBtnSave)
        self.placeControl(self.button_dnld, 16, 10, rowspan=2, columnspan=2)
        self.button_dnld.setEnableCondition('Integer.IsGreater(Control.GetLabel('+ str(tid) +'),0)')
        self.connect(self.button_dnld, self.download)

        # Create the 'Live' button.
        self.button_live = pyxbmct.Button(dlgBtnLive)
        self.placeControl(self.button_live, 16, 12, rowspan=2, columnspan=2)
        self.connect(self.button_live, self.play_live)

        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        self.update_calendar()

        # Connect a key action to a function.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
        self.connect(ACTION_PLAY, self.play_selected)

        log('Addon initialization done.')

        return


    def add_cam(self, name, ip, user, password):
        cam = {
            'Name':     name,
            'IPAddr':   ip,
            'User':     user,
            'Password': password
            }
        self.cams.append(cam)
        self.button_cam[len(self.cams) - 1].setEnabled(True)

        return


    def set_navigation(self):
        # Navigation
        #self.autoNavigation()

        imax = len(self.button_cal) - 1
        for row in range(6):
            for col in range(7):
                i = row * 7 + col
                self.button_cal[i].setNavigation( #up, down, left, right
                    self.button_cal[i - 7] if i > 6 else self.button_mprev,
                    self.button_cal[i + 7] if i < imax - 6 else self.button_close,
                    self.button_cal[i - 1] if i > 0 else self.list,
                    self.button_cal[i + 1] if i < imax else self.list)

        self.radio_jpg.controlDown(self.button_mprev)
        self.radio_jpg.controlRight(self.radio_mp4)
        self.radio_mp4.controlDown(self.button_yprev)
        self.radio_mp4.controlLeft(self.radio_jpg)
        self.radio_mp4.controlRight(self.list)
        self.button_mprev.controlUp(self.radio_jpg)
        self.button_mprev.controlDown(self.button_cal[self.date['Day'] + self.month_offset - 1])
        self.button_mprev.controlRight(self.button_mnext)
        self.button_mnext.controlUp(self.radio_jpg)
        self.button_mnext.controlDown(self.button_cal[self.date['Day']  + self.month_offset - 1])
        self.button_mnext.controlLeft(self.button_mprev)
        self.button_mnext.controlRight(self.button_yprev)
        self.button_yprev.controlUp(self.radio_mp4)
        self.button_yprev.controlDown(self.button_cal[self.date['Day']  + self.month_offset - 1])
        self.button_yprev.controlLeft(self.button_mnext)
        self.button_yprev.controlRight(self.button_ynext)
        self.button_yprev.controlUp(self.radio_mp4)
        self.button_ynext.controlDown(self.button_cal[self.date['Day']  + self.month_offset - 1])
        self.button_ynext.controlLeft(self.button_yprev)
        self.button_ynext.controlRight(self.list)
        self.button_close.controlUp(self.button_cal[self.date['Day']  + self.month_offset - 1])
        self.button_close.controlRight(self.button_cam[0])

        for i in range(4):
            self.button_cam[i].controlUp(self.button_cal[self.date['Day']  + self.month_offset - 1])
            self.button_cam[i].controlLeft(self.button_cam[i - 1] if i > 0 else self.button_close)
            self.button_cam[i].controlRight(self.button_cam[i + 1] if i < 3 else self.button_play)

        self.button_play.controlUp(self.list)
        self.button_play.controlLeft(self.button_cam[3])
        self.button_play.controlRight(self.button_dnld)
        self.button_dnld.controlUp(self.list)
        self.button_dnld.controlLeft(self.button_play)
        self.button_dnld.controlRight(self.button_live)
        self.button_live.controlUp(self.list)
        self.button_live.controlLeft(self.button_dnld)
        self.list.controlLeft(self.radio_mp4)
        self.list.controlDown(self.button_play)

        return


    def update_system(self):
        for i in range(4):
            self.button_cam[i].setLabel(str(i + 1), textColor=self.BLUE if i == self.active_cam else self.WHITE)
            self.button_cam[i].setEnabled(True if i < len(self.cams) else False)

        try:
            (path, totalMB, used) = self.system_status()
            status = dlgStatus.format(used, totalMB)
        except:
            status = dlgError
        self.label_system['LocStore'].setLabel(status) #, font='font10', alignment=pyxbmct.ALIGN_LEFT)

        try:
            (deviceType, serialNumber, hardwareVersion) = self.system_info()
            sysInfo = '{} ({})'.format(deviceType, self.cam['Name'])
        except:
            sysInfo = dlgError
        self.label_system['HWInfo'].setLabel(sysInfo) #, font='font10', alignment=pyxbmct.ALIGN_LEFT)

        return


    def update_calendar(self, focus=True):
        currentDay   = datetime.now().day
        currentMonth = datetime.now().month
        currentYear  = datetime.now().year

        for row in range(6):
            for col in range(7):
                self.button_cal[row * 7 + col].setEnabled(False)
                self.button_cal[row * 7 + col].setVisible(False)

        self.month_offset = 0
        for row, week in enumerate(list(calendar.monthcalendar(self.date['Year'], self.date['Month']))):
            # week sequence is Mon, Tue, Wed, Thu, Fri, Sat, Sun
            for col, weekday in enumerate(week):
                if row == 0 and weekday == 0:
                    self.month_offset += 1
                # weekday is actual day of month or zero
                self.button_cal[row * 7 + col].setLabel(str(weekday), textColor=(self.BLUE if weekday == self.date['Day']  else self.WHITE))
                self.button_cal[row * 7 + col].setEnabled(weekday > 0 and not (self.date['Year']  == currentYear and self.date['Month']  == currentMonth and weekday > currentDay))
                self.button_cal[row * 7 + col].setVisible(weekday > 0)

        self.set_navigation()
        self.update_list(focus=focus)

        return


    def auth_get(self, url, *args, **kwargs):
        if not self.session:
            self.session = requests.Session()
            # Dahua cams use Digest Authentication scheme
            self.session.auth = HTTPDigestAuth(*args)

        # set default timeout value if none is specified
        if 'timeout' not in kwargs.keys():
            kwargs['timeout'] = __timeout__

        try:
            #return requests.get(url, auth=HTTPDigestAuth(*args), **kwargs)
            return self.session.get(url, **kwargs)

        #except requests.exceptions.ConnectionError as e:
        except requests.exceptions.RequestException as e:
            self.session = None
            if __notify__:
                xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'auth_get: ' + str(e), timeout*1000/2))
            log('auth_get: ' + str(e))
            return None


    def system_status(self):
        r = self.auth_get(self.STORAGE_INFO.format(self.cam['IPAddr']), self.cam['User'], self.cam['Password'], stream=True)

        if r.status_code == 200:
            data = r.text.split('\r\n')
            for line in data:
                if 'Path' in line:
                    Path = line.split('=')[1].strip()
                elif 'Name' in line:
                    Name = line.split('=')[1].strip()
                elif 'TotalBytes' in line:
                    TotalBytes = float(line.split('=')[1])
                elif 'UsedBytes' in line:
                    UsedBytes = float(line.split('=')[1])
                elif 'IsError' in line:
                    IsError = bool(line.split('=')[1].strip().lower() == 'true')
            self.label_system['ErrState'].setLabel('')
        else:
            log('Failed retrieving storage info from camera.')
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if __notify__:
                    xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'system_status: ' + str(e), timeout*1000/2))
                log('system_status: ' + str(e))
                self.label_system['ErrState'].setLabel('{}'.format(e))
            return None

        Used = round((UsedBytes / TotalBytes) * 100.0, 1)

        TotalMB = round((TotalBytes / 1024.0 / 1024.0), 1)

        return (Path, TotalMB, Used)


    def system_info(self):
        r = self.auth_get(self.SYSTEM_INFO.format(self.cam['IPAddr']), self.cam['User'], self.cam['Password'], stream=True)

        if r.status_code == 200:
            data = r.text.split('\r\n')
            for line in data:
                if 'deviceType' in line:
                    deviceType = line.split('=')[1].strip()
                elif 'serialNumber' in line:
                    serialNumber = line.split('=')[1].strip()
                elif 'hardwareVersion' in line:
                    hardwareVersion = line.split('=')[1].strip()
        else:
            log('Failed retrieving system info from camera.')
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if __notify__:
                    xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'system_info: ' + str(e), timeout*1000/2))
                log('system_info: ' + str(e))
                self.label_system['ErrState'].setLabel('{}'.format(e))
            return None

        return (deviceType, serialNumber, hardwareVersion)


    def set_cam(self, index):
        def update_cam():
            self.cam = self.cams[index]
            self.active_cam = index
            self.session = None

            self.update_system()
            self.update_list()

        return update_cam


    def set_type(self, type):
        def update_type():
            if type == 'jpg':
                if not self.radio_jpg.isSelected():
                    self.radio_jpg.setSelected(True)
                self.radio_mp4.setSelected(False)
                #self.button_play.setVisible(False)
                self.button_play.setLabel(dlgBtnShow)
                self.type = 'jpg'
                self.update_list()
            if type == 'mp4':
                if not self.radio_mp4.isSelected():
                    self.radio_mp4.setSelected(True)
                self.radio_jpg.setSelected(False)
                #self.button_play.setVisible(True)
                self.button_play.setLabel(dlgBtnPlay)
                self.type = 'mp4'
                self.update_list()

        return update_type


    def set_year(self, dir='+'):
        def update_year():
            currentYear  = datetime.now().year
            currentMonth = datetime.now().month
            if dir =='+':
                if self.date['Year'] < currentYear:
                    self.date['Year'] += 1
                    if self.date['Year'] == currentYear and self.date['Month'] > currentMonth:
                        self.date['Month'] = currentMonth
                        self.label_month.setLabel(str(self.date['Month']))
                else:
                    return
            else:
                if self.date['Year'] > 2010:
                    self.date['Year'] -= 1
                else:
                    return
            self.label_year.setLabel(str(self.date['Year']))
            self.update_calendar(focus=False)

        return update_year


    def set_month(self, dir='+'):
        def update_month():
            currentYear  = datetime.now().year
            currentMonth = datetime.now().month
            if dir == '+':
                if (self.date['Year'] == currentYear and self.date['Month'] < currentMonth) or (self.date['Year'] < currentYear):
                    self.date['Month'] = self.date['Month'] % 12 + 1
                else:
                    return
            else: # dir == '-'
                if self.date['Month'] > 1:
                    self.date['Month'] -= 1
                else:
                    self.date['Month'] = 12 if self.date['Year'] < currentYear else currentMonth
            self.date['Day'] = 1
            self.label_month.setLabel(str(self.date['Month']))
            self.update_calendar(focus=False)

        return update_month


    def set_day(self, index):
        def update_day():
            self.date['Day'] = int(self.button_cal[index].getLabel())
            self.update_calendar()

        return update_day


    def get_items(self):
        # Channel
        channel = 1

        # Set Type to either 'mp4' or 'jpg'
        # self.type = 'mp4'

        # Start and End Time:
        date  = '{}-{:02d}-{:02d}'.format(self.date['Year'] , self.date['Month'] , self.date['Day'] )
        start_date = date + ' 00:00:01'
        end_date   = date + ' 23:59:59'

        # Objects count, may be 100 max
        count = 100

        items = []
        numitems = 0

        # Create a mediaFileFinder
        r = self.auth_get(self.MEDIA_FINDER_CREATE.format(self.cam['IPAddr']), self.cam['User'], self.cam['Password'], stream=True)
        if r.status_code == 200:
            data = r.text.split('\r\n')
            objectId = data[0].split('=')[1]

            # Start findFile
            r = self.auth_get(self.MEDIA_FINDER_FINDFILE.format(self.cam['IPAddr'],
                    objectId, channel,start_date, end_date, self.type),
                    self.cam['User'], self.cam['Password'], stream=True, timeout=__media_timeout__)
            success = (r.text == 'OK\r\n')

            # findNextFile
            while success:
                r = self.auth_get(self.MEDIA_FINDER_FINDNEXT.format(self.cam['IPAddr'],
                        objectId, count), self.cam['User'], self.cam['Password'], stream=True, timeout=__media_timeout__)
                if r.status_code == 200:
                    # Fields in Response:
                    #   found                  Count of found file, found is 0 if no file is found.
                    #   items[i].Channel       Channel, equals to API findFile input condition.Channel -1
                    #   items[i].StartTime     Start Time (YYYY-MM-DD HH:MM:SS)
                    #   items[i].EndTime       End time (YYYY-MM-DD HH:MM:SS)
                    #   items[i].Type          File type ('dav', 'jpg', 'mp4')
                    #   items[i].Flags[0]      Flag ('Timing', 'Manual', 'Marker', 'Event', 'Mosaic', 'Cutout')
                    #   items[i].Events[0]     Event type ('AlarmLocal', 'VideoMotion', 'VideoLoss', 'VideoBlind', 'Traffic*')
                    #   items[i].FilePath      File path
                    #   items[i].Length        File length
                    #   items[i].Duration      Duration time
                    data = r.text.split('\r\n')
                    if 'found=' in data[0]:
                        numitems = int(data[0].split('=')[1])
                        self.label_system['ErrState'].setLabel('')
                    else:
                        if 'error' in data[0]:
                        # e.g. data[0] = {"error":{"code":287637505,"message":"Invalid session in request data!"},"result":false}
                            json_data = json.loads(data[0])
                            log('Error retrieving item list: {}'.format(json_data['error']['message']))
                            self.label_system['ErrState'].setLabel('{}'.format(json_data['error']['message']))
                        continue

                    if numitems == 0:
                        break

                    # Ignore first and last line for calculation of item length
                    numkeys = int((len(data) - 2) / numitems) # numkeys = int(len(data[1:-1]) / numitems)

                    item = {}
                    for line in data[1:-1]:
                        item.update({k: v for k,v in re.findall(r'items\[\d*\]\.(\S*)=(.*)', line)})
                        if len(item) == numkeys:
                            items.append(item)
                            item = {}
                else:
                    log('Failed retrieving item list.')
                    try:
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        if __notify__:
                            xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'get_items: ' + str(e), timeout*1000/2))
                        log('get_items:' + str(e))
                        self.label_system['ErrState'].setLabel('{}'.format(e))
                    break

                xbmc.sleep(1000)

            if not success:
                log('No items.')

            # Close and destroy the mediaFileFinder
            r = self.auth_get(self.MEDIA_FINDER_CLOSE.format(self.cam['IPAddr'],
                    objectId), self.cam['User'], self.cam['Password'], stream=True)
            r = self.auth_get(self.MEDIA_FINDER_DESTROY.format(self.cam['IPAddr'],
                    objectId), self.cam['User'], self.cam['Password'], stream=True)

        return items


    def update_list(self, selected=0, focus=True):
        self.list.reset()
        self.label_total.setLabel(str(self.list.size()))

        self.update_info()

        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

        try:
            self.items = self.get_items()
        except:
            self.items = []
            self.label_system['ErrState'].setLabel(dlgError)

        for item in self.items:
            try:
                if 'StartTime' in item:
                    li = '{}'.format(item['StartTime'].split()[1])
                elif self.type == 'jpg':
                    li = '{}'.format(item['EndTime'].split()[1])
                else:
                    continue

                if 'Flags[0]' in item:
                   li = li + ' {}'.format(item['Flags[0]'])
                #elif 'Events[0]' in item:
                #   li = li + ' Event'

                if 'Events[0]' in item:
                   li = li + ': {}'.format(item['Events[0]'])

                #if 'Events[0]' in item:
                #    li = '{} {}: {}'.format(item['StartTime'].split()[1], item['Flags[0]'], item['Events[0]'])
                #else:
                #    li = '{} {}'.format(item['StartTime'].split()[1], item['Flags[0]'])

                li = '{:31} {}'.format(li[:31], 'SD' if item['FilePath'][:4] == '/mnt' else 'FTP' if item['FilePath'][:4] == 'ftp:' else 'SAN') 
            except Exception as e:
                log('Exception {}: {} in item: {}'.format(type(e).__name__, e, item))
                continue
            self.list.addItem(li)

        self.label_total.setLabel(str(self.list.size()))

        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        if self.list.size() > 0:
            self.list.selectItem(selected)
            if focus:
                self.setFocus(self.list)
            self.update_info()
        elif focus:
            self.setFocus(self.button_cal[self.date['Day'] + self.month_offset - 1])

        return


    def update_info(self):
        if self.type == 'jpg':
            for key in self.label_info:
                self.label_info[key].setVisible(False)
            self.image_preview.setVisible(True)
        else:
            for key in self.label_info:
                self.label_info[key].setVisible(True)
            self.image_preview.setVisible(False)

        if self.list.size() > 0:
            if self.selectedPosition != self.list.getSelectedPosition():
                if self.selectedPosition != -1:
                    self.list.getListItem(self.selectedPosition).select(False)

                # Set selected list item select (highlighted) state to True
                self.selectedPosition = self.list.getSelectedPosition()
                self.list.getListItem(self.selectedPosition).select(True)

                item = self.items[self.selectedPosition]

                if self.type == 'jpg':
                    # show preview of image in info section
                    uri = self.download(item=item, destdir=__tmpdir__)
                    self.image_preview.setImage(uri or '', False)
                    xbmc.sleep(500)
                    xbmcvfs.delete(uri)
                else: #self.type == 'mp4':
                    # show file info
                    self.label_info['StartTime'].setLabel(item['StartTime']) #.split()[1])
                    self.label_info['EndTime'].setLabel(item['EndTime']) #.split()[1])
                    self.label_info['FileSize'].setLabel('{} (KB)'.format(int(round(int(item['Length'])/1024.0, 0))))
        else:
            self.selectedPosition = -1

            if self.type == 'jpg':
                self.image_preview.setImage('', False)
            else:
                self.label_info['StartTime'].setLabel('')
                self.label_info['EndTime'].setLabel('')
                self.label_info['FileSize'].setLabel('')

        return


    def play_live(self):
        self.play(live=True)


    def play_selected(self):
        # on ACTION_PLAY
        if self.list.getSelectedPosition() != -1:
            self.play(self.items[self.list.getSelectedPosition()])


    def play(self, item=None, live=False):
        if not live:
            if not item:
                if self.selectedPosition == -1:
                    return

                item = self.items[self.selectedPosition]

            #uri = 'http://{}/cgi-bin/playBack.cgi?action=getStream&channel=1&subtype=0&startTime={}&endTime={}'.format(self.cam['IPAddr'], item['StartTime'], item['EndTime'])
            #uri = 'rtsp://{}/{}'.format(self.cam['IPAddr'], item['FilePath'])

            uri = self.download(item=item, destdir=__tmpdir__)

            if self.type == 'jpg':
                if __fullscreen_mode__:
                    viewer = ImageViewer(*__fullscreen__.values(), uri)
                else:
                    viewer = ImageViewer(*__overlay__.values(), uri)

                viewer.doModal()
                del viewer
        #end of if not live

        if self.type == 'mp4' or live:
            if live:
                self.subtype = __substream__
                uri = self.LIVESTREAM.format(self.cam['User'], self.cam['Password'], self.cam['IPAddr'], self.subtype)
            else:
                uri = self.download(item=item, destdir=__tmpdir__)

            if __fullscreen_mode__:
                self._player.play(uri)
                xbmc.sleep(500)

                self.close() # need to close the main dialog otherwise it will be in front of video plabyback

                while self._player.isPlaying():
                    if self._monitor.waitForAbort(1):
                        log('Abort requested.')
                        raise SystemExit

                self.doModal() # once video has ended, re-open the main dialog
            else:
                player = VideoPlayer('player.xml', __addon_path__, filename=uri)

                player.doModal()
                del player

        if xbmcvfs.exists(uri):
            xbmcvfs.delete(uri)

        return


    def download(self, item=None, destdir=None, name=None):
        if not item:
            if self.selectedPosition == -1:
                return

            item = self.items[self.selectedPosition]

        if not destdir:
            #destdir = translatePath(__profile__)
            destdir = __dlddir__

        if not xbmcvfs.exists(destdir):
            xbmcvfs.mkdir(destdir)

        path = item['FilePath']
        cmd = self.LOADFILE.format(self.cam['IPAddr'], path)

        # Local FilePath:
        # item['FilePath'] = e.g. /mnt/sd/2019-11-11/001/dav/21/21.40.47-21.41.33[M][0@0][0].mp4
        # item['FilePath'] = e.g. /mnt/sd/2020-10-11/001/jpg/21/09/14[M][0@0][0].jpg
        # FTP FilePath:
        # item['FilePath'] = e.g. ftp://192.168.178.11/dahua/DOOR_CAM/2025-11-18/001/jpg/16/48/50[M][0@0][0].jpg
        # item['FilePath'] = e.g. ftp://192.168.178.11/dahua/DOOR_CAM/2025-11-18/001/dav/16/16.50.08-16.50.58[M][0@0][0].mp4
        # NAS FIlepath should be nfs://

        if not name:
            name = '{}_{}_{}.{}'.format(self.cam['Name'], item['StartTime'].split()[0], item['StartTime'].split()[1].replace(':', '.'), path[-3:])

        try: # python 2
            destfile = os.path.join(destdir, name.decode())
        except: # python 3
            destfile = os.path.join(destdir, name)

        #log('Saving file {} as {}'.format(path, destfile))

        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

        r = self.auth_get(cmd, self.cam['User'], self.cam['Password'], stream=True)
        if r.status_code == 200:
            #r.raw.decode_content = True
            with open(destfile, 'wb') as out:
                try:
                    out.write(r.content)
                    #shutil.copyfileobj(r.raw, out)
                except Exception as e:
                    if __notify__:
                        xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'download: ' + str(e), timeout*1000/2))
                    log('download: ' + str(e))

            self.label_system['ErrState'].setLabel('')
        else:
            log('Failed downloading: {}'.format(destfile))
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if __notify__:
                    xbmc.executebuiltin('Notification({}, {}, {})'.format(__addon_name__, 'download: ' + str(e), timeout*1000/2))
                log('download: ' + str(e))
                self.label_system['ErrState'].setLabel('{}'.format(e))

        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        return destfile if xbmcvfs.exists(destfile) else None


# Create a window instance.
window = DahuaCamPlayback(__cam_name__, __cam_ip__, __cam_usr__, __cam_pwd__)
for i in range(2, 5):
    cam_name  = None or __setting__('name' + str(i))
    cam_ip    = None or __setting__('ipaddress' + str(i))
    cam_usr   = __setting__('username' + str(i))
    cam_pwd   = __setting__('password' + str(i))
    if cam_name and cam_ip:
        window.add_cam(cam_name, cam_ip, cam_usr, cam_pwd)

# Show the created window.
window.doModal()
# Delete the window instance when it is no longer used.
del window
