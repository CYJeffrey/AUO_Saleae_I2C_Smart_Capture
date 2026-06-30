# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions
import math
import numpy
import os
from colorama import Fore, Back, Style, init
from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting
from saleae.range_measurements import DigitalMeasurer
from saleae.data import GraphTimeDelta, GraphTime
from datetime import datetime

# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):
    # List of settings that a user can set for this High Level Analyzer.
    my_string_setting = StringSetting()
    my_number_setting = NumberSetting(min_value=0, max_value=100)
    my_choices_setting = ChoicesSetting(choices=('Diagnosis-Mode','Update-Mode','Capture-Mode'))
    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    if my_choices_setting == "Diagnosis-Mode":
        result_types = {
            'AUO_SGM_30.45': {
                'format': 'DiagResult: {{data.input_type}}'
            }
        }
    elif my_choices_setting == "Update-Mode":
        result_types = {
            'AUO_SGM_30.45': {
                'format': 'UpdateResult: {{data.input_type}}'
            }
        }
    else:
        result_types = {
            'error': {
                'format': 'Error!'
            },
            'DataCapture': {
                'format': 'Result: {{data.input_type}}'
            },
            'StrechCapture': {
                'format': 'StrechTime: {{data.input_type}}'
            },
            "hi2c": {
                'format': 'address: {{data.address}}; data[{{data.count}}]: [ {{data.data}} ]'
            }
        }

    temp_frame = None

    def __init__(self):
        '''
        Initialize HLA.

        Settings can be accessed using the same name used above.
        '''
        self.start_time = None
        self.i2c_cmdid = None
        self.repeat_start_mark = False
        #if not os.path.exists(r'D:\total_periods.txt'):
            #os.mkdir(r'D:\total_periods.txt')
            
        self.file_path = os.path.expanduser(r'D:\total_periods.txt')  # Change this to your desired file path

        # Open the file in write mode
        #if not os.path.exists(r'D:\total_periods.txt'):
        self.file = open(self.file_path, 'w')

        self.file.write(f'/******************\n')
        self.file.write(f'*I2C Smart Capture*\n')
        self.file.write(f'*****Ver.00.05-1*****\n')
        self.file.write(f'******************/\n')

        print("Settings:", self.my_string_setting,
              self.my_number_setting, self.my_choices_setting)
        print("Author   : Chengyu Chen ")
        print("Version  : Ver.00.05-1 ")

    def __del__(self):
        # Close the file when the analyzer is destroyed
        self.file.close()

    def time_delta_to_ms(self, time_delta):
        """
        Convert SaleaeTimeDelta to milliseconds.
        Args:
            time_delta (SaleaeTimeDelta): The time delta object.
        Returns:
            float: The time delta in milliseconds.
        """
        total_ms = time_delta.seconds * 1000 + time_delta.milliseconds
        return total_ms
    
    def measure(self, start_time, end_time):
        return end_time - start_time

    def decode(self, frame: AnalyzerFrame):
        '''
        Process a frame from the input analyzer, and optionally return a single `AnalyzerFrame` or a list of `AnalyzerFrame`s.
        The type and data values in `frame` will depend on the input analyzer.
        '''
        
        if self.temp_frame is None:
            self.temp_frame = AnalyzerFrame("error", frame.start_time, frame.end_time, {
                "address": "error",
                "data": "",
                "count": 0
            }
            )

        '''Declare Global Variables'''
        self.file = open(self.file_path, 'a')

        if self.my_choices_setting == 'Update-Mode':
            Update_Mode = 1
            Diagnosis_Mode = 0
            Capture_Mode = 0
        elif self.my_choices_setting == 'Diagnosis-Mode':
            Update_Mode = 0
            Diagnosis_Mode = 1
            Capture_Mode = 0
        else:
            Update_Mode = 0
            Diagnosis_Mode = 0
            Capture_Mode = 1

        '''When I2C start, Do initial Setting.'''
        if frame.type == 'start':
            #print(Fore.LIGHTBLUE_EX + f'Start+{frame.start_time}')
            if self.repeat_start_mark == False:
                self.repeat_start_mark = True
                self.start_time = frame.start_time
            self.space_time = frame.start_time
        if Diagnosis_Mode == 1 :
            if frame.type == "start" or (frame.type == "address" and self.temp_frame.type == "error"):
                frame_to_flush = None
                if frame.type == "start" and self.temp_frame.type != "error":
                    # the previous frame hasn't been flushed yet. Likely a repeated start event.
                    frame_to_flush = self.temp_frame
                self.temp_frame = AnalyzerFrame("hi2c", frame.start_time, frame.end_time, {
                        "address": "",
                        "data": "",
                        "count": 0
                    }
                )

        if frame.type == 'address':
            if Diagnosis_Mode == 1 :
                self.temp_frame.end_time = frame.end_time
                address_byte = frame.data["address"][0]
                self.temp_frame.data["address"] = hex(address_byte)

            print(frame.data['ack'])
            addr = frame.data['address'][0]
            self.WRcheck = frame.data['read']
            if self.WRcheck == False:
                print(f"addr {hex(addr)} W {hex(self.WRcheck)}")
                self.file.write(f'\nAddr {addr:#04X}')
                self.file.write(f' W')
            else:
                self.file.write(f' R')
        
        if frame.type == 'data':
            if Diagnosis_Mode == 1 :
                self.temp_frame.end_time = frame.end_time
                data_byte = frame.data["data"][0]
                self.temp_frame.data["count"] += 1
                if len(self.temp_frame.data["data"]) > 0:
                    self.temp_frame.data["data"] += ", "
                self.temp_frame.data["data"] += hex(data_byte)

            end_time = frame.start_time
            period = self.measure(frame.start_time, frame.end_time)
            period1 = self.measure(self.space_time, frame.start_time)
            self.space_time = frame.start_time
            print(period)
            data = frame.data['data'][0]
            self.file.write(f' {data:#04X}')
            if self.i2c_cmdid == None:
                self.i2c_cmdid = data
            print(Fore.CYAN + f"Data: {hex(data)}")
            if Capture_Mode == 1 :
                if self.WRcheck == True:
                    return AnalyzerFrame('StrechCapture', frame.start_time, frame.end_time,{
                                        'input_type': str(float(period)*1000) + 'ms'
                    })
                else:
                    return AnalyzerFrame('StrechCapture', self.start_time, frame.start_time,{
                                        'input_type': str(float(period1)*1000) + 'ms'
                    })
        
        if frame.type == 'stop':
            #print(Fore.LIGHTGREEN_EX + f'End+{frame.end_time}')
            end_time = frame.start_time
            period = self.measure(self.start_time, end_time)
            self.repeat_start_mark = False
            #print(dir(period))
            if self.i2c_cmdid != None:
                self.file.write(f'\nCMD {self.i2c_cmdid:#04X} Time {float(period)*1000000} us')
                self.i2c_cmdid = None
            else:
                self.file.write(f'\nCMD NONE Time {float(period)*1000000} us')
                self.i2c_cmdid = None
            if Capture_Mode == 1 :
                return AnalyzerFrame('DataCapture', self.space_time, frame.end_time, {
                                    'input_type': str(float(period)*1000) + 'ms'
                })
            if Diagnosis_Mode == 1 :
                self.temp_frame.end_time = frame.end_time
                new_frame = self.temp_frame
                self.temp_frame = None
                return new_frame

        self.file.close()