# -*- coding: utf-8 -*-

from enigma import getDesktop
from enigma import ePicLoad
from Screens.Screen import Screen
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Components.AVSwitch import AVSwitch
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor

from six.moves import urllib

import json
import os
import shutil
import hashlib
import glob
import threading
import tarfile
import zipfile

pl_name = "OniOn Updater"
pl_tmp = "/tmp/onion/"
pl_url = "https://tomorrow.redirectme.net/"

def printl(msg):
    print("\t" + "[" + pl_name + "] " + msg)# + "\n")

def PrepareEnv(path):
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)
        printl("(INFO) Katalog " + path + " przygotowany.")
        return 0
    except:
        printl("(ERR) Nie udało się przygotować katalogu roboczego.")
        return -1

def DownloadFile(url, filename):
    try:
        urllib.request.urlretrieve(url, pl_tmp + filename)
        printl("(INFO) Plik pobrany pomyślnie.")
        return 0
    except:
        printl("(ERR) Nie udało się pobrać pliku! (" + url + ")! Sprawdź swoje połączenie z internetem.")
        return -1

def CheckIntegrity(path, csum):
    try:
        f = open(path, mode="rb")
        fdata = f.read()
        f.close()

        if hashlib.sha512(fdata).hexdigest() != csum:
            printl("(ERR) Suma kontrolna nie zgadza się! Sprawdź swoje połączenie z internetem!")
            return -2

        printl("(INFO) Suma kontrolna poprawna.")
        return 0

    except:
        printl("(ERR) Nie udało się sprawdzić integralności pliku!")
        return -1

class MainMenu(Screen):
    def __init__(self, session, args = 0):
        try:
            self.session = session

            if PrepareEnv(pl_tmp): return -2
            if DownloadFile(pl_url + "lists.json", "lists.json"): return -3
            if self.ReadLists(pl_tmp + "lists.json"): return -4
            if self.ShowLists(): return -5

        except:
            printl("(ERR) Wystąpił nieoczekiwany błąd!")
            printl("(INFO) Daj znać i podrzuć logi albo męcz się z tym sam :)")
            return -1


    def ReadLists(self, path):
        try:
            jsonfile = open(path, 'r')
            self.lists = json.load(jsonfile)
            jsonfile.close()
            printl("(INFO) Plik z listami wczytany pomyślnie.")
            return 0
        except:
            printl("(ERR) Nie udało się odczytać pliku z listami!")
            return -1

    def ShowLists(self):
        try:
            self.skin = """<screen position="100,150" size="460,400" title="Cebulowe Menu"><widget name="listMenu" position="10,10" size="420,380" scrollbarMode="showOnDemand"/></screen>"""
            self.menu = []
            for l_uuid, l_data in self.lists["lists"].items(): self.menu.append((str(l_data["name"]), str(l_uuid)))
            self.menu.append(("Skrypty", "scripts"))
            self.menu.append(("Wyjście", "exit"))

            Screen.__init__(self, self.session)
            self["listMenu"] = MenuList(self.menu)

            self["ActionMap"] = ActionMap(["SetupActions"],
            {
                "ok": self.ShowListConfirmPrompt,
                "cancel": self.Close
            }, -1)

            printl("(INFO) Menu wyświelone poprawnie.")
            return 0
        except:
            printl("(ERR) Nie udało się wyświetlić dostępnych list!")
            return -1

    def ShowListConfirmPrompt(self):
        try:
            if self["listMenu"].l.getCurrentSelection()[1] == "exit":
                self.Close()
                return

            if self["listMenu"].l.getCurrentSelection()[1] == "scripts":
                self.session.open(ScriptMenu)
                return

            self.session.openWithCallback(self.ReadListResult, MessageBox, _("Czy na pewno chcesz zainstalować wybraną listę?"), MessageBox.TYPE_YESNO)

            printl("(INFO) Komunikat wyświetlony.")
            #return 0
        except:
            printl("(ERR) Nie udało się wyświetlić komunikatu!")
            return -1

    def ReadListResult(self, result):
        try:
            if result:
                sel = self["listMenu"].l.getCurrentSelection()
                printl("(INFO) Potwierdzono instalację listy: " + sel[0] + ".")
                printl("(INFO) UUID listy: " + sel[1] + ".")
                if self.InstallList(sel[1]): return -2
            else:
                printl("(INFO) Nastąpił powrót do menu.")

            return 0
        except:
            pritl("(ERR) Nie udało się wczytać odpowiedzi użytkownika!")
            return -1

    def InstallList(self, uuid):
        try:
            if PrepareEnv(pl_tmp): return -2
            if DownloadFile(self.lists["lists"][uuid]["url"], uuid): return -3
            if CheckIntegrity(pl_tmp + uuid, self.lists["lists"][uuid]["sha512"]): return -4
            if PrepareEnv(pl_tmp + "unpacked"): return -5
            if self.UnpackFile(pl_tmp + uuid, pl_tmp + "unpacked"): return -6
            if self.DeleteFiles(pl_tmp + uuid): return -7
            if PrepareEnv(pl_tmp + uuid): return -8
            if self.ExtractFiles(pl_tmp + "unpacked", pl_tmp + uuid): return -9
            if self.DeleteFiles("/etc/enigma2/*bouquet*"): return -10
            if self.DeleteFiles("/etc/enigma2/lame*"): return -11
            if self.DeleteFiles("/etc/enigma2/black*"): return -12
            if self.DeleteFiles("/etc/enigma2/white*"): return -13
            if self.DeleteFiles("/etc/tuxbox/*.xml"): return -14
            if self.DeleteFiles(pl_tmp + uuid + "/settings"): return -15
            if self.MoveFiles(pl_tmp + uuid + "/*.xml", "/etc/tuxbox/"): return -16
            if self.MoveFiles(pl_tmp + uuid + "/*", "/etc/enigma2/"): return -17

            printl("(INFO) Lista zainstalowana poprawnie.")

            self.session.open(MessageBox, "Sukces!\n\nLista zainstalowana pomyślnie.\n\nDekoder przeładuje się w ciągu kilku sekund.", MessageBox.TYPE_INFO)

            timer = threading.Timer(5.0, os.system, ["killall -9 enigma2"])
            timer.start()

            #os.system("killall -9 enigma2")
            return 0
        except:
            printl("(ERR) Nie udało się zainstalować listy!")
            return -1

    def UnpackFile(self, src, dst):
        try:
            f = open(src, mode="rb")
            fdata = f.read(2)
            f.close()

            if fdata == b'\x1f\x8b':    # gz magic
                f = tarfile.open(src, "r:gz")
                #print(f.getnames())
                f.extractall(dst)
                f.close()
                #shutil.unpack_archive(src, dst, "gztar")
            elif fdata == b'\x50\x4b':  # zip magic
                f = zipfile.ZipFile(src, "r")
                f.extractall(dst)
                f.close()
                #shutil.unpack_archive(src, dst, "zip")
            else:
                printl("(WARN) Nieznany typ pliku! Obsługiwane formaty to: tar.gz oraz zip.")
                return 1

            printl("(INFO) Plik rozpakowany pomyślnie.")
            return 0
        except:
            printl("(ERR) Nie udało się rozpakować pliku!")
            return -1

    def DeleteFiles(self, path):
        try:
            for f in glob.glob(path):
                printl("(INFO) Usuwam " + f + "...")
                os.remove(f)

            printl("(INFO) Pliki usunięte pomyślnie.")
            return 0
        except:
            printl("(ERR) Nie udało się usunąć plików!")
            return -1

    def ExtractFiles(self, src, dst):
        try:
            files = []
            for r, dl, fl in os.walk(src):
                for f in fl:
                    files.append(os.path.join(r, f))

            for f in files:
                shutil.move(f, dst)

            printl("(INFO) Pliki wyodrębione pomyślnie. Struktura katalogów usunięta.")
            return 0
        except:
            printl("(ERR) Nie udało się wyodrębnić plików!")
            return -1

    def MoveFiles(self, src, dst):
        try:
            for f in glob.glob(src):
                printl("(INFO) Przenoszę " + f + " do " + dst + "...")
                shutil.move(f, dst)

            printl("(INFO) Pliki przeniesione pomyślnie.")
            return 0
        except:
            printl("(ERR) Nie udało się przenieść plików!")
            return -1

    def Close(self):
        try:
            PrepareEnv(pl_tmp) # cleanup
            printl("(INFO) Plugin zamknięty.")
            self.close(None)
        except:
            printl("(ERR) Nie wiem jakim cudem udało Ci się rozwalić funkcję zamykającą, ale gratulacje! ;)")

class ScriptMenu(Screen):
    def __init__(self, session, args = 0):
        try:
            self.session = session

            if self.ReadScripts(pl_tmp + "lists.json"): return -2
            if self.ShowScripts(): return -3

        except:
            printl("(ERR) Wystąpił nieoczekiwany błąd!")
            printl("(INFO) Daj znać i podrzuć logi albo męcz się z tym sam :)")
            return -1

    def ReadScripts(self, path):
        try:
            jsonfile = open(path, 'r')
            self.lists = json.load(jsonfile)
            jsonfile.close()
            printl("(INFO) Plik z skryptami wczytany pomyślnie.")
            return 0
        except:
            printl("(ERR) Nie udało się odczytać pliku z skryptami!")
            return -1

    def ShowScripts(self):
        try:
            self.skin = """<screen position="100,150" size="460,400" title="Cebulowe Skrypty"><widget name="scriptMenu" position="10,10" size="420,380" scrollbarMode="showOnDemand"/></screen>"""
            self.menu = []
            for l_uuid, l_data in self.lists["scripts"].items(): self.menu.append((str(l_data["name"]), str(l_uuid)))
            self.menu.append(("Wyjście", "exit"))

            Screen.__init__(self, self.session)
            self["scriptMenu"] = MenuList(self.menu)

            self["ActionMap"] = ActionMap(["SetupActions"],
            {
                "ok": self.ShowScriptConfirmPrompt,
                "cancel": self.Close
            }, -1)

            printl("(INFO) Menu wyświelone poprawnie.")
            return 0
        except:
            printl("(ERR) Nie udało się wyświetlić dostępnych skryptów!")
            return -1

    def ShowScriptConfirmPrompt(self):
        try:
            if self["scriptMenu"].l.getCurrentSelection()[1] == "exit":
                self.Close()
                return

            self.session.openWithCallback(self.ReadScriptResult, MessageBox, _("Czy na pewno chcesz wykonać wybrany skrypt?\n\n" + str(self["scriptMenu"].l.getCurrentSelection()[0]) + "\n\n" + str(self.lists["scripts"][str(self["scriptMenu"].l.getCurrentSelection()[1])]["desc"])), MessageBox.TYPE_YESNO)

            printl("(INFO) Komunikat wyświetlony.")
            #return 0
        except:
            printl("(ERR) Nie udało się wyświetlić komunikatu!")
            return -1

    def ReadScriptResult(self, result):
        try:
            if result:
                sel = self["scriptMenu"].l.getCurrentSelection()
                printl("(INFO) Potwierdzono wykonanie skryptu: " + sel[0] + ".")
                printl("(INFO) UUID skryptu: " + sel[1] + ".")
                if self.ExecuteScript(sel[1]): return -2
            else:
                printl("(INFO) Nastąpił powrót do menu.")

            return 0
        except:
            printl("(ERR) Nie udało się wczytać odpowiedzi użytkownika!")
            return -1

    def ExecuteScript(self, uuid):
        try:
            if PrepareEnv(pl_tmp): return -2
            if DownloadFile(self.lists["scripts"][uuid]["url"], uuid): return -3
            if CheckIntegrity(pl_tmp + uuid, self.lists["scripts"][uuid]["sha512"]): return -4
            os.system("chmod +x " + pl_tmp + str(uuid))
            os.system("/bin/sh " + pl_tmp + str(uuid))

            printl("(INFO) Skrypt wykonany pomyślnie.")

            self.session.open(MessageBox, "Sukces!\n\nSkrypt wykonany pomyślnie.\n\nKliknij OK aby kontynuować.", MessageBox.TYPE_INFO)

            return 0
        except:
            printl("(ERR) Nie udało się wykonać skryptu!")
            return -1

    def Close(self):
        try:
            printl("(INFO) Menu skryptów zamknięte. Powrót do menu głównego.")
            self.close(None)
        except:
            printl("(ERR) Nie wiem jakim cudem udało Ci się rozwalić funkcję zamykającą, ale gratulacje! ;)")

class SplashScreen(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.sizeX = getDesktop(0).size().width()
        self.sizeY = getDesktop(0).size().height()

        self.skin='<screen name="PictureScreen" position="0,0" size="'+str(self.sizeX) + "," + str(self.sizeY) + '" title="Picture Screen" backgroundColor="#00000000"><widget name="bg" position="0,0" size="'+str(self.sizeX) + "," + str(self.sizeY) + '" zPosition="1" alphatest="on" /></screen>'

        self.picPath = "/usr/lib/enigma2/python/Plugins/Extensions/OniOn/img/bg.png"
        self.Scale = AVSwitch().getFramebufferScale()
        self.PicLoad = ePicLoad()
        self["bg"] = Pixmap()
        self.PicLoad.PictureData.get().append(self.DecodePicture)
        self.onLayoutFinish.append(self.ShowPicture)

        timer = threading.Timer(5, self.cancel)
        timer.start()

    def ShowPicture(self):
        if self.picPath is not None:
            self.PicLoad.setPara([self["bg"].instance.size().width(), self["bg"].instance.size().height(), self.Scale[0], self.Scale[1],0, 1, "#00000000"])
            self.PicLoad.startDecode(self.picPath)

    def DecodePicture(self, PicInfo = ""):
        if self.picPath is not None:
            ptr = self.PicLoad.getData()
            self["bg"].instance.setPixmap(ptr)

    def cancel(self):
        self.close(None)


def main(session, **kwargs):
    try:
        print("\n///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////\n")
        printl("OniOn Elite Team's " + pl_name + " by 3Rr0rExE404 (aka Jaron Karakan) & Czarnyker")
        print("\n///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////\n")
        printl("(INFO) Ładowanie...")
        session.open(SplashScreen)
        timer = threading.Timer(2.0, session.open, [MainMenu])
        timer.start()
    except:
        printl("-----------------------------------------------")
        printl("(ERR) Wystąpił błąd! Wina Tuska!")
        printl("(INFO) Szczegóły znajdziesz powyżej :)")
        printl("-----------------------------------------------")
        session.open(MessageBox, "Wystąpił błąd!\n\nGratulacje! Plugin rozłożył się na łopatki jak Tupolew w 2010r.\n\nSprawdź logi e2!", MessageBox.TYPE_ERROR)


def Plugins(**kwargs):
    return PluginDescriptor(name=chr(7) + pl_name, description="Cebulowy aktualizator listy kanałów", where = PluginDescriptor.WHERE_PLUGINMENU, icon="img/logo.png", fnc=main)

