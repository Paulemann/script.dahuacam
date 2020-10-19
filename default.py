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

import xbmc
import xbmcaddon
import xbmcvfs


# Enable or disable Estuary-based design explicitly
pyxbmct.skin.estuary = True

# Set plugin variables
__addon__        = xbmcaddon.Addon()
__addon_id__     = __addon__.getAddonInfo('id')
__addon_path__   = __addon__.getAddonInfo('path')
__profile__      = __addon__.getAddonInfo('profile')

__setting__      = __addon__.getSetting
__localize__     = __addon__.getLocalizedString

# Localization
dlgTitle      = __localize__(33000)         # 'Dahua Cam Playback'
dlgFileType   = __localize__(33001)         # 'Dateityp:'
dlgCalMonth   = __localize__(33002)         # 'Kalendermonat:'
dlgCalYear    = __localize__(33003)         # 'Kalenderjahr:'
dlgItems      = __localize__(33004)         # 'Aufnahmen:'
dlgStartTime  = __localize__(33005)         # 'Startzeit:'
dlgEndTime    = __localize__(33006)         # 'Endzeit:'
dlgFileSize   = __localize__(33007)         # 'Dateigröße:'
dlgLocMemory  = __localize__(33008)         # 'Status:'
dlgIPAddress  = __localize__(33009)         # 'IP-Adresse:'
dlgBtnClose   = __localize__(33010)         # 'Beenden'
dlgBtnPlay    = __localize__(33011)         # 'Abspielen'
dlgBtnSave    = __localize__(33012)         # 'Sichern'
dlgStatus     = __localize__(33013)         # '{}% von {} MB belegt'
dlgError      = __localize__(33014)         # 'Ein Fehler is aufgetreten'
dlgWeekDays   = [
                    __localize__(33020),
                    __localize__(33021),
                    __localize__(33022),
                    __localize__(33023),
                    __localize__(33024),
                    __localize__(33025),
                    __localize__(33026)
                ] # ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

# Settings
settings = os.path.join(xbmc.translatePath(__profile__).decode('utf-8'), 'settings.xml')

cam_name  = None         # 'DahuaCam'
cam_ip    = None         # '10.10.10.10'
cam_usr   = None         # 'admin'
cam_pwd   = None         # 'admin'

if not xbmcvfs.exists(settings):
    xbmc.executebuiltin('Addon.OpenSettings(' + __addon_id__ + ')')

cam_name  = __setting__('name')             # 'DoorCam'
cam_ip    = __setting__('ipaddress')        # '10.10.30.6'
cam_usr   = __setting__('username')         # 'admin'
cam_pwd   = __setting__('password')         # 'admin'

if not cam_name or not cam_ip:
    raise SystemExit

tmpdir    = os.path.join(xbmc.translatePath(__profile__).decode('utf-8'), 'tmp') # '/home/kodi/tmp'


def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)


class DahuaCamPlayback(pyxbmct.AddonDialogWindow):

    def __init__(self, name, ip, user, password):
        # You need to call base class' constructor.
        super(DahuaCamPlayback, self).__init__(dlgTitle)
        # Set the window width, height and the grid resolution: 20 rows, 15 columns.
        #self.setGeometry(640, 480, 20, 15)
        self.setGeometry(880, 600, 18, 15)

        self._monitor = xbmc.Monitor()
        self._player  = xbmc.Player()

        self.camName  = name
        self.camIP    = ip
        self.camUsr   = user
        self.camPwd   = password

        self.month = datetime.now().month
        self.year  = datetime.now().year
        self.day   = datetime.now().day

        self.month_offset = 0

        self.label_info = {}
        self.button_cal = []

        self.items = []
        self.type  = 'mp4'

        log('Addon started.')
        # placeControl(obj, row, column, rowspan=, columnspan=)

        label = pyxbmct.Label(dlgFileType, alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(label, 1, 1, columnspan=2)

        self.radio_jpg = pyxbmct.RadioButton('jpg')
        self.placeControl(self.radio_jpg, 1, 4, columnspan=2)
        self.connect(self.radio_jpg, self.update_radio('jpg'))

        self.radio_mp4 = pyxbmct.RadioButton('mp4')
        self.placeControl(self.radio_mp4, 1, 6, columnspan=2)
        self.connect(self.radio_mp4, self.update_radio('mp4'))

        self.radio_mp4.setSelected(True)

        # Create a text label.
        label = pyxbmct.Label(dlgCalMonth, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 3, 1, columnspan=3)

        self.button_mprev = pyxbmct.Button('<')
        self.placeControl(self.button_mprev, 4, 1)
        self.connect(self.button_mprev, self.month_prev)

        self.label_month = pyxbmct.Label(str(self.month), alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_month, 4, 2)

        self.button_mnext = pyxbmct.Button('>')
        self.placeControl(self.button_mnext, 4, 3)
        self.connect(self.button_mnext, self.month_next)

        # Create a text label.
        label = pyxbmct.Label(dlgCalYear, alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(label, 3, 5, columnspan=3)

        self.button_yprev = pyxbmct.Button('<')
        self.placeControl(self.button_yprev, 4, 5)
        self.connect(self.button_yprev, self.year_prev)

        self.label_year = pyxbmct.Label(str(self.year), alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_year, 4, 6)

        self.button_ynext = pyxbmct.Button('>')
        self.placeControl(self.button_ynext, 4, 7)
        self.connect(self.button_ynext, self.year_next)

        # Create a text label.
        label = pyxbmct.Label(dlgItems, alignment=pyxbmct.ALIGN_CENTER)
        # Place the label on the window grid.
        self.placeControl(label, 1, 10, columnspan=3)

        self.list = pyxbmct.List(_space=-1, _itemTextXOffset=-3, _alignmentY=0) #XBFONT_LEFT
        self.placeControl(self.list, 2, 9, rowspan=10, columnspan=5)
        # Connect the list to a function to display which list item is selected.
        self.connect(self.list, self.update_info)

        self.label_total= pyxbmct.Label(str(len(self.items)), alignment=pyxbmct.ALIGN_CENTER)
        self.placeControl(self.label_total, 1, 13)

        self.image_preview = pyxbmct.Image('', aspectRatio=2)
        self.placeControl(self.image_preview, 12, 9, rowspan=3, columnspan=5)
        self.image_preview.setVisible(False)

        self.label_info['Start'] = pyxbmct.Label(dlgStartTime, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['Start'], 12, 9, columnspan=2)

        self.label_info['StartTime'] = pyxbmct.Label('', font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['StartTime'], 12, 11, columnspan=3)

        self.label_info['End'] = pyxbmct.Label(dlgEndTime, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['End'], 13, 9, columnspan=2)

        self.label_info['EndTime'] = pyxbmct.Label('', font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['EndTime'], 13, 11, columnspan=3)

        self.label_info['File'] = pyxbmct.Label(dlgFileSize, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['File'], 14, 9, columnspan=2)

        self.label_info['FileSize'] = pyxbmct.Label('', font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_info['FileSize'], 14, 11, columnspan=3)

        for col, day in enumerate(dlgWeekDays):
            label = pyxbmct.Label(day, alignment=pyxbmct.ALIGN_CENTER)
            self.placeControl(label, 6, 1 + col)

        for row in range(6):
            for col in range(7):
                button_cal = pyxbmct.Button('')
                self.placeControl(button_cal, 7 + row, 1 + col)
                self.connect(button_cal, self.update_calday(row * 7 + col))
                self.button_cal.append(button_cal)

        label = pyxbmct.Label(dlgLocMemory, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(label, 13, 1, columnspan=2)

        try:
            (path, totalMB, used) = self.status()
            status = dlgStatus.format(used, totalMB)
        except:
            status = dlgError
        self.label_status = pyxbmct.Label(status, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_status, 13, 3, columnspan=5)

        label = pyxbmct.Label(dlgIPAddress, font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(label, 14, 1, columnspan=2)

        self.label_ip = pyxbmct.Label('{} ({})'.format(self.camIP, self.camName), font='font10', alignment=pyxbmct.ALIGN_LEFT)
        self.placeControl(self.label_ip, 14, 3, columnspan=5)

        # Create the 'Close' button.
        self.button_close = pyxbmct.Button(dlgBtnClose)
        self.placeControl(self.button_close, 16, 1, columnspan=2)
        #self.setFocus(self.button_close)
        self.connect(self.button_close, self.close)

        tid = self.label_total.getId()

        # Create the 'Play' button.
        self.button_play = pyxbmct.Button(dlgBtnPlay)
        self.placeControl(self.button_play, 16, 9, columnspan=2)
        self.button_play.setEnableCondition('Integer.IsGreater(Control.GetLabel('+ str(tid) +'),0)')
        self.connect(self.button_play, self.play)

        # Create the 'Download' button.
        self.button_dnld = pyxbmct.Button(dlgBtnSave)
        self.placeControl(self.button_dnld, 16, 12, columnspan=2)
        self.button_dnld.setEnableCondition('Integer.IsGreater(Control.GetLabel('+ str(tid) +'),0)')
        self.connect(self.button_dnld, self.download)

        self.update_calendar()

        # Connect a key action to a function.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

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
        self.button_mprev.controlDown(self.button_cal[self.day + self.month_offset - 1])
        self.button_mprev.controlRight(self.button_mnext)
        self.button_mnext.controlUp(self.radio_jpg)
        self.button_mnext.controlDown(self.button_cal[self.day + self.month_offset - 1])
        self.button_mnext.controlLeft(self.button_mprev)
        self.button_mnext.controlRight(self.button_yprev)
        self.button_yprev.controlUp(self.radio_mp4)
        self.button_yprev.controlDown(self.button_cal[self.day + self.month_offset - 1])
        self.button_yprev.controlLeft(self.button_mnext)
        self.button_yprev.controlRight(self.button_ynext)
        self.button_yprev.controlUp(self.radio_mp4)
        self.button_ynext.controlDown(self.button_cal[self.day + self.month_offset - 1])
        self.button_ynext.controlLeft(self.button_yprev)
        self.button_ynext.controlRight(self.list)
        self.button_close.controlUp(self.button_cal[self.day + self.month_offset - 1])
        self.button_close.controlRight(self.button_play)
        self.button_play.controlUp(self.list)
        self.button_play.controlLeft(self.button_close)
        self.button_play.controlRight(self.button_dnld)
        self.button_dnld.controlUp(self.list)
        self.button_dnld.controlLeft(self.button_play)
        self.list.controlLeft(self.radio_mp4)
        self.list.controlDown(self.button_play)

        log('Init done.')


    def update_calendar(self):
        currentDay   = datetime.now().day
        currentMonth = datetime.now().month
        currentYear  = datetime.now().year

        for row in range(6):
            for col in range(7):
                self.button_cal[row * 7 + col].setEnabled(False)
                self.button_cal[row * 7 + col].setVisible(False)

        self.month_offset = 0
        for row, week in enumerate(list(calendar.monthcalendar(self.year, self.month))):
            # week sequence is Mon, Tue, Wed, Thu, Fri, Sat, Sun
            for col, weekday in enumerate(week):
                if row == weekday == 0:
                    self.month_offset += 1
                # weekday is actual day of month or zero
                self.button_cal[row * 7 + col].setLabel(str(weekday), textColor=('0xFF7ACAFE' if weekday == self.day else '0xFFFFFFFF'))
                self.button_cal[row * 7 + col].setEnabled(weekday > 0 and not (self.year == currentYear and self.month == currentMonth and weekday > currentDay))
                self.button_cal[row * 7 + col].setVisible(weekday > 0)

        self.update_list()

        return


    def auth_get(self, url, *args, **kwargs):
        # Auth Scheme Mapping for Requets
        AUTH_MAP = {
            'basic': HTTPBasicAuth,
            'digest': HTTPDigestAuth,
            }

        r = requests.get(url, **kwargs)

        if r.status_code != 401:
            return r

        auth_scheme = r.headers['WWW-Authenticate'].split(' ')[0]
        auth = AUTH_MAP.get(auth_scheme.lower())

        if not auth:
            raise ValueError('Unknown authentication scheme')

        r = requests.get(url, auth=auth(*args), **kwargs)

        return r


    def status(self):
        r = self.auth_get('http://{}/cgi-bin/storageDevice.cgi?action=getDeviceAllInfo'.format(self.camIP), self.camUsr, self.camPwd)

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
        else:
            log('Failed retrieving status data from camera.')
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                log(e)
            return None

        Used = round((UsedBytes / TotalBytes) * 100.0, 1)

        #TotalGB = round((TotalBytes / 1000000000.0), 2)
        TotalMB = round((TotalBytes / 1024.0 / 1024.0), 1)

        return (Path, TotalMB, Used)


    def update_radio(self, type):
        def update_type():
            if type == 'jpg':
                if not self.radio_jpg.isSelected():
                    self.radio_jpg.setSelected(True)
                self.radio_mp4.setSelected(False)
                self.button_play.setVisible(False)
                self.type = 'jpg'
                self.update_list()
            if type == 'mp4':
                if not self.radio_mp4.isSelected():
                    self.radio_mp4.setSelected(True)
                self.radio_jpg.setSelected(False)
                self.button_play.setVisible(True)
                self.type = 'mp4'
                self.update_list()

        return update_type


    def update_calday(self, index):
        def update_day():
            self.day = int(self.button_cal[index].getLabel())
            self.update_calendar()

        return update_day


    def get_items(self):
        # Input Arguments:
        #Flags  = ['Timing', 'Manual', 'Marker', 'Event', 'Mosaic', 'Cutout']
        #Event  = ['AlarmLocal', 'VideoMotion', 'VideoLoss', 'VideoBlind', 'Traffic*']

        # Channel
        channel = 1

        # Set Type to either 'mp4' or 'jpg'
        # self.type = 'mp4'

        # Start and End Time:
        date  = '{}-{:02d}-{:02d}'.format(self.year, self.month, self.day)
        start_date = date + ' 00:00:01'
        end_date   = date + ' 23:59:59'

        # Objects count may be 100 max
        count = 100

        items = []
        numitems = 0

        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

        # Create a mediaFileFinder
        r = self.auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=factory.create'.format(self.camIP), self.camUsr, self.camPwd)
        if r.status_code == 200:
            data = r.text.split('\r\n')
            factory = data[0].split('=')[1]

            # Start findFile
            r = self.auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=findFile&object={}&condition.Channel={}&condition.StartTime={}&condition.EndTime={}&condition.Types[0]={}'.format(self.camIP, factory, channel, start_date, end_date, self.type), self.camUsr, self.camPwd)
            success = (r.text == 'OK\r\n')

            # findNextFile
            while success:
                r = self.auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=findNextFile&object={}&count={}'.format(self.camIP, factory, count), self.camUsr, self.camPwd)
                if r.status_code == 200:
                    data = r.text.split('\r\n')
                    numitems = int(data[0].split('=')[1])

                    if numitems > 0:
                        # Ignore first and last line for calculation of item length
                        numkeys = int((len(data) - 2) / numitems)
                    else:
                        numkeys = 0

                    item = {}
                    for line in data[1:-1]:
                        item.update({k: v for k,v in re.findall(r'items\[\d*\]\.(\S*)=(.*)', line)})
                        if len(item) == numkeys:
                            items.append(item)
                            item = {}
                else:
                    log('Failed retrieving media file data from camera.')
                    try:
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        log(e)
                    break

                if numitems == 0:
                    break

                xbmc.sleep(500)

            # Close and destroy the mediaFileFinder
            r = self.auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=close&object={}'.format(self.camIP, factory), self.camUsr, self.camPwd)
            r = self.auth_get('http://{}/cgi-bin/mediaFileFind.cgi?action=destroy&object={}'.format(self.camIP, factory), self.camUsr, self.camPwd)

        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        return items


    def update_list(self, selected=0):
        self.list.reset()
        self.label_total.setLabel(str(self.list.size()))
        self.update_info()

        self.items = self.get_items()

        #for index, item in enumerate(self.items):
        for item in self.items:
            try:
                li = '{} {}: {}'.format(item['StartTime'].split()[1], item['Flags[0]'], item['Events[0]'])
            except:
                pass
            self.list.addItem(li)

        self.label_total.setLabel(str(self.list.size()))

        if self.list.size() > 0:
            self.list.selectItem(selected)
            self.setFocus(self.list)
        else:
            self.setFocus(self.button_close)

        self.update_info(selected=selected)

        return


    def update_info(self, selected=None):
        if self.type == 'jpg':
            for key in self.label_info:
                self.label_info[key].setVisible(False)
            self.image_preview.setVisible(True)
        else:
            for key in self.label_info:
                self.label_info[key].setVisible(True)
            self.image_preview.setVisible(False)

        if self.list.size() > 0:
            item = self.items[selected or self.list.getSelectedPosition()]
            if self.type == 'jpg':
                # show preview of image in info section
                tmpfile = self.download(item=item, destdir=tmpdir)
                self.image_preview.setImage(tmpfile, False)

                xbmc.sleep(500)
                xbmcvfs.delete(tmpfile)
            else:
                # show file info
                self.label_info['StartTime'].setLabel(item['StartTime']) #.split()[1])
                self.label_info['EndTime'].setLabel(item['EndTime']) #.split()[1])
                self.label_info['FileSize'].setLabel('{} (KB)'.format(int(round(int(item['Length'])/1024.0, 0))))
        else:
            if self.type == 'jpg':
                self.image_preview.setImage('')
            else:
                self.label_info['StartTime'].setLabel('')
                self.label_info['EndTime'].setLabel('')
                self.label_info['FileSize'].setLabel('')

        return


    def year_next(self):
        currentYear  = datetime.now().year

        #year = int(self.label_year.getLabel())
        if self.year < currentYear:
            self.year += 1
            self.label_year.setLabel(str(self.year))
            self.update_calendar()

        return


    def year_prev(self):
        #year = int(self.label_year.getLabel())
        if self.year > 2010:
            self.year -= 1
            self.label_year.setLabel(str(self.year))
            self.update_calendar()

        return


    def month_next(self):
        currentYear   = datetime.now().year
        currentMonth  = datetime.now().month

        #month = int(self.label_month.getLabel())
        if (self.year == currentYear and self.month < currentMonth) or (self.year < currentYear and self.month < 12):
            self.month += 1
            self.day = 1
            self.label_month.setLabel(str(self.month))
            self.update_calendar()

        return


    def month_prev(self):
        #month = int(self.label_month.getLabel())
        if self.month > 1:
            self.month -= 1
            self.day = 1
            self.label_month.setLabel(str(self.month))
            self.update_calendar()

        return


    def play(self, item=None):
        if not item:
            item = self.items[self.list.getSelectedPosition()]

        #cmd = 'http://{}/cgi-bin/playBack.cgi?action=getStream&channel=1&subtype=0&startTime={}&endTime={}'.format(self.camIP, item['StartTime'], item['EndTime'])
        #cmd = 'rtsp://{}/{}'.format(self.camIP, item['FilePath'])

        tmpfile = self.download(item=item, destdir=tmpdir)

        self._player.play(tmpfile)
        xbmc.sleep(500)
        self.close()

        while self._player.isPlaying():
            if self._monitor.waitForAbort(1):
                log('Abort requested.')
                raise SystemExit

        self.doModal()

        xbmcvfs.delete(tmpfile)

        return


    def download(self, item=None, destdir=None, name=None):
        if not item:
            item = self.items[self.list.getSelectedPosition()]

        if not destdir:
            destdir = xbmc.translatePath(__profile__).decode('utf-8')

        if not xbmcvfs.exists(destdir):
            xbmcvfs.mkdir(destdir)

        path = item['FilePath']
        cmd = 'http://{}/cgi-bin/RPC_Loadfile{}'.format(self.camIP, path)

        # item['FilePath'] = e.g. /mnt/sd/2019-11-11/001/dav/21/21.40.47-21.41.33[M][0@0][0].mp4
        # item['FilePath'] = e.g. /mnt/sd/2020-10-11/001/jpg/21/09/14[M][0@0][0].jpg

        if not name:
            name = '{}_{}_{}.{}'.format(self.camName, item['StartTime'].split()[0], item['StartTime'].split()[1].replace(':', '.'), path[-3:]).decode('utf-8')

        outpath = os.path.join(destdir, name)

        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

        r = self.auth_get(cmd, self.camUsr, self.camPwd)
        if r.status_code == 200:
            #r.raw.decode_content = True
            with open(outpath, 'wb') as out:
                out.write(r.content)
                #shutil.copyfileobj(r.raw, out)

        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        return outpath


# Create a window instance.
window = DahuaCamPlayback(cam_name, cam_ip, cam_usr, cam_pwd)
# Show the created window.
window.doModal()
# Delete the window instance when it is no longer used.
del window
