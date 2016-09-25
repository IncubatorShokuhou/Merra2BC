import pathes
import re
import os
from netCDF4 import Dataset
import numpy as np

met_files=[]
met_times_files={}
wrf_times={}

spec_number=0
nx=ny=nz=nw=0
wrf_p_top=0
znu=[]
xlon=[[]]
xlat=[[]]

wrf_vars=[]

wrfbxs_o=[[[[]]]]
wrfbxe_o=[[[[]]]]
wrfbys_o=[[[[]]]]
wrfbye_o=[[[[]]]]

wrf_lons=[]
wrf_lats=[]

def get_pressure_from_metfile(metfile):
    PSFC=metfile.variables['PSFC'][:]
    WRF_Pres = np.zeros([nz,ny,nx])
    for z_level in reversed(range(nz)):
        WRF_Pres[nz-1-z_level,:]=PSFC*znu[0,z_level]+ (1.0 - znu[0,z_level])*wrf_p_top
    return WRF_Pres

def get_sfcp_from_met_file(filename):
    metfile= Dataset(pathes.wrf_met_dir+"/"+filename,'r')
    PSFC=metfile.variables['PSFC'][:]
    metfile.close()
    return PSFC

def get_met_file_by_time(time):
    return met_times_files.get(time)

def get_index_in_file_by_time(time):
    return wrf_times.get(time)


numbers = re.compile(r'(\d+)')
def numericalSort1(value):
    parts = numbers.split(value)
    return int(float(parts[3])*1e6+float(parts[5])*1e4+float(parts[7])*1e2+float(parts[9]))


def get_ordered_met_files():
    return met_files


def update_boundaries(WRF_SPECIE_BND,wrfbdy_f,name,index):
    WRF_SPECIE_LEFT_BND  =WRF_SPECIE_BND[:,0:ny]
    WRF_SPECIE_TOP_BND   =WRF_SPECIE_BND[:,ny:ny+nx]
    WRF_SPECIE_RIGHT_BND =WRF_SPECIE_BND[:,ny+nx:2*ny+nx]
    WRF_SPECIE_BOT_BND   =WRF_SPECIE_BND[:,2*ny+nx:2*ny+2*nx]

    wrfbxs=np.repeat(WRF_SPECIE_LEFT_BND[np.newaxis,:,:], nw, axis=0)
    wrfbxe=np.repeat(WRF_SPECIE_RIGHT_BND[np.newaxis,:,:], nw, axis=0)
    wrfbys=np.repeat(WRF_SPECIE_BOT_BND[np.newaxis,:,:], nw, axis=0)
    wrfbye=np.repeat(WRF_SPECIE_TOP_BND[np.newaxis,:,:], nw, axis=0)


    print "\t\t\tUpdating BC for "+name
    wrfbdy_f.variables[name+"_BXS"][index,:]=wrfbdy_f.variables[name+"_BXS"][index,:]+wrfbxs
    wrfbdy_f.variables[name+"_BXE"][index,:]=wrfbdy_f.variables[name+"_BXE"][index,:]+wrfbxe
    wrfbdy_f.variables[name+"_BYS"][index,:]=wrfbdy_f.variables[name+"_BYS"][index,:]+wrfbys
    wrfbdy_f.variables[name+"_BYE"][index,:]=wrfbdy_f.variables[name+"_BYE"][index,:]+wrfbye


def update_tendency_boundaries(wrfbdy_f,name,index,dt,wrf_sp_index):
    global wrfbxs_o,wrfbxe_o,wrfbys_o,wrfbye_o

    if(index>0):
        print "\t\t\tUpdating Tendency BC for "+name
        wrfbdy_f.variables[name+"_BTXS"][index-1,:]=(wrfbdy_f.variables[name+"_BXS"][index,:]-wrfbxs_o[wrf_sp_index,:])/dt
        wrfbdy_f.variables[name+"_BTXE"][index-1,:]=(wrfbdy_f.variables[name+"_BXE"][index,:]-wrfbxe_o[wrf_sp_index,:])/dt
        wrfbdy_f.variables[name+"_BTYS"][index-1,:]=(wrfbdy_f.variables[name+"_BYS"][index,:]-wrfbys_o[wrf_sp_index,:])/dt
        wrfbdy_f.variables[name+"_BTYE"][index-1,:]=(wrfbdy_f.variables[name+"_BYE"][index,:]-wrfbye_o[wrf_sp_index,:])/dt

    wrfbxs_o[wrf_sp_index,:]=wrfbdy_f.variables[name+"_BXS"][index,:]
    wrfbxe_o[wrf_sp_index,:]=wrfbdy_f.variables[name+"_BXE"][index,:]
    wrfbys_o[wrf_sp_index,:]=wrfbdy_f.variables[name+"_BYS"][index,:]
    wrfbye_o[wrf_sp_index,:]=wrfbdy_f.variables[name+"_BYE"][index,:]



def initialise():
    global met_files,wrf_times,wrf_p_top,znu,xlon,xlat,nx,ny,nz,nw,wrf_lons,wrf_lats,spec_number,wrf_vars,wrfbxs_o,wrfbxe_o,wrfbys_o,wrfbye_o

    met_files=sorted([f for f in os.listdir(pathes.wrf_dir) if re.match(pathes.wrf_met_files, f)], key=numericalSort1)
    wrfbddy = Dataset(pathes.wrf_dir+"/"+pathes.wrf_bdy_file,'r')
    for i in range(0,len(wrfbddy.variables['Times'][:]),1):
        wrf_times.update({''.join(wrfbddy.variables['Times'][i]):i})
        met_times_files.update({''.join(wrfbddy.variables['Times'][i]):met_files[i]})

    nx=wrfbddy.dimensions['west_east'].size
    ny=wrfbddy.dimensions['south_north'].size
    nz=wrfbddy.dimensions['bottom_top'].size
    print "\nWRF dimensions: [bottom_top]="+str(nz)+" [south_north]="+str(ny)+" [west_east]="+str(nx)

    nw=wrfbddy.dimensions['bdy_width'].size
    wrfbddy.close()

    #Reading "PRESSURE TOP OF THE MODEL, PA" and "eta values on half (mass) levels"
    wrfinput=Dataset(pathes.wrf_dir+"/"+pathes.wrf_input_file,'r')
    wrf_p_top=wrfinput.variables['P_TOP'][:]
    znu=wrfinput.variables['ZNU'][:]
    xlon=wrfinput.variables['XLONG'][0,:]
    xlat=wrfinput.variables['XLAT'][0,:]
    wrf_vars=[var for var in wrfinput.variables]
    wrfinput.close()

    wrf_lons=np.concatenate((xlon[:,0],xlon[ny-1,:],xlon[:,nx-1],xlon[0,:]), axis=0)
    wrf_lats=np.concatenate((xlat[:,0],xlat[ny-1,:],xlat[:,nx-1],xlat[0,:]), axis=0)

    print "Lower left corner: lat="+str(min(wrf_lats))+" long="+str(min(wrf_lons))
    print "Upper right corner: lat="+str(max(wrf_lats))+" long="+str(max(wrf_lons))


    spec_number=len(pathes.spc_map)

    wrfbxs_o=np.zeros((spec_number,nw,nz,ny))
    wrfbxe_o=np.zeros((spec_number,nw,nz,ny))
    wrfbys_o=np.zeros((spec_number,nw,nz,nx))
    wrfbye_o=np.zeros((spec_number,nw,nz,nx))
