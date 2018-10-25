﻿'''
A direct implimentation of the P300's communication interface.

:copyright: (C) Espec North America, INC.
:license: MIT, see LICENSE for more details.
'''
#pylint: disable=W0703
import re
from especinteract import EspecSerial, EspecTCP

def tryfloat(val, default):
    '''
    Convert a value to a float, if its not valid return default
    '''
    try:
        return float(val)
    except Exception:
        return default

class P300(object):
    '''
    P300 communications basic implimentation

    Args:
        interface (str): The interface type to connect to: "Serial" or "TCP"
    Kwargs:
        serialport (str/int): The serial port to connect to when interface="Serial"
        baudrate (int): The baud rate to connect at when interface="Serial"
        address (int): The RS485 address of the chamber to connect to.
        host (str): The IP address or hostname of the chamber when interface="TCP"
    '''

    def __init__(self, interface, **kwargs):
        self.reflookup = {
            'REF0':{'mode':'off', 'setpoint':0},
            'REF1':{'mode':'manual', 'setpoint':20},
            'REF3':{'mode':'manual', 'setpoint':50},
            'REF6':{'mode':'manual', 'setpoint':100},
            'REF9':{'mode':'auto', 'setpoint':0}
        }
        self.ramprgms = 40
        if interface == 'Serial':
            self.ctlr = EspecSerial(
                port=kwargs.get('serialport'),
                baud=kwargs.get('baudrate'),
                address=kwargs.get('address')
            )
        else:
            self.ctlr = EspecTCP(
                host=kwargs.get('host'),
                address=kwargs.get('address')
            )

    def __del__(self):
        self.close()

    def close(self):
        '''
        Close the physical interface
        '''
        try:
            self.ctlr.close()
        except Exception:
            pass

    def rom_pgm(self, num):
        '''
        Get string for what type of program this is
        '''
        return 'RAM' if num <= self.ramprgms else 'ROM'

    def interact(self, message):
        '''
        Read a responce from the controller

        Args:
            message: the command to write
        returns:
            string: response
        '''
        return self.ctlr.interact(message)

    def read_rom(self, display=False):
        '''
        Get the rom version of the controller

        Args:
            display: If true get the controllers display rom
        returns:
            rom version as a string
        '''
        return self.ctlr.interact('ROM?%s' % (',DISP' if display else ''))

    def read_date(self):
        '''
        Get the date from the controller

        returns:
            {"year":int,"month":int,"day":int}
        '''
        rsp = self.ctlr.interact('DATE?').split('.')
        date = [rsp[0]] + rsp[1].split('/')
        return {'year':2000+int(date[0]), 'month':int(date[1]), 'day':int(date[2])}

    def read_time(self):
        '''
        Get the time from the controller

        returns:
            {"hour":int, "minute":int, "second":int}
        '''
        time = self.ctlr.interact('TIME?').split(':')
        return {'hour':int(time[0]), 'minute':int(time[1]), 'second':int(time[2])}

    def read_date_time(self):
        '''
        Get the date & time from the controller.
        Merges read_date and read_time to avoid date/time being read on a different day.
        Intended only for use with serial connections.

        returns:
            {"year":int,"month":int,"day":int, "hour":int, "minute":int, "second":int}
        '''
        date, time = self.ctlr.interact(['DATE?', 'TIME?'])
        time = time.split(':')
        ret = {'hour':int(time[0]), 'minute':int(time[1]), 'second':int(time[2])}
        tmp_date = date.split('.')
        date = [tmp_date[0]] + tmp_date[1].split('/')
        ret.update({'year':2000+int(date[0]), 'month':int(date[1]), 'day':int(date[2])})
        return ret
        
    def read_srq(self):
        '''
        Read the SRQ status

        returns:
            {"alarm":boolean, "single_step_done":boolean, "state_change":boolean, "GPIB":boolean}
        '''
        srq = list(self.ctlr.interact('SRQ?'))
        return {
            'alarm':srq[1] == '1',
            'single_step_done':srq[2] == '1',
            'state_change':srq[3] == '1',
            'GPIB':srq[6] == '1'
        }

    def read_mask(self):
        '''
        Read the SRQ mask

        returns:
            {"alarm":boolean, "single_step_done":boolean, "state_change":boolean, "GPIB":boolean}
        '''
        mask = list(self.ctlr.interact('MASK?'))
        return {
            'alarm':mask[1] == '1',
            'single_step_done':mask[2] == '1',
            'state_change':mask[3] == '1',
            'GPIB':mask[6] == '1'
        }

    def read_timer_on(self):
        '''
        Return a list of valid timers by number

        returns:
            [int]
        '''
        rsp = self.ctlr.interact('TIMER ON?').split(',')
        return [int(t) for t in rsp[1:]]

    def read_timer_use(self):
        '''
        Return the number of each set timer

        returns:
            [int]
        '''
        rsp = self.ctlr.interact('TIMER USE?').split(',')
        return [int(t) for t in rsp[1:]]

    def read_timer_list_quick(self, constant=None):
        '''
        Read the timer settings for the quick timer(timer 0)

        returns:
            {"mode":string, "time":{"hour":int, "minute":int}, "pgmnum":int, "pgmstep":int}
            "mode"="STANDBY" or "OFF" or "CONSTANT" or "RUN"
            "pgmnum" and "pgmstep" only present when mode=="RUN"
        '''
        rsp = self.ctlr.interact('TIMER LIST?,0%s' % (',CONSTANT' if constant else '' ))
        parsed = re.search(
            r"(\w+)(?:,R[AO]M:(\d+),STEP(\d+))?,(\d+):(\d+)",
            rsp 
        ) 
        ret = {
            'mode':parsed.group(1),
            'time':{'hour':int(parsed.group(4)), 'minute':int(parsed.group(5))}
        }
        if parsed.group(1) == 'RUN':
            ret.update({'pgmnum':int(parsed.group(2)), 'pgmstep':int(parsed.group(3))})
        return ret

    def read_timer_list_start(self, constant=None):
        '''
        Read the timer settings for the start timer (timer 1)

        returns:
            {
                "repeat":string,
                "time":{"hour":int, "minute":int},
                "mode":string",
                "date":{"month":int, "day":int, "year":int},
                "day":string,
                "pgmnum":int,
                "pgmstep":int
            }
            "repeat"="once" or "weekly" or "daily"
            "mode"="CONSTANT" or "RUN"
            "date" only present when "repeat"=="once"
            "pgmnum" and "step" only present when "mode"=="RUN"
            "days" only present when "repeat"=="weekly"
        '''
        rsp = self.ctlr.interact('TIMER LIST?,1%s' % (',CONSTANT' if constant else ''))

        parsed = re.search(
            r"1,MODE(\d)(?:,(\d+).(\d+)/(\d+))?(?:,([A-Z/]+))?,(\d+):(\d+),(\w+[123])",
            rsp
        )
        ret = {
            'repeat':['once', 'weekly', 'daily'][int(parsed.group(1))-1],
            'time':{'hour':int(parsed.group(6)), 'minute':int(parsed.group(7))},
            'mode':parsed.group(8)
        }
        if parsed.group(2):
            ret['date'] = {
                'year':2000+int(parsed.group(2)),
                'month':int(parsed.group(3)),
                'day':int(parsed.group(4))
            }
        if parsed.group(5):
            ret['days'] = parsed.group(5).split('/')
        if parsed.group(9):
            ret.update({'pgmnum':int(parsed.group(9)), 'pgmstep':int(parsed.group(10))})
        return ret

    def read_timer_list_stop(self):
        '''
        Read the timer settings for the start timer (timer 1)

        returns:
            {
                "repeat":string,
                "time":{"hour":int, "minute":int},
                "mode":string",
                "date":{"month":int, "day":int, "year":int},
                "day":string
            }
            "repeat"="once" or "weekly" or "daily"
            "mode"="STANDBY" or "OFF"
            "date" only present when "repeat"=="once"
            "days" only present when "repeat"=="weekly"
        '''
        rsp = self.ctlr.interact('TIMER LIST?,2')
        parsed = re.search(
            r'2,MODE(\d)(?:,(\d+).(\d+)/(\d+))?(?:,([A-Z]+))?,(\d+):(\d+),(\w+)',
            rsp
        )
        ret = {
            'repeat':['once', 'weekly', 'daily'][int(parsed.group(1))-1],
            'time':{'hour':int(parsed.group(6)), 'minute':int(parsed.group(7))},
            'mode':parsed.group(8)
        }
        if parsed.group(2):
            ret['date'] = {
                'year':2000+int(parsed.group(2)),
                'month':int(parsed.group(3)),
                'day':int(parsed.group(4))
            }
        if parsed.group(5):
            ret['days'] = parsed.group(5).split('/')
        return ret

    def read_alarm(self):
        '''
        Return a list of active alarm codes, an empty list if no alarms.

        returns:
            [int]
        '''
        rsp = self.ctlr.interact('ALARM?').split(',')
        return [int(t) for t in rsp[1:]]

    def read_keyprotect(self):
        '''
        Returns the key protection state of the controller.

        returns:
            True if protection is enabled False if not
        '''
        return self.ctlr.interact('KEYPROTECT?') == 'ON'

    def read_type(self):
        '''
        Returns the type of sensor(s), controller and max temperature of the controller

        returns:
            {"drybulb":string, "wetbulb":string, "controller":string, "tempmax":float}
            "wetbulb" only present if chamber has humidity
        '''
        rsp = self.ctlr.interact('TYPE?').split(',')
        if len(rsp) == 4:
            return {
                'drybulb':rsp[0],
                'wetbulb':rsp[1],
                'controller':rsp[2],
                'tempmax':float(rsp[3])
            }
        else:
            return {
                'drybulb':rsp[0],
                'controller':rsp[1],
                'tempmax':float(rsp[2])
            }

    def read_mode(self, detail=False, constant=None):
        '''
        Return the chamber operation state.

        Added new feature: CONSTANT 

        Args:
            detail: boolean, if True get additional information (not SCP220 compatible)
        returns:
            detail=Faslse: string "OFF" or "STANDBY" or "CONSTANT" or "RUN"
            detail=True: string (one of the following):
                "OFF""STANDBY" or "CONSTANT" or "RUN" or "RUN PAUSE" or "RUN END HOLD" or
                "RMT RUN" or "RMT RUN PAUSE" or "RMT RUN END HOLD"
        '''
        return self.ctlr.interact('MODE?%s%s' % (',DETAIL' if detail else '',',CONSTANT' if constant else '' ))

    def read_mon(self, detail=False, constant=None):
        '''
        Returns the conditions inside the chamber

        Args:
            detail: boolean, when True "mode" parameter has additional details
        returns:
            {"temperature":float,"humidity":float,"mode":string,"alarms":int}
            "humidity": only present if chamber has humidity
            "mode": see read_mode for valid parameters (with and without detail flag).
        '''
        rsp = self.ctlr.interact('MON?%s%s' % (',DETAIL' if detail else '', ',CONSTANT' if constant else '')).split(',')
        data = {'temperature':float(rsp[0]), 'mode':rsp[2], 'alarms':int(rsp[3])}
        if rsp[1]:
            data['humidity'] = float(rsp[1])
        return data

    def read_temp(self):
        '''
        Returns the temperature parameters

        returns:
            {
                "processvalue":float,
                "setpoint":float,
                "enable":boolean(always True),
                "range":{"max":float, "min":float}
            }
        '''
        rsp = self.ctlr.interact('TEMP?').split(',')
        return {
            'processvalue':float(rsp[0]),
            'setpoint':float(rsp[1]),
            'enable':True,
            'range':{'max':float(rsp[2]), 'min':float(rsp[3])}
        }

    #have raise a special error about not being avaiable on non humditity chambers?
    def read_humi(self):
        '''
        Returns the humidity parameters

        returns:
            {
                "processvalue":float,
                "setpoint":float,
                "enable":boolean,
                "range":{"max":float, "min":float}
            }
        '''
        rsp = self.ctlr.interact('HUMI?').split(',')
        try:
            hsp = float(rsp[1])
            enable = True
        except Exception:
            hsp = 0
            enable = False
        return {
            'processvalue':float(rsp[0]),
            'setpoint':hsp,
            'enable':enable,
            'range':{'max':float(rsp[2]), 'min':float(rsp[3])}
        }

    def read_set(self):
        '''
        returns the regrigeration capacity set point of the chamber

        returns:
            {"mode":string,"setpoint":int}
            "mode": "off" or "manual" or "auto"
            "setpoint: 20 or 50 or 100 (percent cooling power)
        '''
        return self.reflookup.get(self.ctlr.interact('SET?'), {'mode':'manual', 'setpoint':0})

    def read_ref(self):
        '''
        returns the state of the compressors on the system

        returns:
            [boolean] 0=high stage, 1=low stage
        '''
        rsp = self.ctlr.interact('REF?').split(',')
        if len(rsp) == 3:
            return [rsp[1] == 'ON1', rsp[2] == 'ON2']
        else:
            return [rsp[1] == 'ON1']

    #cannot be checked with a p300 with stopped plc...
    def read_relay(self):
        '''
        returns the status of each relay(time signal)

        returns:
            [boolean] len=12
        '''
        rsp = self.ctlr.interact('RELAY?').split(',')
        return [str(i) in rsp[1:] for i in range(1, 13)]

    def read_htr(self):
        '''
        returns the heater outputs

        returns:
            {"dry":flaot,"wet":float}
            "wet" is only present with humidity chambers
        '''
        rsp = self.ctlr.interact('%?').split(',')
        if len(rsp) == 3:
            return {'dry':float(rsp[1]), 'wet':float(rsp[2])}
        else:
            return {'dry':float(rsp[1])}

    def read_constant_temp(self, constant=None):
        '''
        Get the constant settings for the temperature loop

        returns:
            {"setpoint":float,"enable":True}
        '''

        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?,TEMP,C%d' % constant).split(',')
        elif constant is None: 
            rsp = self.ctlr.interact('CONSTANT SET?,TEMP').split(',')
        else:
            raise ValueError("Constant must be None or 1, 2, 3")

        # rsp = self.ctlr.interact('CONSTANT SET?,TEMP').split(',')

        return {'setpoint':float(rsp[0]), 'enable':rsp[1] == 'ON'}

    def read_constant_humi(self, constant=None):
        '''
        Get the constant settings for the humidity loop

        returns:
            {"setpoint":float,"enable":boolean}
        '''

        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('COSNTANT SET?,HUMI,C%d' % constant).split(',')
        elif constant is None:
            rsp = self.ctlr.interact('CONSTANT SET?,HUMI').split(',') 
        else: 
            raise ValueError("Constant must be None or 1, 2, 3")

        # rsp = self.ctlr.interact('CONSTANT SET?,HUMI').split(',')

        return {'setpoint':float(rsp[0]), 'enable':rsp[1] == 'ON'}

    def read_constant_ref(self, constant=None):
        '''
        Get the constant settings for the refigeration system

        returns:
            {"mode":string,"setpoint":float}
        '''

        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?,REF,C%d' % constant)
        elif constant is None:
            rsp = self.ctlr.interact('CONSTANT SET?,REF')
        else: 
            raise ValueError("Constant must be None or 1, 2, 3")

        # rsp = self.ctlr.interact('CONSTANT SET?,REF')
        try:
            return {'mode':'manual', 'setpoint':float(rsp)}
        except Exception:
            return {'mode':rsp.lower(), 'setpoint':0}

    def read_constant_relay(self, constant=None):
        '''
        Get the constant settings for the relays(time signals)

        returns:
            [int]
        '''

        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?,RELAY,C%d' % constant).split(',')
        elif constant is None:
            rsp = self.ctlr.interact('CONSTANT SET?,RELAY').split(',')
        else: 
            raise ValueError("Constant must be None or 1, 2, 3")

        # rsp = self.ctlr.interact('CONSTANT SET?,RELAY').split(',')
        return [str(i) in rsp[1:] for i in range(1, 13)]

    def read_constant_ptc(self, constant=None):
        '''
        Get the constant settings for product temperature control

        returns:
            {"enable":boolean,"deviation":{"positive":float,"negative":float}}
        '''
        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?,PTC,C%d' % constant).split(',')
        elif constant is None:
            rsp = self.ctlr.interact('CONSTANT SET?,PTC').split(',')
        else: 
            raise ValueError("Constant must be None or 1, 2, 3")

        # rsp = self.ctlr.interact('CONSTANT SET?,PTC').split(',')
        return {
            'enable': rsp[0] == 'ON',
            'deviation': {'positive':float(rsp[1]), 'negative':float(rsp[2])}
        }

    # new feature added to the new P-300 model
    def read_constant_air(self, constant=None):
        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?,AIR,C%d' % constant).split('/') 
        elif constant is None: 
            rsp = self.ctlr.interact('CONSTANT SET?,AIR').split('/') 
        else: 
            raise ValueError("Constant must be None or 1, 2, 3") 
        return { 
            'set value': rsp[0], 
            'maintenance value': rsp[1] 
        }
        
    def read_prgm_mon(self):
        '''
        get the status of the running program

        returns:
            {
                "pgmstep":int,
                "temperature":float,
                "humidity":float,
                "time":{"hour":int, "minute":int},
                "counter_a":int,
                "counter_b":int
            }
            "humidity" is only present on chambers with humidity
            "counter_?" is the cycles remaining
        '''
        rsp = self.ctlr.interact('PRGM MON?').split(',')
        if len(rsp) == 6:
            time = rsp[3].split(':')
            return {
                'pgmstep':int(rsp[0]),
                'temperature':float(rsp[1]),
                'humidity':tryfloat(rsp[2], 0),
                'time':{'hour':int(time[0]), 'minute':int(time[1])},
                'counter_a':int(rsp[4]),
                'counter_b':int(rsp[5])
            }
        else:
            time = rsp[2].split(':')
            return {
                'pgmstep':int(rsp[0]),
                'temperature':float(rsp[1]),
                'time':{'hour':int(time[0]), 'minute':int(time[1])},
                'counter_a':int(rsp[3]),
                'counter_b':int(rsp[4])
            }

    def read_prgm_set(self):
        '''
        get the name,number and end mode of the current program

        returns:
            {"number":int,"name":string,"end":string}
            "end"="OFF" or "STANDBY" or "CONSTANT" or "HOLD" or "RUN"
        '''
        rsp = self.ctlr.interact('PRGM SET?')
        parsed = re.search(r'R[AO]M:(\d+),(.+),END\((\w+)\)', rsp)
        return {'number':int(parsed.group(1)), 'name':parsed.group(2), 'end':parsed.group(3)}

    def read_prgm_use(self):
        '''
        get the id number for each program on the controller as a list

        returns:
            [int]
        '''
        rsp = self.ctlr.interact('PRGM USE?,RAM').split(',')
        return [str(i) in rsp[1:] for i in range(1, 41)]

    def read_prgm_use_num(self, pgmnum):
        '''
        get the name and creation date of a specific program

        Args:
            pgmnum: the program to read
        returns:
            {"name":string,"date":{"year":int,"month":int,"day":int}}
        '''
        rsp = re.search(
            r'(.+)?,(\d+).(\d+)\/(\d+)',
            self.ctlr.interact('PRGM USE?,%s:%d' % (self.rom_pgm(pgmnum), pgmnum))
        )
        return {
            'name':rsp.group(1) if rsp.group(1) else '',
            'date':{
                'year':2000+int(rsp.group(2)),
                'month':int(rsp.group(3)),
                'day':int(rsp.group(4))
            }
        }

    def read_prgm_data(self, pgmnum, constant=None):
        '''
        get the parameters for a given program

        Args:
            pgmnum: int, the program to get
        returns:
            {
                "steps":int,
                "name":string,
                "end":string,
                "counter_a":{"start":int, "end":int, "cycles":int},
                "counter_b":{"start":int, "end":int, "cycles":int}
            }
            "END"="OFF" or "CONSTANT" or "STANDBY" or "RUN"
        '''
        pdata = self.ctlr.interact('PRGM DATA?,%s:%d%s' % (self.rom_pgm(pgmnum), 
                                           pgmnum,',CONSTANT' if constant else ''))
        return self.parse_prgm_data(pdata)

    def read_prgm_data_detail(self, pgmnum):
        '''
        get the conditions a program will start with and its operational range

        Args:
            pgmnum: int, the program to get
        returns:
            {
                "temperature":{"range":{"max":float, "min":float},"mode":string,"setpoint":float},
                "humidity":{"range":{"max":float,"min":float},"mode":string,"setpoint":float}
            }
        '''
        pdata = self.ctlr.interact('PRGM DATA?,%s:%d,DETAIL'%(self.rom_pgm(pgmnum), pgmnum))
        return self.parse_prgm_data_detail(pdata)

    def read_prgm_data_step(self, pgmnum, pgmstep, air=None):
        '''
        get a programs step parameters and air feature

        Args:
            pgmnum: int, the program to read from
            pgmstep: int, the step to read from
        returns:
            {
                "number":int,
                "time":{"hour":int, "minute":int},
                "paused":boolean,
                "granty":boolean,
                "refrig":{"mode":string, "setpoint":int},
                "temperature":{"setpoint":float, "ramp":boolean},
                "humidity":{"setpoint":float, "enable":boolean, "ramp":boolean},
                "relay":[int]
            }
        '''
        tmp = self.ctlr.interact('PRGM DATA?,%s:%d,STEP%d%s'%(self.rom_pgm(pgmnum), pgmnum, pgmstep, ',AIR' if air else ''))
        return self.parse_prgm_data_step(tmp)

    def read_system_set(self, arg='PTCOPT'):
        '''
        return controller product monitor and or control configuration

        Args:
            arg: what to read options are: "PTCOPT","PTC","PTS"
        returns:
            string
        '''
        if arg in ['PTCOPT', 'PTC', 'PTS']:
            return self.ctlr.interact('SYSTEM SET?,%s'%arg)
        else:
            raise ValueError('arg must be one of the following: "PTCOPT","PTC","PTS"')

    def read_mon_ptc(self):
        '''
        Returns the conditions inside the chamber, including PTCON

        returns:
            {
                "temperature":{"product":float,"air":float},
                "humidity":float,
                "mode":string,
                "alarms":int
            }
            "humidity" is present only on humidity chambers
        '''
        rsp = self.ctlr.interact('MON PTC?').split(',')
        if len(rsp) == 5:
            return {
                'temperature':{'product':float(rsp[0]), 'air':float(rsp[1])},
                'humidity':float(rsp[2]),
                'mode':rsp[3],
                'alarms':int(rsp[4])
            }
        else:
            return {
                'temperature':{'product':float(rsp[0]), 'air':float(rsp[1])},
                'mode':rsp[2],
                'alarms':int(rsp[3])
            }

    def read_temp_ptc(self):
        '''
        returns the temperature paramers including product temp control settings

        returns:
            {
                "enable":boolean,
                "enable_cascade":boolean,
                "deviation":{"positive":float, "negative":float},
                "processvalue":{"air":float, "product":float},
                "setpoint":{"air":float, "product":float}
            }
        '''
        rsp = self.ctlr.interact('TEMP PTC?').split(',')
        return {
            'enable':True,
            'enable_cascade':rsp[0] == 'ON',
            'deviation':{'positive':tryfloat(rsp[5], 0), 'negative':tryfloat(rsp[6], 0)},
            'processvalue':{'air':tryfloat(rsp[2], 0), 'product':tryfloat(rsp[1], 0)},
            'setpoint':{'air':tryfloat(rsp[3], 0), 'product':tryfloat(rsp[4], 0)}
        }

    def read_set_ptc(self):
        '''
        get the product temperature control parameters (on/off, deviation settings)

        returns:
            {"enable_cascade":boolean,"deviation":{"positive":float,"negative":float}}
        '''
        rsp = self.ctlr.interact('SET PTC?').split(',')
        return {
            'enable_cascade':rsp[0] == 'ON',
            'deviation':{'positive':tryfloat(rsp[1], 0), 'negative':tryfloat(rsp[2], 0)}
        }

    def read_ptc(self):
        '''
        get the product temperature control parameters (range,p,i,filter,opt1,opt2)

        returns:
            {
                "range":{"max":float, "min":float},
                "p":float,
                "filter":float,
                "i":float,
                "opt1":0.0,
                "opt2":0.0
            }
        '''
        rsp = self.ctlr.interact('PTC?').split(',')
        return {
            'range':{'max':float(rsp[0]), 'min':float(rsp[1])},
            'p':float(rsp[2]),
            'filter':float(rsp[3]),
            'i':float(rsp[4]),
            'opt1':float(rsp[5]),
            'opt2':float(rsp[6])
        }

    def read_prgm_data_ptc(self, pgmnum, constant=None):
        '''
        get the parameters for a given program that includes ptc

        Args:
            pgmnum: int, the program to get
        returns:
            {
                "steps":int,
                "name":string,
                "end":string,
                "counter_a":{"start":int, "end":int, "cycles":int},
                "counter_b":{"start":int, "end":int, "cycles":int}
            }
            "END"="OFF" or "CONSTANT" or "STANDBY" or "RUN"
        '''
        pdata = self.ctlr.interact('PRGM DATA PTC?,%s:%d%s' % (self.rom_pgm(pgmnum), pgmnum), 
                                                           ',CONSTANT' if constant else '')
        return self.parse_prgm_data(pdata)

    def read_prgm_data_ptc_detail(self, pgmnum):
        '''
        get the conditions a program will start with and its operational range including ptc

        Args:
            pgmnum: int, the program to get
        returns:
            {
                "temperature":{"range":{"max":float, "min":float}, "mode":string,"setpoint":float},
                "humidity":{"range":{"max":float, "min":float}, "mode":string, "setpoint":float}
            }
        '''
        tmp = self.ctlr.interact('PRGM DATA PTC?,%s:%d,DETAIL' % (self.rom_pgm(pgmnum), pgmnum))
        return self.parse_prgm_data_detail(tmp)

    def read_prgm_data_ptc_step(self, pgmnum, pgmstep, air=None):
        '''
        get a programs step parameters including ptc

        Args:
            pgmnum: int, the program to read from
            pgmstep: int, the step to read from
        returns:
            {
                "number":int,
                "time":{"hour":int, "minute":int},
                "paused":boolean,
                "granty":boolean,
                "refrig":{"mode":string, "setpoint":int},
                "temperature":{
                    "setpoint":float,
                    "ramp":boolean,
                    "enable_cascade":boolean,
                    "deviation":{"positive":float, "negative":float}
                },
                "humidity":{
                    "setpoint":float,
                    "enable":boolean,
                    "ramp":boolean
                },
                "relay":[int]
            }
        '''
        tmp = self.ctlr.interact('PRGM DATA PTC?,%s:%d,STEP%d%s' % (self.rom_pgm(pgmnum),
                                                          pgmnum, pgmstep, ',AIR' if air else ''))
        return self.parse_prgm_data_step(tmp)

    def read_run_prgm_mon(self):
        '''
        Get the state of the remote program being run

        returns:
            {
                "pgmstep":int,
                "temperature":float,
                "humidity":float,
                "time":{"hour":int, "minute":int},
                "counter":int
            }
            "humidity" is present only on humidity chambers
        '''
        rsp = self.ctlr.interact('RUN PRGM MON?').split(',')
        if len(rsp) == 5:
            time = rsp[3].split(':')
            return {
                'pgmstep':int(rsp[0]),
                'temperature':float(rsp[1]),
                'humidity':float(rsp[2]),
                'time':{'hour':int(time[0]), 'minute':int(time[1])},
                'counter':int(rsp[4])
            }
        else:
            time = rsp[2].split(':')
            return {
                'pgmstep':int(rsp[0]),
                'temperature':float(rsp[1]),
                'time':{'hours':int(time[0]), 'minuets':int(time[1])},
                'counter':int(rsp[3])
            }

    #not tested
    def read_run_prgm(self, air=None):
        '''
        get the settings for the remote program being run

        returns:
            {
                "temperature":{"start":float,"end":float},"humidity":{"start":float,"end":float},
                "time":{"hours":int,"minutes":int},"refrig":{"mode":string,"setpoint":}
            }
        '''
        rsp = self.ctlr.interact('RUN PRGM?%s' % (',AIR' if air else ''))
        parsed = re.search(
            r'TEMP([0-9.-]+) GOTEMP([0-9.-]+)(?: HUMI(\d+) GOHUMI(\d+))? TIME(\d+):(\d+) (\w+)'
            r'(?: RELAYON,([0-9,]+))?',
            rsp
        )
        ret = {
            'temperature':{'start':float(parsed.group(1)), 'end':float(parsed.group(2))},
            'time':{'hours':int(parsed.group(5)), 'minutes':int(parsed.group(6))},
            'refrig':self.reflookup.get(parsed.group(7), {'mode':'manual', 'setpoint':0})
        }
        if parsed.group(3):
            ret['humidity'] = {'start':float(parsed.group(3)), 'end':float(parsed.group(4))}
        if parsed.group(8):
            relays = parsed.group(8).split(',')
            ret['relay'] = [str(i) in relays for i in range(1, 13)]
        else:
            ret['relay'] = [False for i in range(1, 13)]

    def read_ip_set(self):
        '''
        Read the configured IP address of the controller
        '''
        return dict(zip(['address', 'mask', 'gateway'], self.ctlr.interact('IPSET?').split(',')))

    #--- write methods --- write methods --- write methods --- write methods --- write methods ---

    def write_date(self, year, month, day, dow):
        '''
        write a new date to the controller

        Args:
            year: int,2007-2049
            month: int,1-12
            day: int,1-31
        '''
        cyear = (year - 2000) if year > 2000 else year
        self.ctlr.interact('DATE,%d.%d/%d. %s' % (cyear, month, day, dow))

    def write_time(self, hour, minute, second):
        '''
        write a new time to the controller

        Args:
            hour: int,0-23
            minute: int,0-59
            second: int,0-59
        '''
        self.ctlr.interact('TIME,%d:%d:%d' %(hour, minute, second))

    def write_mask(self, alarm=False, single_step_done=False, state_change=False, gpib=False):
        '''
        write the srq mask

        Args:
            alarm,single_step_done,state_change,GPIB: boolean
        '''
        self.ctlr.interact('MASK,0%d%d%d00%d0' % (
            int(alarm),
            int(single_step_done),
            int(state_change),
            int(gpib)))

    def write_srq(self):
        '''
        reset the srq register
        '''
        self.ctlr.interact('SRQ,RESET')

    def write_timer_quick(self, mode, time, pgmnum=None, pgmstep=None):
        '''
        write the quick timer parameters to the controller(timer 0)

        Args:
            mode: string, "STANDBY" or "OFF" or "CONSTANT" or "RUN"
            time: {"hour":int,"minute":int}, the time to wait
            pgmnum: int, program to run if mode=="RUN"
            pgmstep: int, program step to run if mode=="RUN"
        '''
        cmd = 'TIMER WRITE,NO0,%d:%d,%s' % (time['hour'], time['minute'], mode)
        if mode == 'RUN':
            cmd = '%s,%s:%d,STEP%d' % (cmd, self.rom_pgm(pgmnum), pgmnum, pgmstep)
        self.ctlr.interact(cmd)

    def write_timer_start(self, repeat, time, mode, **kwargs):
        '''
        write the start timer parameters to the controller (timer 1)

        Args:
            repeat: string, "once" or "weekly" or "daily"
            time: {"hour":int,"minute":int}, the time of day to start the chamber
            mode: string, "CONSTANT" or "RUN"
            date: {"month":int,"day":int,"year":int}, date to start chamber on when repeat=="once"
            days: [string], the day to start the chamber on when repeat=="weekly" i.e. "WED"
            pgmnum: int,
            pgmstep: int, only present when "mode"=="RUN"
        '''
        date, days, pgmnum = kwargs.get('date'), kwargs.get('days'), kwargs.get('pgmnum')
        pgmstep = kwargs.get('pgmstep')
        cmd = 'TIMER WRITE,NO1,MODE%d' % {'once':1, 'weekly':2, 'daily':3}[repeat]
        if repeat == 'once':
            cmd = '%s,%d.%d/%d' % (cmd, date['year']-2000, date['month'], date['day'])
        elif repeat == 'weekly':
            cmd = '%s,%s' % (cmd, '/'.join(days))
        cmd = '%s,%d:%d,%s' % (cmd, time['hour'], time['minute'], mode)
        if mode == 'RUN':
            cmd = '%s,%s:%d,STEP%d' % (cmd, self.rom_pgm(pgmnum), pgmnum, pgmstep)
        self.ctlr.interact(cmd)

    def write_timer_stop(self, repeat, time, mode, date=None, days=None):
        '''
        write the stop timer parameters to the controller (timer 2)

        Args:
            repeat: string, "once" or "weekly" or "daily"
            time: {"hour":int,"minute":int}, the time of day to start the chamber
            mode: string, "STANDBY" or "OFF"
            date: {"month":int,"day":int,"year":int}, date to start chamber on when repeat=="once"
            days: [string], the day to start the chamber on when repeat=="weekly" i.e. "WED"
        '''
        cmd = 'TIMER WRITE,NO2,MODE%d' % {'once':1, 'weekly':2, 'daily':3}[repeat]
        if repeat == 'once':
            cmd = '%s,%d.%d/%d' % (cmd, date['year']-2000, date['month'], date['day'])
        elif repeat == 'weekly':
            cmd = '%s,%s' % (cmd, '/'.join(days))
        cmd = '%s,%d:%d,%s' % (cmd, time['hour'], time['minute'], mode)
        self.ctlr.interact(cmd)

    def write_timer_erase(self, timer):
        '''
        erase the give timer

        Args:
            timer: string, "quick" or "start" or "stop"
        '''
        self.ctlr.interact('TIMER ERASE,NO%d' % ({'quick':0, 'start':1, 'stop':2}[timer]))

    def write_timer(self, timer, run):
        '''
        set the run mode of a give timer

        Args:
            timer: string, "quick" or "start" or "stop"
            run: boolean, True=turn timer on, False=turn timer off
        '''
        tmp = {'quick':0, 'start':1, 'stop':2}
        self.ctlr.interact('TIMER,%s,%d' % ('ON' if run else 'OFF', tmp[timer]))

    def write_keyprotect(self, enable):
        '''
        enable/disable change and operation protection

        Args:
            enable: boolean True=protection on, False=protection off
        '''
        self.ctlr.interact('KEYPROTECT,%s' % ('ON' if enable else 'off'))

    def write_power(self, start):
        '''
        turn on the chamber power

        Args:
            start: boolean True=start constant1, False=Turn contoller off)
        '''
        self.ctlr.interact('POWER,%s' % ('ON' if start else 'off'))

    def write_air(self, speed, constant=None):
        """
        turn on air speed
        """
        if speed in range(1,11):
            if constant in [1, 2, 3]:
                self.ctlr.interact('AIR,%d,%d' % (speed, constant))
            elif constant is None: 
                self.ctlr.interact('AIR,%d' % speed)
            else:
                raise ValueError("Constant must be None or 1, 2, 3")
        else:
            raise ValueError("Speed must be given")

    def write_temp(self, constant=None, **kwargs):
        '''
        update the temperature parameters

        Args:
            setpoint: float
            max: float
            min: float
            range: {"max":float, "min":float}
        '''
        setpoint, maximum, minimum = kwargs.get('setpoint'), kwargs.get('max'), kwargs.get('min')

        if setpoint is not None and minimum is not None and maximum is not None:
            if constant is None:
                self.ctlr.interact('TEMP, S%0.1f H%0.1f L%0.1f' % (setpoint, maximum, minimum))
            elif constant in [1, 2, 3]:
                self.ctlr.interact('TEMP, S%0.1f H%0.1f L%0.1f, C%d' % (setpoint, 
                                                                    maximum, minimum, constant))
            else:
                raise ValueError("Constant must be None or 1, 2 or 3") 
        else:
            if constant in [1, 2, 3]:
                if setpoint is not None:
                    self.ctlr.interact('TEMP, S%0.1f, C%d' % (setpoint, constant))
                
                if minimum is not None:
                    self.ctlr.interact('TEMP, L%0.1f, C%d' % (minimum, constant))

                if maximum is not None:
                    self.ctlr.interact('TEMP, H%0.1f, C%d' % (maximum, constant))

            elif constant is None:
                if setpoint is not None:
                    self.ctlr.interact('TEMP, S%0.1f' % setpoint)
                
                if minimum is not None:
                    self.ctlr.interact('TEMP, L%0.1f' % minimum)

                if maximum is not None:
                    self.ctlr.interact('TEMP, H%0.1f' % maximum)
            else:
                raise ValueError("Constant must be None or 1, 2 or 3") 

    def write_humi(self, constant=None, **kwargs):
        '''
        update the humidity parameters

        Args:
            enable: boolean
            setpoint: float
            max: float
            min: float
            range: {"max":float,"min":float}
        '''
        setpoint, maximum, minimum = kwargs.get('setpoint'), kwargs.get('max'), kwargs.get('min')
        enable = kwargs.get('enable')
        if enable is False:
            spstr = 'SOFF'
        elif setpoint is not None:
            spstr = ' S%0.1f' % setpoint
        else:
            spstr = None
        # For Non-air feature:
        # if spstr is not None and minimum is not None and maximum is not None:
        #     self.ctlr.interact('HUMI,%s H%0.1f L%0.1f' % (spstr, maximum, minimum))
        # else:
        #    if spstr is not None:
        #        self.ctlr.interact('HUMI,' + spstr)
        #    if minimum is not None:
        #        self.ctlr.interact('HUMI, L%0.1f' % minimum)
        #    if maximum is not None:
        #        self.ctlr.interact('HUMI, H%0.1f' % maximum)
        if spstr is not None and minimum is not None and maximum is not None:
            if constant is None:
                self.ctlr.interact('HUMI, %s H%0.1f L%0.1f' % (spstr, maximum, minimum)) 
            elif constant in [1, 2, 3]:
                self.ctlr.interact('HUMI, %s H%0.1f L%0.1f, C%d' % (spstr, maximum, minimum, constant))
            else:
                raise ValueError("Constant must be None or 1, 2 or 3")
        else:
            if constant in [1, 2, 3]:
                if spstr is not None:
                    self.ctlr.interact('HUMI,' + spstr + ',C%d' % constant)
                if minimum is not None: 
                    self.ctlr.interact('HUMI, L%0.1f, C%d' % (minimum, constant)) 
                if maximum is not None: 
                    self.ctlr.interact('HUMI, H%0.1f, C%d' % (maximum, constant))
            elif constant is None:
                if spstr is not None: 
                    self.ctlr.interact('HUMI,' + spstr) 
                if minimum is not None: 
                    self.ctlr.interact('HUMI, L%0.1f' % minimum)
                if maximum is not None:
                    self.ctlr.interact('HUMI, H%0.1f' % maximum)
            else:
                raise ValueError("Constant must be None or 1, 2 or 3") 

    def write_set(self, mode, setpoint=0, constant = None):
        '''
        Set the constant setpoints refrig mode

        Args:
            mode: string,"off" or "manual" or "auto"
            setpoint: int,20 or 50 or 100
        '''
        if constant is None: 
            self.ctlr.interact('SET,%s' % self.encode_refrig(mode, setpoint))
        elif constant in [1, 2, 3]: 
            self.ctlr.interact('SET,%s,C%d' % (self.encode_refrig(mode, setpoint), constant))
        else: 
            raise ValueError("Constant must be None or 1, 2 or 3")

    def write_relay(self, relays, constant=None):
        '''
        set each relay(time signal)

        Args:
            relays: [boolean] True=turn relay on, False=turn relay off, None=do nothing
        '''

        vals = self.parse_relays(relays) 
        if constant in [1, 2, 3]:
            if len(vals['on']):
                self.ctlr.interact('RELAY,ON,%s,C%d' % (','.join(str(v) for v in vals['on']), 
                                                                             constant))
            if len(vals['off']):
                self.ctlr.interact('RELAY,OFF,%s,C%d' % (','.join(str(v) for v in vals['off']), 
                                                                             constant))
        elif constant is None: 
            if len(vals['on']) > 0:
                self.ctlr.interact('RELAY,ON,%s' % ','.join(str(v) for v in vals['on']))
            if len(vals['off']) > 0:
                self.ctlr.interact('RELAY,OFF,%s' % ','.join(str(v) for v in vals['off']))
        else: 
            raise ValueError("Constant must be None or 1, 2 or 3")

    def write_prgm_run(self, pgmnum, pgmstep):
        '''
        runs a program at the given step

        params:
            pgmnum: int, program to run
            prgmstep: int, step to run
        '''
        self.ctlr.interact('PRGM,RUN,%s:%d,STEP%d' % (self.rom_pgm(pgmnum), pgmnum, pgmstep))

    def write_prgm_pause(self):
        '''
        pause a running program.
        '''
        self.ctlr.interact('PRGM,PAUSE')

    def write_prgm_continue(self):
        '''
        resume execution of a paused program
        '''
        self.ctlr.interact('PRGM,CONTINUE')

    def write_prgm_advance(self):
        '''
        skip to the next step of a running program
        '''
        self.ctlr.interact('PRGM,ADVANCE')

    def write_prgm_end(self, mode="STANDBY", constant = None):
        '''
        stop the running program

        Args:
            mode: string, vaid options: "HOLD"/"CONST"/"OFF"/"STANDBY"(default)
        ''' 
        if constant is None:    
            if mode in ["HOLD", "CONST", "OFF", "STANDBY"]:
                self.ctlr.interact('PRGM,END,%s' % mode)
            else:
                raise ValueError('"mode" must be "HOLD"/"CONST"/"OFF"/"STANDBY"')

        elif constant in [1, 2, 3]: 
            if mode in ["HOLD", "CONST", "OFF", "STANDBY"]:
                self.ctlr.interact('PRGM,END,%s,CONST%d' % (mode, constant)) 
            else:
                raise ValueError('"mode" must be "HOLD"/"CONST"/"OFF"/"STANDBY"')    
        else:
            raise ValueError("Constant must be None or 1, 2 or 3") 

    def write_mode_off(self):
        '''
        turn the controller screen off
        '''
        self.ctlr.interact('MODE,OFF')

    def write_mode_standby(self):
        '''
        stop operation(STANDBY)
        '''
        self.ctlr.interact('MODE,STANDBY')

    def write_mode_constant(self, constant = None):
        '''
        run constant setpoint 1
        '''
        if constant is None: 
            self.ctlr.interact('MODE,CONSTANT')
        elif constant in [1, 2, 3]:
            self.ctlr.interact('MODE,CONSTANT,C%d' % constant) 
        else:
            raise ValueError("Constant must be None or 1, 2 or 3") 

    def write_mode_run(self, pgmnum):
        '''
        run a program given by number

        Args:
            pgmnum: int, the program to run
        '''
        self.ctlr.interact('MODE,RUN%d' % pgmnum)

    def write_prgm_data_edit(self, pgmnum, mode, overwrite=False):
        '''
        start/stop/cancel program editing on a new or exising program

        Args:
            pgmnum: int, the program to start/stop/cancel editing on
            mode: string, "START" or "END" or "CANCEL"
            overwrite: boolean, when true programs/steps may be overwritten
        '''
        tmp = 'PRGM DATA WRITE,PGM%d,%s %s'%(pgmnum, 'OVER WRITE' if overwrite else 'EDIT', mode)
        self.ctlr.interact(tmp)

    def write_prgm_data_details(self, pgmnum, constant=None, **pgmdetail):
        '''
        write the various program wide parameters to the controller

        Args:
            pgmnum: int, the program being written or edited
            pgmdetail: the program details see write_prgmDataDetail for parameters
        '''
        if 'counter_a' in pgmdetail and pgmdetail['counter_a']['cycles'] > 0:
            ttp = (pgmnum, pgmdetail['counter_a']['start'], pgmdetail['counter_a']['end'],
                   pgmdetail['counter_a']['cycles'])
            tmp = 'PRGM DATA WRITE,PGM%d,COUNT,A(%d.%d.%d)' % ttp
            if 'counter_b' in pgmdetail and pgmdetail['counter_b']['cycles'] > 0:
                ttp = (tmp, pgmdetail['counter_b']['start'], pgmdetail['counter_b']['end'],
                       pgmdetail['counter_b']['cycles'])
                tmp = '%s,B(%d.%d.%d)' % ttp
            self.ctlr.interact(tmp)
        elif 'counter_b' in pgmdetail and pgmdetail['counter_b']['cycles'] > 0:
            ttp = (pgmnum, pgmdetail['counter_b']['start'], pgmdetail['counter_b']['end'],
                   pgmdetail['counter_b']['cycles'])
            self.ctlr.interact('PRGM DATA WRITE,PGM%d,COUNT,B(%d.%d.%d)' % ttp)
        if 'name' in pgmdetail:
            self.ctlr.interact('PRGM DATA WRITE,PGM%d,NAME,%s' % (pgmnum, pgmdetail['name']))
        if 'end' in pgmdetail:
            if pgmdetail['end'] != 'RUN' and constant in [1,2,3]: 
                ttp = (pgmnum, '%s,CONSTANT%d' % (pgmdetail['end'], constant))
            elif pgmdetail['end'] != 'RUN' and constant is None:
                ttp = (pgmnum, pgmdetail['end'])     
            else:
                ttp = (pgmnum, 'RUN,PTN%s'%pgmdetail['next_prgm'])
            self.ctlr.interact('PRGM DATA WRITE,PGM%d,END,%s' % ttp)
        if 'tempDetail' in pgmdetail:
            if 'range' in pgmdetail['tempDetail']:
                ttp = (pgmnum, pgmdetail['tempDetail']['range']['max'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,HTEMP,%0.1f' % ttp)
                ttp = (pgmnum, pgmdetail['tempDetail']['range']['min'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,LTEMP,%0.1f' % ttp)
            if 'mode' in pgmdetail['tempDetail']:
                ttp = (pgmnum, pgmdetail['tempDetail']['mode'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,PRE MODE,TEMP,%s' % ttp)
            if 'setpoint' in pgmdetail['tempDetail'] and pgmdetail['tempDetail']['mode'] == 'SV':
                ttp = (pgmnum, pgmdetail['tempDetail']['setpoint'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,PRE TSV,%0.1f' % ttp)
        if 'humiDetail' in pgmdetail:
            if 'range' in pgmdetail['humiDetail']:     
                ttp = (pgmnum, pgmdetail['humiDetail']['range']['max'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,HHUMI,%0.0f' % ttp)
                ttp = (pgmnum, pgmdetail['humiDetail']['range']['min'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,LHUMI,%0.0f' % ttp)
            if 'mode' in pgmdetail['humiDetail']:
                ttp = (pgmnum, pgmdetail['humiDetail']['mode'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,PRE MODE,HUMI,%s' % ttp)
            if 'setpoint' in pgmdetail['humiDetail'] and pgmdetail['humiDetail']['mode'] == 'SV':
                ttp = (pgmnum, pgmdetail['humiDetail']['setpoint'])
                self.ctlr.interact('PRGM DATA WRITE,PGM%d,PRE HSV,%0.0f' % ttp)

    def write_prgm_data_step(self, pgmnum, **pgmstep):
        '''
        write a program step to the controller

        Args:
            pgmnum: int, the program being written/edited
            pgmstep: the program parameters, see read_prgm_data_step for parameters
        '''
        cmd = 'PRGM DATA WRITE, PGM%d, STEP%d' % (pgmnum, pgmstep['number'])
        if 'time' in pgmstep:
            cmd = '%s,TIME%d:%d' % (cmd, pgmstep['time']['hour'], pgmstep['time']['minute'])
        if 'paused' in pgmstep:
            cmd = '%s,PAUSE %s' % (cmd, 'ON' if pgmstep['paused'] else 'OFF') 
        if 'air' in pgmstep:
            cmd = '%s%s' % (cmd, ',AIR3' if pgmstep['air'] else '')
        if 'refrig' in pgmstep:
            cmd = '%s,%s' % (cmd, self.encode_refrig(**pgmstep['refrig']))
        if 'granty' in pgmstep:
            cmd = '%s,GRANTY %s' % (cmd, 'ON' if pgmstep['granty'] else 'OFF')
        if 'temperature' in pgmstep:
            if 'setpoint' in pgmstep['temperature']:
                cmd = '%s,TEMP%0.1f' % (cmd, pgmstep['temperature']['setpoint'])
            if 'ramp' in pgmstep['temperature']:
                cmd = '%s,TRAMP%s' % (cmd, 'ON' if pgmstep['temperature']['ramp'] else 'OFF')
            if 'enable_cascade' in pgmstep['temperature']:
                cmd = '%s,PTC%s'%(cmd, 'ON' if pgmstep['temperature']['enable_cascade'] else 'OFF')
            if 'deviation' in pgmstep['temperature']:
                ttp = (cmd, pgmstep['temperature']['deviation']['positive'],
                       pgmstep['temperature']['deviation']['negative'])
                cmd = '%s,DEVP%0.1f,DEVN%0.1f' % ttp
        if 'humidity' in pgmstep:
            if 'setpoint' in pgmstep['humidity']:
                if pgmstep['humidity']['enable']:
                    htmp = '%0.0f' % pgmstep['humidity']['setpoint']
                else:
                    htmp = 'OFF'
                cmd = '%s,HUMI%s' % (cmd, htmp)
            if 'ramp' in pgmstep['humidity'] and pgmstep['humidity']['enable']:
                cmd = '%s,HRAMP%s' % (cmd, 'ON' if pgmstep['humidity']['ramp'] else 'OFF')
        if 'time' in pgmstep:
            cmd = '%s,TIME%d:%d' % (cmd, pgmstep['time']['hour'], pgmstep['time']['minute'])
        if 'granty' in pgmstep:
            cmd = '%s,GRANTY %s' % (cmd, 'ON' if pgmstep['granty'] else 'OFF')
        if 'paused' in pgmstep:
            cmd = '%s,PAUSE %s' % (cmd, 'ON' if pgmstep['paused'] else 'OFF')
        if 'refrig' in pgmstep:
            cmd = '%s,%s' % (cmd, self.encode_refrig(**pgmstep['refrig']))
        if 'relay' in pgmstep:
            rlys = self.parse_relays(pgmstep['relay'])
            if rlys['on']:
                cmd = '%s,RELAY ON%s' % (cmd, '.'.join(str(v) for v in rlys['on']))
            if rlys['off']:
                cmd = '%s,RELAY OFF%s' % (cmd, '.'.join(str(v) for v in rlys['off']))
        self.ctlr.interact(cmd)

    def write_prgm_erase(self, pgmnum):
        '''
        erase a program

        Args:
            pgmnum: int, the program to erase
        '''
        self.ctlr.interact('PRGM ERASE,%s:%d'%(self.rom_pgm(pgmnum), pgmnum))

    def write_run_prgm(self, temp, hour, minute, gotemp=None, humi=None, gohumi=None, relays=None, constant=None):
        '''
        Run a remote program (single step program)

        Args:
            temp: float, temperature to use at the start of the step
            hour: int, # of hours to run the step
            minute: int, # of minutes to run the step
            gotemp: float, temperature to end the step at(optional for ramping)
            humi: float, the humidity to use at the start of the step (optional)
            gohumi: float, the humidity to end the steap at (optional for ramping)
            relays: [boolean], True= turn relay on, False=turn relay off, None=Do nothing
            air: int, # of air speed to provide to system to operate 
        '''
        cmd = 'RUN PRGM, TEMP%0.1f TIME%d:%d' % (temp, hour, minute)
        if gotemp is not None:
            cmd = '%s GOTEMP%0.1f' % (cmd, gotemp)
        if humi is not None:
            cmd = '%s HUMI%0.0f' % (cmd, humi)
        if gohumi is not None:
            cmd = '%s GOHUMI%0.0f' % (cmd, gohumi)
        rlys = self.parse_relays(relays) if relays is not None else {'on':None, 'off':None}
        if rlys['on']:
            cmd = '%s RELAYON,%s' % (cmd, ','.join(str(v) for v in rlys['on']))
        if rlys['off']:
            cmd = '%s RELAYOFF,%s' % (cmd, ','.join(str(v) for v in rlys['off'])) 
        if constant is not None: 
            cmd = '%s AIR%d' % (cmd, constant)

        self.ctlr.interact(cmd)

    def write_temp_ptc(self, enable, positive, negative):
        '''
        set product temperature control settings

        Args:
            enable: boolean, True(on)/False(off)
            positive: float, maximum positive deviation
            negative: float, maximum negative deviation
        '''
        ttp = ('ON' if enable else 'OFF', positive, negative)
        self.ctlr.interact('TEMP PTC, PTC%s, DEVP%0.1f, DEVN%0.1f' % ttp)

    def write_ptc(self, op_range, pid_p, pid_filter, pid_i, **kwargs):
        '''
        write product temp control parameters to controller

        Args:
            range: {"max":float,"min":float}, allowable range of operation
            p: float, P parameter of PID
            i: float, I parameter of PID
            filter: float, filter value
            opt1,opt2 not used set to 0.0
        '''
        opt1, opt2 = kwargs.get('opt1', 0), kwargs.get('opt2', 0)
        ttp = (op_range['max'], op_range['min'], pid_p, pid_filter, pid_i, opt1, opt2)
        self.ctlr.interact('PTC,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f' % ttp)

    def write_ip_set(self, address, mask, gateway):
        '''
        Write the IP address configuration to the controller
        '''
        self.ctlr.interact('IPSET,%s,%s,%s' % (address, mask, gateway))

    # --- helpers etc --- helpers etc --- helpers etc --- helpers etc -- helpers etc -- helpers etc
    def parse_prgm_data_step(self, arg):
        '''
        Parse a program step
        '''
        parsed = re.search(
            r'(\d+),TEMP([0-9.-]+),TEMP RAMP (\w+)(?:,PTC (\w+))?(?:,HUMI([^,]+)'
            r'(?:,HUMI RAMP (\w+))?)?,TIME(\d+):(\d+),GRANTY (\w+),REF(\w+)'
            r'(?:,RELAY ON([0-9.]+))?(?:,PAUSE (\w+))?(?:,DEVP([0-9.-]+),DEVN([0-9.-]+))?',
            arg
        )
        base = {'number':int(parsed.group(1)),
                'time':{'hour':int(parsed.group(7)),
                        'minute':int(parsed.group(8))},
                'paused':parsed.group(12) == 'ON',
                'granty':parsed.group(9) == 'ON',
                'refrig':self.reflookup.get(
                    'REF' + parsed.group(10),
                    {'mode':'manual', 'setpoint':0}
                ),
                'temperature':{'setpoint':float(parsed.group(2)),
                               'ramp':parsed.group(3) == 'ON'}}
        if parsed.group(5):
            base['humidity'] = {
                'setpoint':tryfloat(parsed.group(5), 0.0),
                'enable':parsed.group(5) != ' OFF',
                'ramp':parsed.group(6) == 'ON'
            }
        if parsed.group(4):
            base['temperature'].update({
                'enable_cascade':parsed.group(4) == 'ON',
                'deviation': {
                    'positive':float(parsed.group(13)),
                    'negative':float(parsed.group(14))
                }
            })
        if parsed.group(11):
            relays = parsed.group(11).split('.')
            base['relay'] = [str(i) in relays for i in range(1, 13)]
        else:
            base['relay'] = [False for i in range(1, 13)]
        return base

    def parse_prgm_data_detail(self, arg):
        '''
        Parse the program data command with details flag
        '''
        parsed = re.search(
            r'([0-9.-]+),([0-9.-]+),(?:(\d+),(\d+),)?TEMP(\w+)'
            r'(?:,([0-9.-]+))?(?:,HUMI(\w+)(?:,(\d+))?)?',
            arg
        )
        ret = {
            'tempDetail':{
                'range':{'max':float(parsed.group(1)), 'min':float(parsed.group(2))},
                'mode':parsed.group(5),
                'setpoint':parsed.group(6)
            }
        }
        if parsed.group(3):
            ret['humiDetail'] = {
                'range':{'max':float(parsed.group(3)), 'min':float(parsed.group(4))},
                'mode':parsed.group(7),
                'setpoint':parsed.group(8)
            }
        return ret

    #currently not parsing the patern number on endmode run
    def parse_prgm_data(self, arg):
        '''
        Parse the program data command
        '''
        parsed = re.search(
            r'(\d+),<(.+)?>,COUNT,A\((\d+).(\d+).(\d+)\),B\((\d+).(\d+).(\d+)\),'
            r'END\(([a-zA-Z0-9:]+)\)',
            arg
        )
        return {
            'steps':int(parsed.group(1)),
            'name':parsed.group(2) if parsed.group(2) else '',
            'end':parsed.group(9) if 'RUN' not in parsed.group(9) else parsed.group(9)[:3],
            'next_prgm':int('0' if 'RUN' not in parsed.group(9) else parsed.group(9)[4:]),
            'counter_a':{
                'start':int(parsed.group(3)),
                'end':int(parsed.group(4)),
                'cycles':int(parsed.group(5))
            },
            'counter_b':{
                'start':int(parsed.group(6)),
                'end':int(parsed.group(7)),
                'cycles':int(parsed.group(8))
            }
        }

    def read_prgm(self, pgmnum, with_ptc=False):
        '''
        read an entire program helper method
        '''
        if pgmnum > 0 and pgmnum <= 40:
            pgm = self.read_prgm_data_ptc(pgmnum) if with_ptc else self.read_prgm_data(pgmnum)
            if with_ptc:
                try:
                    pgm.update(self.read_prgm_data_ptc_detail(pgmnum))
                except NotImplementedError:
                    pass #SCP-220 does not have the detail command
                tmp = [self.read_prgm_data_ptc_step(pgmnum, i) for i in range(1, pgm['steps']+1)]
            else:
                try:
                    pgm.update(self.read_prgm_data_detail(pgmnum))
                except NotImplementedError:
                    pass #SCP-220 does not have the detail command
                tmp = [self.read_prgm_data_step(pgmnum, i) for i in range(1, pgm['steps']+1)]
            pgm['steps'] = tmp
        elif pgmnum == 0:
            pgm = {
                'counter_a':{'cycles':0, 'end':0, 'start':0},
                'counter_b':{'cycles':0, 'end':0, 'start':0},
                'end':'OFF',
                'name':'',
                'next_prgm':0,
                'tempDetail':{'mode':'OFF', 'setpoint':None, 'range':self.read_temp()['range']},
                'steps':[
                    {
                        'granty':False,
                        'number':1,
                        'paused':False,
                        'refrig':{'mode':'auto', 'setpoint':0},
                        'time':{'hour':1, 'minute':0},
                        'relay':[False for i in range(12)],
                        'temperature':{'ramp':False, 'setpoint':0.0}
                    }
                ]
            }
            if with_ptc:
                pgm['steps'][0]['temperature'].update({
                    'deviation':self.read_temp_ptc()['deviation'],
                    'enable_cascade':False
                })
            try:
                pgm['humiDetail'] = {
                    'mode':'OFF',
                    'setpoint':None,
                    'range':self.read_humi()['range']
                }
                pgm['steps'][0]['humidity'] = {'enable':False, 'ramp':False, 'setpoint':0.0}
            except Exception:
                pass
        else:
            raise ValueError('pgmnum must be 0-40')
        return pgm

    def write_prgm(self, pgmnum, program):
        '''
        write an entire program helper method (must use same program format as read_prgm)
        '''
        max_write = 40 if self.ramprgms == 40 else 20 #SCP220 has 20 programs P300 40
        if pgmnum > max_write:
            raise ValueError('Program #%d is readonly and connot be saved over.' % pgmnum)
        self.write_prgm_data_edit(pgmnum, 'START')
        try:
            set_humi = False
            for num, step in enumerate(program['steps']):
                step['number'] = num+1 #ensure the step number is sequential
                self.write_prgm_data_step(pgmnum, **step)
                if step.get('humidity', {'enable':False})['enable']:
                    set_humi = True
            if not set_humi and 'humiDetail' in program:
                program['humiDetail'].pop('range', None)
            self.write_prgm_data_details(pgmnum, **program)
            self.write_prgm_data_edit(pgmnum, 'END')
        except:
            self.write_prgm_data_edit(pgmnum, 'CANCEL')
            raise

    def encode_refrig(self, mode, setpoint):
        '''
        Convert refig mode dict to string
        '''
        if mode in ['off', 'Off']:
            act = 'REF0'
        elif mode in ['auto', 'Auto']:
            act = 'REF9'
        elif mode in ['manual', 'Manual']:
            if setpoint == 0:
                act = 'REF0'
            elif setpoint == 20:
                act = 'REF1'
            elif setpoint == 50:
                act = 'REF3'
            elif setpoint == 100:
                act = 'REF6'
            else:
                raise ValueError('param "setpoint" must be one of the following: 20/50/100')
        else:
            raise ValueError('param "mode" must be: "off"/"Off"/"manual"/"Manual"/"auto"/"Auto"')
        return act

    def parse_relays(self, relays):
        '''
        handle relays
        '''
        ret = {'on':[], 'off':[]}
        for i, val in enumerate(relays):
            if val is not None:
                if isinstance(val, bool):
                    if val:
                        ret['on'].append(i+1)
                    else:
                        ret['off'].append(i+1)
                else:
                    if val['value']:
                        ret['on'].append(val['number'])
                    else:
                        ret['off'].append(val['number'])
        ret['on'] = sorted(ret['on'])
        ret['off'] = sorted(ret['off'])
        return ret

class P300vib(P300):
    '''
    This is the basic implementation for communications with the P300
    with vibration feature. 

    Most of its standard features are inherited from the superclass, standard P300.

    Args:
        interface (str): The interface type to connect to: "Serial" or "TCP"
    Kwargs:
        serialport (str/int): The serial port to connect to when interface="Serial"
        baudrate (int): The baud rate to connect at when interface="Serial"
        address (int): The RS485 address of the chamber to connect to.
        host (str): The IP address or hostname of the chamber when interface="TCP"
    '''
    def __init__(self, interface, **kwargs):
        super(P300vib, self).__init__(self, interface, **kwargs)

    def read_vib(self):
        '''
        Read and return vibration values
        '''
        rsp = self.ctlr.interact('VIB?').split(',')
        data = {
            'vibration': float(rsp[0]),
            'setpoint': float(rsp[1]),
            'upperalarmvalue': float(rsp[2]),
            'loweralarmvalue': float(rsp[3])
        }
        return data

    def read_mon(self):
        '''
        Return the chamber status and its operation modes
        '''
        rsp = self.ctlr.interact('MON?').split(',')
        data = {
            'temperature': float(rsp[0]),
            'mode': rsp[2],
            'alarms': int(rsp[3])
        }
        if rsp[1]:
            data['humidity'] = float(rsp[1])
        return data 

    def read_mon_ext(self):
        '''
        Return the chamber status and its operation modes
        '''
        rsp = self.ctlr.interact('MON?,EXT1').split(',')
        data = {
            'temperature': float(rsp[0]),
            'modes': rsp[2],
            'alarms': int(rsp[3])
        }
        if rsp[1]:
            data['vibration'] = float(rsp[1])
        return data 

    def read_mon_detail(self, constant=None):
        '''
        Return the chamber status and its operation mode
        '''
        rsp = self.ctlr.interact('MON?,DETAIL{0:s}'.format(',CONSTANT' if constant else '')).split(',') 
        data = {
            'temperature': float(rsp[0]),
            'mode': rsp[2],
            'alarms': int(rsp[3])
        }
        if rsp[1]:
            data['vibration'] = float(rsp[1])
        return data

    def read_htr(self, ext=False):
        '''
        Return the heater outputs and number of controllable heaters.
        '''
        rsp = self.ctlr.interact('%?{0:s}'.format(',EXT1' if ext else '')).split(',')
        if ext:
            data = {
                'Number of heaters': int(rsp[0]),
                'Temperature': float(rsp[1]),
                'Vibration': float(rsp[2])
            }
        else:
            if len(rsp) == 3:
                data = {
                    'Number of heaters': int(rsp[0]),
                    'Temperature': float(rsp[1]),
                    'Humidity': float(rsp[2])
                }
            else:
                data = {
                    'Number of heaters': int(rsp[0]),
                    'Temperature': float(rsp[1])
                }
        return data 

    def read_vib_constant_set(self, constant=None):
        '''
        Read vibrating status
        '''
        if constant in [1, 2, 3]:
            rsp = self.ctlr.interact('CONSTANT SET?, VIB, C{0:d}'.format(constant)).split(',')
        elif constant is None:
            rsp = self.ctlr.interact('CONSTANT SET?, VIB').split(',')
        else:
            raise ValueError("Constant must be None or 1, 2, 3.")
        return {
            'Vibration': float(rsp[0]),
            'Control Permission': rsp[1]
        }

    def read_prgm_mon(self, ext=False):
        '''
        Read status of running program

        Parameters:
            'step number': int,
            'temperature': float,
            'humidity': float,
            'vibration': float,
            'time':{'hour':int, 'minute':int},
            'counter A': int,
            'counter B': int

            Note: 'humidity' is only available on chambers having that feature.
            This means that for chambers with temperature and humidity, return 
            parameters will be six. Chambers without humidity will return 
            five parameters. Thus, two types of chambers are those with
            temperature and vibration, temperature and humidity. 
        '''
        rsp = self.ctlr.interact('PRGM MON?{0:s}'.format(',EXT1' if ext else '')).split(',')
        if exit:
            time = rsp[3].split(':')
            data = {
                'step number': int(rsp[0]),
                'temp setvalue': float(rsp[1]),
                'vibration setvalue': float(rsp[2]),
                'remaining time': {'hour': int(time[0]), 'minute':int(time[1])},
                'counter A': int(rsp[4]),
                'counter B': int(rsp[5])
            }
        elif len(rsp)==5:
            time = rsp[2].split(':')
            data = {
                'step number': int(rsp[0]),
                'temperature': float(rsp[1]),
                'remaining time': {'hour': int(time[0]), 'minute': int(time[1])},
                'counter A': int(rsp[3]),
                'counter B': int(rsp[4])
            }
        else:
            time = rsp[3].split(':')
            data = {
                'step number': int(rsp[0]),
                'temperature': float(rsp[1]),
                'humidity': float(rsp[2]),
                'remaining time': {'hour': int(time[0]), 'minute':int(time[1])},
                'counter A': int(rsp[4]),
                'counter B': int(rsp[5])               
            }
        return data  

    # NOTE: read_prgm_data, read_prgm_data_step, 
    #       read_prgm_data_detail are all inherited from the superclass P300.
    #       Only read_prgm_data that includes vibration reading (with EXT1 command)
    #       are the new def's for P300vib.
    #
    # def read_prgm_data(self, pgmnum, constant=None):
    #     pdata = self.ctlr.interact('PRGM DATA?,{0}:{1}{2}'.format(self.rom_pgm(pgmnum)))
    #     return self.parse_prgm_data(pdata)
    #
    # def read_prgm_data_step(self, pgmnum, pgmstep, ext=False):
    #     tmp = self.ctlr.interact('PRGM DATA?,{0}:{1:d},STEP{2:d}{3}'.format 
    #     (self.rom_pgm(pgmnum), pgmnum, pgmstep, ',EXT1' if ext else '')) 
    #     return self.parse_prgm_data_step(tmp) 
    #
    # def read_prgm_data_detail(self, pgmnum, ext=False):
    #     tmp = self.ctlr.interact('PRGM DATA?,{0}:{1:d},DETAIL{2}'.format 
    #     (self.rom_pgm(pgmnum), pgmnum, ',EXT1' if ext else ''))
    #    return self.parse_prgm_data_detail(tmp) 
     
    def read_prgm_data_step_ext(self, pgmnum, pgmstep):
        pdata = self.ctlr.interact('PRGM DATA?,{0}:{1:d},STEP{2:d},EXT1'.format
        (self.rom_pgm(pgmnum), pgmnum, pgmstep))
        return self.parse_prgm_data_step_ext(pdata) # need to write parse def 

    def read_prgm_data_detail_ext(self, pgmnum): 
        pdata = self.ctlr.interact('PRGM DATA?,{0}:{1:d},DETAIL,EXT1'.format 
        (self.rom_pgm(pgmnum), pgmnum)) 
        return self.parse_prgm_data_detail_ext(pdata) # need to write parse def  

    def parse_prgm_data_step_ext(self, arg):
        '''
        Parse the program parameters with vibration feature
        '''
        parsed = re.search(
            r'(\d+),TEMP([0-9.-]+),TEMP RAMP (\w+),VIB([0-9.-]+),VIB RAMP (\w+)'
            r',TIME(\d+):(\d+),GRANTY (\w+),REF(\w+)(?:,RELAY ON([0-9.]+))?,PAUSE (\w+)',
            arg
        )
        # command data and response data
        # cmd> PRGM DATA?,RAM:3,STEP3,EXT1
        # rsp> 3,TEMP30.0,TEMP RAMP ON,VIB2.5,VIB RAMP ON,TIME0:03,GRANTY OFF,REF9,RELAY ON1.2,PAUSE OFF
        #      1      2              3     4            5     6 7          8     9         10       11
        # cmd> PRGM DATA?,RAM:1,STEP1,EXT1
        # rsp> 1,TEMP25.0,TEMP RAMP ON,VIB0.0,VIB RAMP OFF,TIME1:30,GRANTY OFF,REF9,PAUSE OFF
        #      1      2              3     4            5      6  7          8    9  (10)  11
        base = {
            'number':int(parsed.group(1)),          # step number
            'time':{
                'hour':int(parsed.group(6)),        # time: hour
                'minute':int(parsed.group(7))       # time: minute
            },
            'paused':parsed.group(11) == 'ON', 'granty':parsed.group(8) == 'ON',
            'refrig':self.reflookup.get(
                'REF' + parsed.group(9),            # refrig number
                    { 'mode':'manual', 'setpoint':0 }
            ),
            'temperature':{
                'setpoint':float(parsed.group(2)),  # temp setpoint
                'ramp':parsed.group(3) == 'ON'      # ramp on
            }, 
            'vibration':{
                'setpoint':float(parsed.group(4)),  # vibration setpoint
                'ramp':parsed.group(5) == 'ON'      # vibration ramp
            }
        }
        if parsed.group(10):
            relays = parsed.group(10).split('.')
            base['relay'] = [str(i) in relays for i in range(1, 13)]
        else:
            base['relay'] = [False for i in range(1, 13)]
        return base

    def parse_prgm_data_detail_ext(self, arg):
        '''
        parse program parameters
        '''
        parsed = re.search(
            r'([0-9.-]+),([0-9.-]+),([0-9.-]+),([0-9.-]+),TEMP(\w+)'
            r'(?:,([0-9.-]+))?,VIB(\w+)(?:,([0-9.-]+))?',
            arg
        )
        # general cmd/rsp pattern: 
        # cmd> PRGM DATA?,RAM:2,DETAIL,EXT1
        # rsp> 180.0,-50.0,110.0,0.0,TEMPSV,26.0,VIBOFF
        # cmd> PRGM DATA?,RAM:3,DETAIL,EXT1
        # rsp> 180.0,-50.0,110.0,0.0,TEMPSV,26.0,VIBSV,2.5
        # cmd> PRGM DATA?,RAM:1,DETAIL,EXT1 
        # rsp> 265.0,-115.0,110.0,0.0,TEMPOFF,VIBOFF
        # cmd> PRGM DATA?,RAM:2,DETAIL,EXT1
        # rsp> 180.0,-50.0,110.0,0.0,TEMPSV,26.0,VIBOFF
        ret = {
            'tempDetail':{
                'range':{
                    'max':float(parsed.group(1)), 'min':float(parsed.group(2))
                    },
                'mode':parsed.group(5)
            },
            'vibrationDetail':{
                'range':{
                    'max':float(parsed.group(3)), 'min':float(parsed.group(4))
                },
                'mode':parsed.group(7)
            }
        }
        if parsed.group(6):
            ret['tempDetail'] = {
                'range':{
                    'max':float(parsed.group(1)), 'min':float(parsed.group(2))
                },
                'mode':parsed.group(5), 'setpoint':parsed.group(6)
            }
        if parsed.group(8):
            ret['vibrationDetail'] = {
                'range':{
                    'max':float(parsed.group(3)), 'min':float(parsed.group(4))
                },
                'mode':parsed.group(7), 'setpoint':parsed.group(8)
            }
        return ret

    def write_vib(self, constant=None, **kwargs):
        '''
        Update the vibration parameters
        '''
        setpoint, maximum, minimum = kwargs.get('setpoint'), kwargs.get('max'), kwargs.get('min')
    
        if setpoint is not None and minimum is not None and maximum is not None:
            if constant is None:
				self.ctlr.interact('VIB, S{0:0.1f} H{1:0.1f} L{2:0.1f}'.format(setpoint, maximum, minimum))				
            elif constant in [1, 2, 3]:
        
				self.ctlr.interact('VIB, S{0:0.1f} H{1:0.1f} L{2:0.1f}, C{3:d}'.format 
                        (setpoint, maximum, minimum, constant))
            else:
                raise ValueError("Constant must be None or 1, 2 or 3")
        else:
            if constant in [1, 2, 3]:
                if setpoint is not None:
                    self.ctlr.interact('VIB, S{0:0.1f}, C{1:d}'.format(setpoint, constant))

                if minimum is not None:
                    self.ctlr.interact('VIB, L{0:0.1f}, C{1:d}'.format(minimum, constant))

                if maximum is not None:
                    self.ctlr.interact('VIB, H{0:0.1f}, C{1:d}'.format(maximum, constant))

            elif constant is None:
                if setpoint is not None:
                    self.ctlr.interact('VIB, S{0:0.1f}'.format(setpoint))

                if minimum is not None:
                    self.ctlr.interact('VIB, L{0:0.1f}'.format(minimum))

                if maximum is not None:
                    self.ctlr.interact('VIB, H{0:0.1f}'.format(maximum))
            else:
                raise ValueError("Constant must be None or 1, 2 or 3")
    # program to write prgm data for vibration feature
    # written/modified: 10/19/2018
    def write_prgm_data_details(self, pgmnum, constant=None, **pgmdetail):
        '''
        write the various program wide parameters to the controller

        Args:
            pgmnum: int, the program being written or edited
            pgmdetail: the program details see write_prgmDataDetail for parameters
        '''
        if 'counter_a' in pgmdetail and pgmdetail['counter_a']['cycles'] > 0:
            ttp = (pgmnum, pgmdetail['counter_a']['start'], pgmdetail['counter_a']['end'],
                   pgmdetail['counter_a']['cycles'])
            tmp = 'PRGM DATA WRITE,PGM{0:d},COUNT,A({1:d}.{2:d}.{3:d})'.format(ttp)
            if 'counter_b' in pgmdetail and pgmdetail['counter_b']['cycles'] > 0:
                ttp = (tmp, pgmdetail['counter_b']['start'], pgmdetail['counter_b']['end'],
                       pgmdetail['counter_b']['cycles'])
                #tmp = '%s,B(%d.%d.%d)' % ttp
                tmp = '{0:s},B({1:d}.{2:d}.{3:d})'.format(ttp)
            self.ctlr.interact(tmp)
        elif 'counter_b' in pgmdetail and pgmdetail['counter_b']['cycles'] > 0:
            ttp = (pgmnum, pgmdetail['counter_b']['start'], pgmdetail['counter_b']['end'],
                   pgmdetail['counter_b']['cycles'])
            self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},COUNT,B({1:d}.{2:d}.{3:d})'.format(ttp))
        if 'name' in pgmdetail:
            self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},NAME,{1:s}'.format(pgmnum, pgmdetail['name']))
        
        # Add new parameter after program ends
        if 'end' in pgmdetail:
            if pgmdetail['end'] != 'RUN' and constant in [1,2,3]: 
                ttp = (pgmnum, '{0:s},CONSTANT{1:d}'.format(pgmdetail['end'], constant))
            elif pgmdetail['end'] != 'RUN' and constant is None:
                ttp = (pgmnum, pgmdetail['end'])     
            else:
                ttp = (pgmnum, 'RUN,PTN{0:s}'.format(pgmdetail['next_prgm']))
            self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},END,{1:s}'.format(ttp)) 

        if 'tempDetail' in pgmdetail:
            if 'range' in pgmdetail['tempDetail']:
                ttp = (pgmnum, pgmdetail['tempDetail']['range']['max'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},HTEMP,{1:0.1f}'.format(ttp))
                ttp = (pgmnum, pgmdetail['tempDetail']['range']['min'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},LTEMP,{1:0.1f}'.format(ttp))
            if 'mode' in pgmdetail['tempDetail']:
                ttp = (pgmnum, pgmdetail['tempDetail']['mode'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE MODE,TEMP,{1:s}'.format(ttp))
            if 'setpoint' in pgmdetail['tempDetail'] and pgmdetail['tempDetail']['mode'] == 'SV':
                ttp = (pgmnum, pgmdetail['tempDetail']['setpoint'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE TSV,{1:0.1f}'.format(ttp))

        if 'humiDetail' in pgmdetail:
            if 'range' in pgmdetail['humiDetail']:     
                ttp = (pgmnum, pgmdetail['humiDetail']['range']['max'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},HHUMI,{1:0.0f}'.format(ttp))
                ttp = (pgmnum, pgmdetail['humiDetail']['range']['min'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},LHUMI,{1:0.0f}'.format(ttp))
            if 'mode' in pgmdetail['humiDetail']:
                ttp = (pgmnum, pgmdetail['humiDetail']['mode'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE MODE,HUMI,{1:s}'.format(ttp))
            if 'setpoint' in pgmdetail['humiDetail'] and pgmdetail['humiDetail']['mode'] == 'SV':
                ttp = (pgmnum, pgmdetail['humiDetail']['setpoint'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE HSV,{1:0.0f}'.format(ttp)) 

        if 'vibrationDetail' in pgmdetail:
            if 'range' in pgmdetail['vibrationDetail']:
                ttp = (pgmnum, pgmdetail['vibrationDetail']['range']['max'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},HVIB,{1:0.1f}'.format(ttp))
                ttp = (pgmnum, pgmdetail['vibrationDetail']['range']['min'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},LVIB,{1:0.1f}'.format(ttp))
            if 'mode' in pgmdetail['vibrationDetail']:
                ttp = (pgmnum, pgmdetail['vibrationDetail']['mode'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE MODE,VIB,{1:s}'.format(ttp))
            if 'setpoint' in pgmdetail['vibrationDetail'] and pgmdetail['vibrationDetail']['mode'] == 'SV':
                ttp = (pgmnum, pgmdetail['vibrationDetail']['setpoint'])
                self.ctlr.interact('PRGM DATA WRITE,PGM{0:d},PRE VSV,{1:0.1f}'.format(ttp))   

    def write_prgm_data_step(self, pgmnum, **pgmstep):
        '''
        write a program step includiong vibration feature to the controller

        Args:
            pgmnum: int, the program being written/edited
            pgmstep: the program parameters, see read_prgm_data_step for parameters
        '''
        cmd = ('PRGM DATA WRITE,PGM{0:d},STEP{1:d}'.format(pgmnum, pgmstep['number']))
        if 'time' in pgmstep:
            cmd = '{0:s},TIME{1:d}:{2:d}'.format(cmd, pgmstep['time']['hour'], pgmstep['time']['minute'])
        if 'paused' in pgmstep:
            cmd = '{0:s},PAUSE {1:s}'.format(cmd, 'ON' if pgmstep['paused'] else 'OFF')
        if 'air' in pgmstep:
            cmd = '{0:s}{1:s}'.format(cmd, ',AIR3' if pgmstep['air'] else '')
        if 'refrig' in pgmstep:
            cmd = '{0:s},{1:s}'.format(cmd, self.encode_refrig(**pgmstep['refrig']))
        if 'granty' in pgmstep:
            cmd = '{0:s},GRANTY {1:s}'.format(cmd, 'ON' if pgmstep['granty'] else 'OFF')
        if 'temperature' in pgmstep:
            if 'setpoint' in pgmstep['temperature']:
                cmd = '{0:s},TEMP{1:0.1f}'.format(cmd, pgmstep['temperature']['setpoint'])
            if 'ramp' in pgmstep['temperature']:
                cmd = ('{0:s},TRAMP{1:s}'
                    .format(cmd, 'ON' if pgmstep['temperature']['ramp'] else 'OFF'))
            if 'enable_cascade' in pgmstep['temperature']:
                cmd = ('{0:s},PTC{1:s}'
                .format(cmd, 'ON' if pgmstep['temperature']['enable_cascade'] else 'OFF'))
            if 'deviation' in pgmstep['temperature']:
                ttp = (cmd, pgmstep['temperature']['deviation']['positive'],
                       pgmstep['temperature']['deviation']['negative'])
                cmd = '{0:s},DEVP{1:0.1f},DEVN{2:0.1f}'.format(ttp)
        if 'humidity' in pgmstep:
            if 'setpoint' in pgmstep['humidity']:
                if pgmstep['humidity']['enable']:
                    htmp = '{0:0.0f}'.format(pgmstep['humidity']['setpoint'])
                else:
                    htmp = 'OFF'
                cmd = '{0:s},HUMI{1:s}'.format(cmd, htmp)
            if 'ramp' in pgmstep['humidity'] and pgmstep['humidity']['enable']:
                cmd = '{0:s},HRAMP{1:s}'.format(cmd, 'ON' if pgmstep['humidity']['ramp'] else 'OFF')
        if 'vibration' in pgmstep:
            if 'setpoint' in pgmstep['vibration']:
                if pgmstep['vibration']['enable']:
                    vtmp = ('{0:0.1f}'.format(pgmstep['vibration']['setpoint']))
                else:
                    vtmp = 'OFF'
                cmd = ('{0:s},VIB{1:s}'.format(cmd, vtmp)) 
            if 'ramp' in pgmstep['vibration'] and pgmstep['vibration']['enable']:
                cmd = ('{0:s},VRAMP{1:s}'
                    .format(cmd, 'ON' if pgmstep['vibration']['ramp'] else 'OFF'))
        if 'relay' in pgmstep:
            rlys = self.parse_relays(pgmstep['relay'])
            if rlys['on']:
                cmd = '{0:s},RELAY ON{1:s}'.format(cmd, '.'.join(str(v) for v in rlys['on']))
            if rlys['off']:
                cmd = '{0:s},RELAY OFF{1:s}'.format(cmd, '.'.join(str(v) for v in rlys['off']))
        self.ctlr.interact(cmd)

    def write_prgm_erase(self, pgmnum):
        '''
        erase a program

        Args:
            pgmnum: int, the program to erase
        '''
        self.ctlr.interact('PRGM ERASE,{0:s}:{1:d}'.format(self.rom_pgm(pgmnum), pgmnum))

    def write_run_prgm(self, temp, hour, minute, gotemp=None, humi=None, gohumi=None, relays=None, constant=None):
        '''
        Run a remote program (single step program)

        Args:
            temp: float, temperature to use at the start of the step
            hour: int, # of hours to run the step
            minute: int, # of minutes to run the step
            gotemp: float, temperature to end the step at(optional for ramping)
            humi: float, the humidity to use at the start of the step (optional)
            gohumi: float, the humidity to end the step at (optional for ramping)
            relays: [boolean], True= turn relay on, False=turn relay off, None=Do nothing
            air: int, # of air speed to provide to system to operate
        '''
        cmd = 'RUN PRGM, TEMP{0:0.1f} TIME{1:d}:{2:d}'.format(temp, hour, minute)
        if gotemp is not None:
            cmd = '{0:s} GOTEMP{1:0.1f}'.format(cmd, gotemp)
        if humi is not None:
            cmd = '{0:s} HUMI{1:0.0f}'.format(cmd, humi)
        if gohumi is not None:
            cmd = '{0:s} GOHUMI{1:0.0f}'.format(cmd, gohumi)
        rlys = self.parse_relays(relays) if relays is not None else {'on':None, 'off':None}
        if rlys['on']:
            cmd = '{0:s} RELAYON,{1:s}'.format(cmd, ','.join(str(v) for v in rlys['on']))
        if rlys['off']:
            cmd = '{0:s} RELAYOFF,{1:s}'.format(cmd, ','.join(str(v) for v in rlys['off'])) 
        if constant is not None: 
            cmd = '{0:s} AIR{1:d}'.format(cmd, constant)

        self.ctlr.interact(cmd)
    # NOTE: The following data commands for vibration are null:
    # PRGM DATA ERASE, RUN PRGM, PRGM SET?, PRGM USE?, and PRGM DATA PTC?
    #
    #def write_temp_ptc(self, enable, positive, negative):
    #    '''
    #    set product temperature control settings
    #    Args:
    #        enable: boolean, True(on)/False(off)
    #        positive: float, maximum positive deviation
    #        negative: float, maximum negative deviation
    #    '''
    #    ttp = ('ON' if enable else 'OFF', positive, negative)
    #    self.ctlr.interact('TEMP PTC,PTC{0:s},DEVP{1:0.1f},DEVN{2:0.1f}'.format(ttp)
    
    #def write_ptc(self, op_range, pid_p, pid_filter, pid_i, **kwargs):
    #    '''
    #    write product temp control parameters to controller
    #
    #    Args:
    #        range: {"max":float,"min":float}, allowable range of operation
    #        p: float, P parameter of PID
    #        i: float, I parameter of PID
    #        filter: float, filter value
    #        opt1,opt2 not used set to 0.0
    #    '''
    #    opt1, opt2 = kwargs.get('opt1', 0), kwargs.get('opt2', 0)
    #    ttp = (op_range['max'], op_range['min'], pid_p, pid_filter, pid_i, opt1, opt2)
    #    self.ctlr.interact('PTC,{0:0.1f},{1:0.1f},{2:0.1f},{3:0.1f},{4:0.1f},{5:0.1f},{6:0.1f}'.format(ttp))
    
    #def write_ip_set(self, address, mask, gateway):
    #    '''
    #    Write the IP address configuration to the controller
    #    '''
    #    self.ctlr.interact('IPSET,{0:s},{1:s},{2:s}'.format(address, mask, gateway))
