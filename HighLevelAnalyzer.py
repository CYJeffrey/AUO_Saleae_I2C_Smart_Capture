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
            'DataCapture': {
                'format': 'Result: {{data.input_type}}'
            }
        }

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
        self.file.write(f'*****Ver.00.04*****\n')
        self.file.write(f'******************/\n')

        print("Settings:", self.my_string_setting,
              self.my_number_setting, self.my_choices_setting)
        print("Author   : Chengyu Chen ")
        print("Version  : Ver.00.04 ")

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
        
        '''Declare Global Variables'''
        self.file = open(self.file_path, 'a')
        global I2C_Write_Flag
        global I2C_Addr_0x12_Flag
        global bytecount
        global Dignositic_0x16_Flag
        global Dignositic_0x1C_Flag
        global Dignositic_0x16_Shot
        global Dignositic_0x1C_Shot
        global Dignositic_0x16_Check
        global Dignositic_0x1C_Check
        global Update_Mode

        # if self.start_time is None:
        #     self.start_time = frame.start_time
        # else:
        #     end_time = frame.start_time
        #     period = self.measure(self.start_time, end_time)
        #     self.start_time = end_time
        #     print(f'{period}')

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
            #print('start state')
            I2C_Write_Flag = 0
            I2C_Addr_0x12_Flag = 0
            bytecount = 0
            Dignositic_0x16_Shot = 0
            Dignositic_0x1C_Shot = 0
            Dignositic_0x16_Check = 0
            Dignositic_0x1C_Check = 0
            #print(Fore.LIGHTBLUE_EX + f'Start+{frame.start_time}')
            if self.repeat_start_mark == False:
                self.repeat_start_mark = True
                self.start_time = frame.start_time
                
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
                return AnalyzerFrame('DataCapture', frame.start_time, frame.end_time, {
                                    'input_type': str(float(period)*1000) + 'ms'
                })

        '''Once the target address device detected, set Flag for the next judgement.'''
        if frame.type == 'address':
            addr = frame.data['address'][0]
            WRcheck = frame.data['read']
            if WRcheck == False:
                print(f"addr {hex(addr)} W {hex(WRcheck)}")
                self.file.write(f'\nAddr {addr:#04X}')
                self.file.write(f' W')
            else:
                self.file.write(f' R')
            if frame.data['read'] == False:
                # set I2C_Write_Flag
                I2C_Write_Flag = 1
                if bytes(frame.data['address']) == b'\x12':
                    #print('write to ' + str(frame.data['address']))
                    I2C_Addr_0x12_Flag = 1
                    Dignositic_0x16_Flag = 0
                    Dignositic_0x1C_Flag = 0
                    
                else :
                    I2C_Addr_0x12_Flag = 0
            else :
                I2C_Write_Flag = 0
                if bytes(frame.data['address']) == b'\x12':
                    #print('read from ' + str(frame.data['address']))
                    I2C_Addr_0x12_Flag = 1
                else :
                    I2C_Addr_0x12_Flag = 0

        '''Search for specific diagnositic value (0x16 & 0x1C).'''
        if frame.type == 'data':
            #print('data state')
            data = frame.data['data'][0]
            self.file.write(f' {data:#04X}')
            if self.i2c_cmdid == None:
                self.i2c_cmdid = data
            # print(Fore.CYAN + f"Data: {hex(data)}")
            if I2C_Write_Flag == 1:
                # clean I2C_Write_Flag
                I2C_Write_Flag = 0
                if bytes(frame.data['data']) == b'\x16':
                    Dignositic_0x16_Flag = 1
                    #print('data 0x16 is captured')
                if bytes(frame.data['data']) == b'\x1c':
                    Dignositic_0x1C_Flag = 1
                    #print('data 0x1C is captured')
                if I2C_Addr_0x12_Flag == 1:
                    if Update_Mode == 1:
                        if bytes(frame.data['data']) == b'\x05':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = Display ID '
                            })
                        if bytes(frame.data['data']) == b'\x20':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = Dimming CTRL '
                            })
                        if bytes(frame.data['data']) == b'\x31':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Reset '
                            })
                        if bytes(frame.data['data']) == b'\x34':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Key Send '
                            })
                        if bytes(frame.data['data']) == b'\x80':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Status '
                            })
                        if bytes(frame.data['data']) == b'\x84':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Unlock '
                            })
                        if bytes(frame.data['data']) == b'\x88':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Erase '
                            })
                        if bytes(frame.data['data']) == b'\x8D':
                            return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                                'input_type': str(frame.data['data'])+' = BL Write Flash '
                            })
            elif I2C_Addr_0x12_Flag == 1:
                if Dignositic_0x16_Flag == 1:
                    bytecount = bytecount +1
                    #print('bytecount =' + str(bytecount))  'Check the byte position is good or not.'
                    if bytecount == 4:
                        if bytes(frame.data['data']) != b'\x00' :
                            print('dignositic 0x16 check = FAIL  ' + str(frame.data['data']))
                            Dignositic_0x16_Check = 'FAIL'
                        else:
                            print('dignositic 0x16 check = PASS  ' + str(frame.data['data']))
                            Dignositic_0x16_Check = 'PASS'

                        Dignositic_0x16_Shot = 1
                elif Dignositic_0x1C_Flag == 1:
                    bytecount = bytecount +1
                    #print('bytecount =' + str(bytecount))  'Check the byte position is good or not.'
                    if bytecount == 3:
                        if bytes(frame.data['data']) != b'\x00' :
                            print('dignositic 0x1C check = FAIL  ' + str(frame.data['data']))
                            Dignositic_0x1C_Check = 'FAIL'
                        else:
                            print('dignositic 0x1C check = PASS  ' + str(frame.data['data']))
                            Dignositic_0x1C_Check = 'PASS'
                        Dignositic_0x1C_Shot = 1
        '''Check every frame and show RESULT.'''
        if Dignositic_0x16_Shot == 1:
            # Clear Flag
            Dignositic_0x16_Shot = 0
            # Return the data frame itself
            if Diagnosis_Mode == 1 :
                return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                    'input_type': str(frame.data['data'])+' = '+str(Dignositic_0x16_Check)+'@Dia_16' + str(frame.start_time - frame.end_time)
                })
        elif Dignositic_0x1C_Shot == 1:
            Dignositic_0x1C_Shot = 0
            if Diagnosis_Mode == 1 :
                return AnalyzerFrame('AUO_SGM_30.45', frame.start_time, frame.end_time, {
                    'input_type': str(frame.data['data'])+' = '+str(Dignositic_0x1C_Check)+'@Dia_1C'
                })
        self.file.close()
