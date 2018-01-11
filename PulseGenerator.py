import wx
import time
import threading
import wx.lib.buttons as buttons
import logger
import os, sys

"""
This code generates a repetitive pulse on a selected digital output of the DataSpider
The duration of the pulse and its repetition period are entered by user
"""

#When this program is closed, and re-opened, it does not work.
#There seems to be an issue with the Propeller DataSpider.
#Probably needs to add a closing function to close everything.
#08jan18 - implemented closing function - still same problem
#Stop all threads and de-register and destroy everything.

title = "Pulse Generator"
description = "Generates repetitive trigger pulses on selected DO pin"

xSize = 500    #Hor size of window button
ySize = 100    #Vert size of window button
btnSize = 70

# these are used to stop or cancel the pulsing output
pulseFlag = threading.Event()
endFlag = threading.Event()


#helper function -------
def scale_bitmap(bitmap, width, height):
    image = wx.ImageFromBitmap(bitmap)
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.BitmapFromImage(image)
    return result


def run_tool(window_parent, device):

    # ask user for selected channel (single choice)
    choices = []
    for n in range(0,4):
        choices.append( "Digital Output " + str(n) )

    dlg = wx.SingleChoiceDialog(window_parent, message="Select which output to control",\
                                caption="Output Selection", choices=choices)
    dlg.SetSelection(0)
    outDigPin = 0
    if dlg.ShowModal()== wx.ID_OK:
        outDigPin = dlg.GetSelection()
    else:
        return
    dlg.Destroy()
    digIdx = outDigPin + 1                
    digIdx = 2 ** (digIdx - 1)


    # set pulse duration
    # as it is, it takes only round numbers (integers) - 5 Dec 2017
    # GetNumberFromUser only takes long values, not float
    duration = 0.1
    while True:
        duration = wx.GetNumberFromUser("Pulse Duration: (>0.1)", "seconds", \
                                "Duration", duration,1,20,window_parent,wx.DefaultPosition)
        if duration > 0.1:
            break
    dur = str(duration)
    print "duration: ", duration, " dur: ", dur

    # set pulse period
    period = 1.1
    while True:
        period = wx.GetNumberFromUser("Pulse Period: (>"+dur+")", "seconds", "Period",\
                                period,2,10000,window_parent,wx.DefaultPosition)
        if period > duration:
            break
        
    print "period: ", period
    delay = period - duration
    print "delay: ", delay

    trig = TrigGen(window_parent, title, device, \
                   digIdx, duration, delay, xSize, ySize,\
                   pulsing)
    trig.Show()


class TrigGen(wx.Frame):
    def __init__(self, window_parent, title, device,\
                 digIdx, duration, delay,  xSize, ySize,\
                     pulsing):
        self.title = title
        self.device = device
        self.digIdx = digIdx
        self.duration = duration
        self.delay = delay
        self.xSize = xSize
        self.ySize = ySize
        self.val = True

        self.cnt = -1
        self.digPin = 0

        self.digPin = self.digIdx * 2

        while True:
            self.digPin = self.digPin / 2
            self.cnt += 1
            if self.digPin < 2:
                break

        global pulseFlag
        global endFlag
        global pt

        print "selfduration: ", self.duration

        wx.Frame.__init__(self, window_parent, wx.ID_ANY,\
                          title = self.title, size = (self.xSize,self.ySize) )


        valueFont = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False)
        
        ico = wx.Icon('OFSI.ico', wx.BITMAP_TYPE_ICO )
        self.SetIcon( ico )
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.panel = wx.Panel(self, wx.ID_ANY)
        
        durationBox = wx.StaticBox(self.panel, -1, 'Duration')
        durboxSizer = wx.StaticBoxSizer(durationBox, wx.VERTICAL)
        durationVal = wx.StaticText(self.panel, -1, str(self.duration))
        durationVal.SetFont(valueFont)
        durbox = wx.BoxSizer(wx.HORIZONTAL) 
        durbox.Add(durationVal, 0, wx.LEFT|wx.RIGHT|wx.CENTER, 20)
        durboxSizer.Add(durbox, 0, wx.ALL|wx.CENTER, 5)
        

        periodBox = wx.StaticBox(self.panel, -1, 'Period')
        perboxSizer = wx.StaticBoxSizer(periodBox, wx.VERTICAL)
        periodVal = wx.StaticText(self.panel, wx.ID_ANY,str(self.duration + self.delay))
        periodVal.SetFont(valueFont)
        perbox = wx.BoxSizer(wx.HORIZONTAL) 
        perbox.Add(periodVal, 0, wx.LEFT|wx.RIGHT|wx.CENTER, 20)
        perboxSizer.Add(perbox, 0, wx.ALL|wx.CENTER, 5)

        digoutBox = wx.StaticBox(self.panel, -1, 'Output')
        digboxSizer = wx.StaticBoxSizer(digoutBox, wx.VERTICAL)
        digVal = wx.StaticText(self.panel, wx.ID_ANY,'DO-'+str(self.cnt))
        digVal.SetFont(valueFont)
        digbox = wx.BoxSizer(wx.HORIZONTAL) 
        digbox.Add(digVal, 0, wx.LEFT|wx.RIGHT|wx.CENTER, 10)
        digboxSizer.Add(digbox, 0, wx.ALL|wx.CENTER, 5)

        self.pulseOn = scale_bitmap(wx.Bitmap("record-button-on.png"), btnSize, btnSize)
        self.pulseOff = scale_bitmap(wx.Bitmap("record-button-off.png"),btnSize, btnSize)

        self.pulseBtn = buttons.GenBitmapToggleButton(self.panel, id=wx.ID_ANY,\
                                            bitmap=self.pulseOff, size=(btnSize, btnSize))
        self.pulseBtn.SetBitmapSelected(self.pulseOn)
        self.pulseBtn.Bind(wx.EVT_BUTTON,self.tgl)

        digSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        mainSizer.Add(durboxSizer, 0, wx.ALL,5)
        mainSizer.Add(perboxSizer, 0, wx.ALL,5)
        mainSizer.Add(digboxSizer, 0, wx.ALL,5)
        mainSizer.Add(self.pulseBtn, 0, wx.ALL,5)

        self.panel.SetSizer(mainSizer)
        mainSizer.Fit(self)        
        

        #registering this object with digital channel
        self.device.digitals.register(self)
        
        pt = pulsing(self.device, self.digIdx, self.duration, self.delay)
        pt.start()

        self.Bind( wx.EVT_CLOSE, self.onClose )

    def tgl(self, e):
        global pulseFlag  
        self.value = self.pulseBtn.GetValue()
        print "tgl self-value: ", self.value
        if self.value:
            pulseFlag.set()
        else:
            pulseFlag.clear()
            
    def onClose(self, event):
        """"""
        global pt
        endFlag.set()
        time.sleep(0.5)
        print "thread object: ", pt
        try:
            if pt.isAlive():
                pt.join()
                print "end pt thread..."
            else:
                print "pt is already closed"
        except:
            print "error trying pt.join()"
            pass
        try:
            print "de-registering app...."
            self.device.digitals.deregister(self)
        except:
            print "unable to de-register..."
        print "destroying and exiting"
        self.Destroy()


# new class for pulsing in a new thread
class pulsing(threading.Thread):
    def __init__(self,device,digIdx,duration,delay):
        threading.Thread.__init__(self)
        self.device = device
        self.digIdx = digIdx                                    
        self.duration = duration
        self.delay = delay
        global pulseFlag
        global endFlag
        print "running pulsing thread"

    def run(self):
        while not endFlag.isSet():
            if pulseFlag.isSet():
                self.device.digitals.setValue(self.digIdx)
                t = time.time() + self.duration
                while t - time.time() > 0:
                    if not pulseFlag.isSet():
                        break
                    if endFlag.isSet():
                        break
                self.device.digitals.setValue(0)
                t = t + self.delay
                while t -time.time() > 0:
                    if not pulseFlag.isSet():
                        break
                    if endFlag.isSet():
                        break
                    



