import pandas as pd
import numpy as np

from dataAccuPatt import DataAccuPatt
from seriesData import SeriesData
from passData import Pass

class FileTools:

    def load_from_accupatt_1_file(file):
        #Load in the file
        data = DataAccuPatt(file)
        data.readFromFile()
        #get dataframes for each sheet
        dFlyin = data.getFlyinData()
        dAircraft = data.getAircraftData()
        dSeries = data.getSeriesData()
        dPatternInfo = data.getPatternInfo()
        dPatternData = data.getPatternData()
        dExcitationData = data.getExcitationData()
        #initialize SeriesData object to store all info
        s = SeriesData()
        #Pull *Applicator Info* data from AppInfo Tab
        s.info.pilot = dAircraft.at[0,'Value']
        s.info.business = dAircraft.at[1,'Value']
        s.info.street = dAircraft.at[3,'Value']
        s.info.city = dAircraft.at[4,'Value']
        s.info.state = dAircraft.at[5,'Value']
        s.info.zip = dAircraft.at[6,'Value']
        s.info.phone = dAircraft.at[2,'Value']
        s.info.email = dAircraft.at[7,'Value']
        #Pull *Aircraft* data from AppInfo Tab
        s.info.regnum = dAircraft.at[8,'Value']
        s.info.series = dAircraft.at[9,'Value']
        s.info.make = dAircraft.at[10,'Value']
        s.info.model = dAircraft.at[11,'Value']
        s.info.set_wingspan(dAircraft.at[25,'Value'])
        s.info.winglets = dAircraft.at[30,'Value']
        #Pull *Spray System* data from AppInfo Tab
        s.info.set_swath(string=dAircraft.at[22,'Value'])
        s.info.set_swath_adjusted(string=dAircraft.at[23,'Value'])
        s.info.set_rate(string=dAircraft.at[21,'Value'])
        s.info.set_pressure(string=dAircraft.at[20,'Value'])
        s.info.nozzle_type_1 = dAircraft.at[12,'Value']
        s.info.set_nozzle_size_1(string=dAircraft.at[14,'Value'])
        s.info.set_nozzle_deflection_1(string=dAircraft.at[15,'Value'])
        s.info.set_nozzle_quantity_1(string=dAircraft.at[13,'Value'])
        s.info.nozzle_type_2 = dAircraft.at[16,'Value']
        s.info.set_nozzle_size_2(string=dAircraft.at[18,'Value'])
        s.info.set_nozzle_deflection_2(string=dAircraft.at[19,'Value'])
        s.info.set_nozzle_quantity_2(string=dAircraft.at[17,'Value'])
        s.info.set_boom_width(string=dAircraft.at[26,'Value'])
        s.info.set_boom_drop(string=dAircraft.at[28,'Value'])
        s.info.set_nozzle_spacing(string=dAircraft.at[29,'Value'])
        if dAircraft.at[32,'Value'] == 'False':
            #Non-Metric
            s.info.swath_units = 'ft'
            s.info.rate_units = 'gpa'
            s.info.pressure_units = 'psi'
            s.info.wingspan_units = 'ft'
            s.info.boom_width_units = 'ft'
            s.info.boom_drop_units = 'in'
            s.info.nozzle_spacing_units = 'in'

        else:
            #Metric
            s.info.swath_units = 'm'
            s.info.rate_units = 'l/ha'
            s.info.pressure_units = 'bar'
            s.info.wingspan_units = 'm'
            s.info.boom_width_units = 'm'
            s.info.boom_drop_units = 'cm'
            s.info.nozzle_spacing_units = 'cm'

        #Clear any stored individual passes
        s.passes.clear()
        #Search for any active passes and create entries in seriesData.passes dict
        for c in dSeries.columns[1:]:
            n = str(c)
            if not str(dSeries.at[1,n]) == '':
                p = Pass(name=n)
                p.ground_speed = float(dSeries.at[1,n])
                p.ground_speed_units='mph'
                p.spray_height=float(dSeries.at[2,n])
                p.spray_height_units='ft'
                p.pass_heading=int(dSeries.at[3,n])
                p.wind_direction=int(dSeries.at[4,n])
                p.wind_speed=float(dSeries.at[5,n])
                p.wind_speed_units='mph'
                p.temperature = int(dSeries.at[6,'Pass 1'])
                p.temperature_units = '°F'
                p.humidity = int(dSeries.at[7,'Pass 1'])

                s.passes[n] = p

        #Pull patterns and place them into seriesData.passes dicts by name (created above)
        for column_name in dPatternInfo:
            if str(dPatternInfo.at[3,column_name]) != 'nan':
                name = column_name
                if name in s.passes.keys():
                    p = s.passes[name]
                else:
                    #If pass not created from series data, make one here
                    p = Pass(name=name)
                p.trimL = dPatternInfo.at[0,column_name]
                p.trimR = dPatternInfo.at[1,column_name]
                p.trimV = dPatternInfo.at[2,column_name]
                p.data = dPatternData[['loc',column_name]]
                p.data_ex = dExcitationData[['loc',column_name]]

                s.passes[name] = p

        return s
