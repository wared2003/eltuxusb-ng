#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This class reads the content of the file created by the main program
# and generates a graphical plot using the matplotlib library.

import re
import datetime
import matplotlib
import matplotlib.pyplot as plt


class plot:
    def __init__(self):
        self.date = []
        self.temp = []
        self.hum = []
        self.dew = []
        self.date_odd = []
        self.temp_odd = []
        self.hum_odd = []
        self.dew_odd = []
        self.limit = 10000
        self.unit = "celsius"
        self.header = ""
        self.humPos = 0
        self.tempAlarmColor = "red"
        self.humAlarmColor = "blue"
        self.highTempAlarmValue = 0
        self.lowTempAlarmValue = 0
        self.highHumAlarmValue = 0
        self.lowHumAlarmValue = 0
        self.highTempAlarmPos = 0
        self.lowTempAlarmPos = 0
        self.highHumAlarmPos = 0
        self.lowHumAlarmPos = 0
        self.dewPointPos = 0
        self.deviceModel = ""
        self.recName = ""
        self.positionCount = 3

    def parse_header(self, first_line):
        self._firstLine = first_line

        if re.search('High Alarm', self.header) is not None:
            self.highTempAlarmPos = self.positionCount
            self.highTempAlarmValue = float(re.split(",", self._firstLine)[self.positionCount])
            self.positionCount += 1

        if re.search('Low Alarm', self.header) is not None:
            self.lowTempAlarmPos = self.positionCount
            self.lowTempAlarmValue = float(re.split(",", self._firstLine)[self.positionCount])
            self.positionCount += 1

        if re.search('Humidity', self.header) is not None:
            self.deviceModel = "elusb2"
            self.humPos = self.positionCount
            self.positionCount += 1

        if re.search('High Alarm rh', self.header) is not None:
            self.highHumAlarmPos = self.positionCount
            self.highHumAlarmValue = float(re.split(",", self._firstLine)[self.positionCount])
            self.positionCount += 1

        if re.search('Low Alarm rh', self.header) is not None:
            self.lowHumAlarmPos = self.positionCount
            self.lowHumAlarmValue = float(re.split(",", self._firstLine)[self.positionCount])
            self.positionCount += 1

        if re.search('dew point', self.header) is not None:
            self.dewPointPos = self.positionCount
            self.positionCount += 1

    def parse_file(self, input_file):
        self._fichier = open(input_file)
        self.header = self._fichier.readline()
        self._data = self._fichier.readlines()
        self._firstLine = self._data[0]
        self._count = 1
        self.recName = re.split(",", self.header)[0]
        self.parse_header(self._firstLine)

        for ligne in self._data:
            self._day = re.search(',../', ligne).group()[1:3]
            self._month = re.search('/../', ligne).group()[1:3]
            self._year = re.search('/.... ', ligne).group()[1:5]
            self._hour = re.search(' ..:', ligne).group()[1:3]
            self._minute = re.search(':..:', ligne).group()[1:3]
            self._second = re.search(':..,', ligne).group()[1:3]
            self._temperature = re.split(",", ligne)[2]
            self.date.append(datetime.datetime(int(self._year), int(self._month),
                              int(self._day), int(self._hour), int(self._minute),
                              int(self._second)))

            self.temp.append(self._temperature)

            if self.deviceModel == "elusb2" or self.deviceModel == "elusb2lcd":
                self.humidity = re.split(",", ligne)[self.humPos]
                self.hum.append(self.humidity)
                self.dew_point = re.split(",", ligne)[self.dewPointPos]
                self.dew.append(self.dew_point)

            self._count += 1
        self._fichier.close()

    def array_odd(self, array_name, array_odd):
        count = 1
        for i in array_name:
            if count % 2 != 0:
                array_odd.append(i)
            count += 1
        return array_odd

    def render_plot(self):
        self.fig = plt.figure()
        plt.grid(False)
        self._ax = self.fig.add_subplot(111)
        plt.title(self.recName)
        self._ax.set_ylabel("temperature")

        # if the numbers of recordings exceed 10'000 lines, we read only the odd lines.
        if len(self.date) > self.limit:
            self.date = self.array_odd(self.date, self.date_odd)
            self.temp = self.array_odd(self.temp, self.temp_odd)

            if len(self.hum) != 0:
                self.hum = self.array_odd(self.hum, self.hum_odd)
                self.dew = self.array_odd(self.dew, self.dew_odd)

        if self.deviceModel == "elusb2" or self.deviceModel == "elusb2lcd":
            self._tempPlot = self._ax.plot(self.date, self.temp, 'r.-',
                                           self.date, self.dew, 'g.-', linewidth=2)
            self._ax2 = self._ax.twinx()
            self.hum_plot = self._ax2.plot(self.date, self.hum, 'b.-', linewidth=2)
            self._ax.legend(self._tempPlot, [self.unit, 'dew point'],
                            loc='upper left')
            self._ax2.legend(self.hum_plot, ['humidity'], loc='upper right')
            self._ax2.set_ylim(0, 100)
            self._ax2.set_ylabel("humidity")

        else:
            self._tempPlot = self._ax.plot(self.date, self.temp, 'r.-', linewidth=2)
            self.fig.legend(self._tempPlot, ['temperature'], loc='upper right')

        if self.highTempAlarmPos != 0:
            self._ax.axhline(y=self.highTempAlarmValue, color=self.tempAlarmColor, linestyle="-")

        if self.lowTempAlarmPos != 0:
            self._ax.axhline(y=self.lowTempAlarmValue, color=self.tempAlarmColor, linestyle=":")

        if self.highHumAlarmPos != 0:
            self._ax2.axhline(y=self.highHumAlarmValue, color=self.humAlarmColor, linestyle="-")

        if self.lowHumAlarmPos != 0:
            self._ax2.axhline(y=self.lowHumAlarmValue, color=self.humAlarmColor, linestyle=":")

        return self.fig
