import json
import os
import time
from datetime import datetime, timedelta, timezone
from math import floor
from urllib import request

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

from mbta_gui import Ui_main_window

# Resizes to fit on a variety of screens
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
try:
    with open('key.env', 'r') as f:
        API_KEY = f.readlines()[0]
        print(API_KEY)
except FileNotFoundError:
    API_KEY = ''

class MBTATracker(QObject):
    """Tracker object which parses the MBTA data and
    sends signals to the GUI to update every minute
    """
    # Creating signals
    chiswick_1_sig = pyqtSignal(str)
    chiswick_2_sig = pyqtSignal(str)
    chiswick_stopped_sig = pyqtSignal(str)
    chiswick_delayed_sig = pyqtSignal(str)
    cleveland_1_sig = pyqtSignal(str)
    cleveland_2_sig = pyqtSignal(str)
    cleveland_stopped_sig = pyqtSignal(str)
    cleveland_delayed_sig = pyqtSignal(str)
    reservoir_1_sig = pyqtSignal(str)
    reservoir_2_sig = pyqtSignal(str)
    reservoir_stopped_sig = pyqtSignal(str)
    reservoir_delayed_sig = pyqtSignal(str)
    refresh_lcd_sig = pyqtSignal(int)
    
    def __init__(self):
        """Connects the signals to GUI elements and creates the
        lists which are used in the tracker logic
        """
        super().__init__()
        self.chiswick_1_sig.connect(gui.chiswick_1.setText)
        self.chiswick_2_sig.connect(gui.chiswick_2.setText)
        self.cleveland_1_sig.connect(gui.cleveland_1.setText)
        self.cleveland_2_sig.connect(gui.cleveland_2.setText)
        self.reservoir_1_sig.connect(gui.reservoir_1.setText)
        self.reservoir_2_sig.connect(gui.reservoir_2.setText)
        self.chiswick_stopped_sig.connect(gui.chiswick_stopped.setStyleSheet)
        self.chiswick_stopped_sig.connect(gui.cleveland_stopped.setStyleSheet)
        self.chiswick_delayed_sig.connect(gui.reservoir_stopped.setStyleSheet)
        self.chiswick_delayed_sig.connect(gui.chiswick_delayed.setStyleSheet)
        self.cleveland_delayed_sig.connect(gui.cleveland_delayed.setStyleSheet)
        self.reservoir_delayed_sig.connect(gui.reservoir_delayed.setStyleSheet)
        self.refresh_lcd_sig.connect(gui.refresh_lcd.display)
        
        self.green_lines = [
                (
                'https://api-v3.mbta.com/predictions?filter'
                '[stop]=place-chswk&route=Green-B&direction_id=1&sort=arrival_time'
                ),
                (
                'https://api-v3.mbta.com/schedules?filter'
                '[stop]=place-clmnl&route=Green-C&direction_id=1&sort=departure_time'
                ),
                (
                'https://api-v3.mbta.com/predictions?filter'
                '[stop]=place-rsmnl&route=Green-D&direction_id=1&sort=arrival_time'
                )
        ]
        
        self.arrival_times = [
                self.chiswick_1_sig,
                self.chiswick_2_sig,
                self.cleveland_1_sig,
                self.cleveland_2_sig,
                self.reservoir_1_sig,
                self.reservoir_2_sig
        ]
        
        self.stopped_alerts = [
                self.chiswick_stopped_sig,
                self.cleveland_stopped_sig,
                self.reservoir_stopped_sig
        ]
        
        self.delayed_alerts = [
                self.chiswick_delayed_sig,
                self.cleveland_delayed_sig,
                self.reservoir_delayed_sig
        ]

    @pyqtSlot()
    def run(self):
        while True:
            # Loops through each of the 3 T stops
            for station in range(3):
                with request.urlopen(self.green_lines[station]) as url:
                    mbta_info = json.load(url)
                    k = 0
                    break_flag = None
                    previous_time = 0
                    previous_status = None
                    # Retrieves the status and arrival time whether predicted or scheduled
                    try:
                        # Writes to the top then bottom minute time status display
                        for col in range(2):
                            if break_flag:
                                break
                            try:
                                status = mbta_info['data'][col]['attributes']['status']
                            except KeyError:
                                status = None
                                pass
                            while True:
                                departure_time = mbta_info['data'][col + k]['attributes']['departure_time']
                                dt = datetime.now(timezone.utc) - timedelta(hours=5, minutes=0)
                                formatted_time = datetime.fromisoformat(
                                        departure_time.replace('T', ' ')[:-6]
                                        + '+00:00'
                                )
                                formatted_time -= dt
                                display_time = floor(formatted_time.total_seconds() / 60)
                                if display_time < 0:
                                    k += 1
                                else:
                                    break
                            
                            # If the train isn't stopped, show arrival time
                            if not status:
                                # If not stopped, displays either the minutes to wait or "Arriving" if 0
                                if display_time > 0:
                                    minute = ' minute' if display_time == 1 else ' minutes'
                                    self.arrival_times[station * 2 + col].emit(
                                            ' '
                                            + str(display_time)
                                            + minute
                                    )
                                else:
                                    self.arrival_times[station * 2 + col].emit(' Arriving')
                                    
                                # Handles delay logic
                                if previous_time > 12:
                                    self.delayed_alerts[station].emit('color: #FF4444;')
                                elif display_time - previous_time > 12:
                                    self.delayed_alerts[station].emit('color: #FF4444;')
                                else:
                                    self.delayed_alerts[station].emit('color: #303030;')
                                    
                            # Handles stoppped train logic
                            if status or previous_status:
                                self.stopped_alerts[station].emit('color: #FF4444;')
                            else:
                                self.stopped_alerts[station].emit('color: #303030;')
                        
                            previous_time = display_time
                            previous_status = status
                    except IndexError:
                        continue
                
            # Rate limit = 20 times/sec, so lcd_value must not be below 3
            lcd_value = 30
            while lcd_value > 0:
                self.refresh_lcd_sig.emit(lcd_value)
                lcd_value -= 1
                time.sleep(1)


if __name__ == '__main__':
    app = QApplication([])
    window = QMainWindow()
    gui = Ui_main_window()
    gui.setupUi(window)
    # GUI updates come from a worker thread
    gui.thread = QThread()
    gui.worker = MBTATracker()
    gui.worker.moveToThread(gui.thread)
    gui.thread.started.connect(gui.worker.run)
    gui.thread.start()
    window.show()
    app.exec()
   
