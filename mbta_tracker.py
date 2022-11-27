from datetime import datetime, timedelta, timezone
import json
import time
from urllib import request
from math import floor
from mbta_gui import Ui_main_window
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

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
                '[stop]=place-chswk&route=Green-B&direction_id=0&sort=arrival_time'
                ),
                (
                'https://api-v3.mbta.com/predictions?filter'
                '[stop]=place-clmnl&route=Green-C&direction_id=0&sort=arrival_time'
                ),
                (
                'https://api-v3.mbta.com/predictions?filter'
                '[stop]=place-rsmnl&route=Green-D&direction_id=0&sort=arrival_time'
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
                self.chiswick_stopped_sig,
                self.chiswick_delayed_sig
        ]
        
        self.delayed_alerts = [
                self.chiswick_delayed_sig,
                self.cleveland_delayed_sig,
                self.reservoir_delayed_sig
        ]

    @pyqtSlot()
    def run(self):
        while True:
            for station in range(3):
                with request.urlopen(self.green_lines[station]) as url:
                    mbta_info = json.load(url)
                    for col in range(2):
                        status = mbta_info['data'][col]['attributes']['status']
                        arrival_time = mbta_info['data'][col]['attributes']['arrival_time']
                        if not status:
                            self.stopped_alerts[station].emit('color: #303030;')
                            dt = datetime.now(timezone.utc) - timedelta(hours=5, minutes=0)
                            formatted_time = datetime.fromisoformat(
                                    arrival_time.replace('T', ' ')[:-6]
                                    + '+00:00'
                            )
                            formatted_time -= dt
                            display_time = floor(formatted_time.total_seconds() / 60)
                            if display_time > 0:
                                self.arrival_times[station * 2 + col].emit(
                                        ' '
                                        + str(display_time)
                                        + ' minutes'
                                )
                                self.delayed_alerts[station].emit('color: #303030;')
                                if col == 0 and display_time > 12:
                                    self.delayed_alerts[station].emit('color: #FF4444;')
                            else:
                                self.arrival_times[station * 2 + col].emit(' Arriving')
                        else:
                            self.stopped_alerts[station].emit('color: #FF4444;')
            
            lcd_value = 60
            while lcd_value > 0:
                self.refresh_lcd_sig.emit(lcd_value)
                lcd_value -= 1
                time.sleep(1)


if __name__ == '__main__':
    app = QApplication([])
    window = QMainWindow()
    gui = Ui_main_window()
    gui.setupUi(window)
    gui.thread = QThread()
    gui.worker = MBTATracker()
    gui.worker.moveToThread(gui.thread)
    gui.thread.started.connect(gui.worker.run)
    gui.thread.start()
    window.show()
    app.exec()
   