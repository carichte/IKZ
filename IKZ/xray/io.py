# -*- coding: utf-8 -*-


from __future__ import print_function
import zipfile
import os
import xml.etree.ElementTree as ET
import xmltodict
import collections
import numpy as np
import time
import locale

from io import BytesIO, StringIO

def try_scalar(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    try:
        return float(val)
    except (ValueError, TypeError):
        pass
    return val


def parse_rasx_metadata(xml):
    mdata = dict()
    #xml.seek(0)
    tree = ET.parse(xml)
    measurement = tree.getroot()

    for group in ["GeneralInformation", "ScanInformation", "SampleInformation", "RSMInformation"]:
        groupobj = measurement.find(group)
        if groupobj is None:
            continue
        mdata[group] = dict((info.tag, try_scalar(info.text)) for info in groupobj)



    hwdict = mdata["HardwareConfig"] = dict()
    hwconf = measurement.find("HWConfigurations")

    optics = hwdict["optics"] = dict()
    for category in hwconf.find("Categories"):
        optics[category.attrib["Name"]] = category.attrib["SelectedUnit"]
    optics["Monochromator"] = [child.text for child in hwconf.find("Optics")]
    hwdict["Detector"] = optics["Detector"]


    distances = hwdict["distances"] = []
    
    ## python >= 3.7:
    #Distance = collections.namedtuple("Distance", ("To", "From", "Unit", "Value"), defaults=4*[None])
    ## python < 3.7:
    Distance = collections.namedtuple('Distance', ("To", "From", "Unit", "Value"))
    Distance.__new__.__defaults__ = (None,) * len(Distance._fields)

    for distance in hwconf.find("Distances"):
        attrib = distance.attrib.copy()
        attrib["Value"] = try_scalar(attrib["Value"])
        distances.append(Distance(**attrib))



    hwdict["xraygenerator"] = dict((info.tag, try_scalar(info.text)) for info in hwconf.find("XrayGenerator"))


    header = mdata["RASHeader"] = dict()
    axtitle = dict()
    for info in measurement.find("RASHeader"):
        pair = list(info)
        key = pair[0].text
        if "MEAS_COND_AXIS_NAME" in key:
            num = int(key.rsplit("-", 1)[1])
            axtitle[num] = pair[1].text
        else:
            header[key] = pair[1].text

    ## python >= 3.7:
    #Axis = collections.namedtuple("Axis",
    #                              ("Name", "Unit", "Offset", "Position", "Description"),
    #                              defaults=5*[None])
    ## python < 3.7:
    Axis = collections.namedtuple('Axis', ("Name", "Unit", "Offset", "Position", "EndPosition", "Description", "State", "Resolution"))
    Axis.__new__.__defaults__ = (None,) * len(Axis._fields)

    axes = mdata["Axes"] = collections.OrderedDict()
    for i, axis in enumerate(measurement.find("Axes")):
        attrib = axis.attrib.copy()
        attrib["Description"] = axtitle[i]
        for key in ("Offset", "Position"):
            attrib[key] = try_scalar(attrib.get(key))
        axes[axis.attrib["Name"]] = Axis(**attrib)

        
    return mdata


class RASXfile(object):
    def __init__(self, path, verbose=True):
        with zipfile.ZipFile(path) as fh:
            profiles = [f.filename for f in fh.filelist if "Profile" in f.filename]
            numscans = len(profiles)
            data = []
            meta = []
            for i in range(numscans):
                if verbose and not i:
                    print("Loading profile %i"%i, end="")
                if verbose and i:
                    print(", %i"%i, end="")
                profile = profiles[i]
                metafile = profile.replace("Profile", "MesurementConditions")
                metafile = metafile[:-4] + ".xml"
                #print(fname)
                with fh.open(profile) as f:
                    ## python >= 3.7:
                    #f.seek(3) # skip the 3 non-ascii symbols at the start
                    #data.append(np.loadtxt(f))
                    ## the ugly way to stay python < 3.7 compatible:
                    _content = BytesIO(f.read()[3:])
                    data.append(np.loadtxt(_content))
                with fh.open(metafile) as xml:
                    meta.append(parse_rasx_metadata(xml))

            images = [f.filename for f in fh.filelist if "Image" in f.filename]
            numimg = len(images)
            imgdata = []
            for i in range(numimg):
                if verbose and not i:
                    print("Loading frame %i"%i, end="")
                if verbose and i:
                    print(", %i"%i, end="")
                imgpath = images[i]
                metafile = imgpath.replace("Image", "MesurementConditions")
                metafile = metafile[:-4] + ".xml"
                #print(fname)
                
                with fh.open(imgpath) as f:
                    imgarr = np.fromstring(f.read(), dtype=np.uint32)
                    imgarr.resize(385, 775) # for now only Hypix3000
                    imgdata.append(imgarr)
                with fh.open(metafile) as xml:
                    meta.append(parse_rasx_metadata(xml))

            if verbose:
                print()

        self.data = np.stack(data) if data else []
        self.images = np.stack(imgdata) if imgdata else []
        self._meta = meta
        self.positions = collections.defaultdict(list)
        for mdata in meta:
            for axis in mdata["Axes"].values():
                self.positions[axis.Name].append(axis.Position)
        for axis in self.positions:
            if len(set(self.positions[axis])) == 1:
                self.positions[axis] = self.positions[axis][0]
            else:
                self.positions[axis] = np.array(self.positions[axis])

    def get_RSM(self):
        tth, I, _ = self.data.transpose(2,0,1).squeeze()
        output = dict(TwoTheta=tth, Intensity=I)
        for axis in ["Omega", "Chi", "Phi"]:
            axdata = self.positions[axis]
            if np.ndim(axdata):
                axdata = axdata[:,None] * np.ones_like(I)
            output[axis] = axdata

        return output


class BRMLfile(object):
    def __init__(self, path, exp_nbr=0, encoding="utf-8", verbose=True):
        self.path = path
        with zipfile.ZipFile(path, 'r') as fh:
            experiment = "Experiment%i"%exp_nbr
            datacontainer = "%s/DataContainer.xml"%experiment
            
            with fh.open(datacontainer, "r") as xml:
                data = xmltodict.parse(xml.read(), encoding=encoding)
            rawlist = data["DataContainer"]["RawDataReferenceList"]["string"]
            if not isinstance(rawlist, list):
                rawlist = [rawlist]

            self.data = collections.defaultdict(list)
            self.motors = self.data # collections.defaultdict(list)
            for i, rawpath in enumerate(rawlist):
                if verbose:
                    if not i:
                        print("Loading frame %i"%i, end="")
                    else:
                        print(", %i"%i, end="")
                with fh.open(rawpath, "r") as xml:
                    data = xmltodict.parse(xml.read(), encoding=encoding)
                dataroute = data["RawData"]["DataRoutes"]["DataRoute"]
                scaninfo = dataroute["ScanInformation"]
                nsteps = int(scaninfo["MeasurementPoints"])
                if nsteps==1:
                    rawdata = np.array(dataroute["Datum"].split(","))
                elif nsteps>1:
                    rawdata = np.array([d.split(",") for d in dataroute["Datum"]])

                rawdata = rawdata.astype(float).T
                rdv = dataroute["DataViews"]["RawDataView"]
                for view in rdv:
                    viewtype = view["@xsi:type"]
                    vstart = int(view["@Start"])
                    vlen = int(view["@Length"])
                    if viewtype=="FixedRawDataView":
                        vname = view["@LogicName"]
                        self.data[vname].append(rawdata[vstart:(vstart+vlen)])
                    elif viewtype=="RecordedRawDataView":
                        vname = view["Recording"]["@LogicName"]
                        self.data[vname].append(rawdata[vstart:(vstart+vlen)])
                        
                self.data["ScanName"].append(scaninfo["@ScanName"])
                self.data["TimePerStep"].append(scaninfo["TimePerStep"])
                self.data["TimePerStepEffective"].append(scaninfo["TimePerStepEffective"])
                self.data["ScanMode"].append(scaninfo["ScanMode"])
                
                scanaxes = scaninfo["ScanAxes"]["ScanAxisInfo"]
                if not isinstance(scanaxes, list):
                    scanaxes = [scanaxes]
                for axis in scanaxes:
                    aname = axis["@AxisName"]
                    aunit = axis["Unit"]["@Base"]
                    aref = float(axis["Reference"])
                    astart = float(axis["Start"]) + aref
                    astop = float(axis["Stop"]) + aref
                    astep = float(axis["Increment"])
                    nint = int(round(abs(astop-astart)/astep))
                    self.data[aname].append(np.linspace(astart, astop, nint+1))

                drives = data["RawData"]["FixedInformation"]["Drives"]["InfoData"]
                for axis in drives:
                    aname = axis["@LogicName"]
                    apos = float(axis["Position"]["@Value"])
                    self.motors[aname].append(apos)
            
            
            for key in self.data:
                self.data[key] = np.array(self.data[key]).squeeze()
                if not self.data[key].shape:
                    self.data[key] = self.data[key].item()
            for key in self.motors:
                self.motors[key] = np.array(self.motors[key]).squeeze()
                if not self.motors[key].shape:
                    self.motors[key] = self.motors[key].item()





class FIOdata(object):
    """ 
        This class handles measurement data files that are present in
        the .fio format which is produced at the DESY Photon Science
        Instruments.
    """
    def __init__(self, FILENAME, verbose=False):
        """
            This opens a .fio file using a path to the file or a file
            handle. If verbose is True, additional information is printed.
            
            After initialization the following objects are available:
            .name       - name of measurement
            .repeats    - number of repeat
            .parameters - dictionary of motor positions
            .colname    - list of columns names
            .comment    - comment string
            .data       - numpy array of measured data
            .startsec   - unix time of measurement start
            .stopsec    - unix time of measurement stop
            .starttime  - struct_time of measurement start
            .stoptime   - struct_time of measurement stop
            
            Methods:
            .normalize  - method to normalize all columns onto a selected one
            .to_dat     - convert to .dat format (columns with 1 header line)
        """
        if isinstance(FILENAME, str):
            if verbose: print("Loading %s"%FILENAME)
            data=open(FILENAME, "r")
        elif hasattr(FILENAME, "readline"):
            if verbose: print("Loading %s"%FILENAME.name)
            data = FILENAME
        else: raise ValueError('fname must be a string or file handle')
        
        self.comment=""
        self.parameters={}
        colname=[]
        self.repeats = 1
        #self.data=np.array([])
        flag = True
        while flag:
            line = data.readline()
            if not line: break
            if not line.find("!"):
                continue
            if "%c" in line:
                line = data.readline()
                while not line.startswith("!"):
                    if not line: break
                    self.comment+=line
                    line = data.readline()
            if "%p" in line:
                line = data.readline()
                while not ("! Data" in line):
                    if line.startswith("!"): 
                        line = data.readline()
                        continue
                    elif not line: break
                    line=line.replace(" ","")
                    [param, value]=line.split("=")
                    try:
                        value = float(value)
                    except:
                        pass
                    self.parameters[param] = value
                    line = data.readline()
            if "%d" in line:
                line = data.readline()
                while not line.startswith("!"):
                    if not line: break
                    if "Col" in line:
                        colname.append(line.split()[2])
                    else: 
                        flag = False
                        break
                    line = data.readline()
        numdata = StringIO(line + data.read())
        data.close()
        self.data=np.genfromtxt(numdata, comments="!")
        i=0
        cond = True
        if len(colname)<=1:
            self.name = colname[0]
            self.colname = colname
        else:
            while cond:
                i+=1
                for name in colname:
                    cond *= (name[:i]==colname[0][:i])
            self.name = colname[0][:(i-2)]
            for j in range(len(colname)):
                colname[j] = colname[j][(i-1):]
            self.colname = colname
        
        words = self.comment.split()
        
        if "sampling" in words:
            ind = words.index("sampling")
            self.sampletime = float(words[ind+1])
        try:
            i1 = words.index("ended")
            day = words[i1-2]
            time0 = words[i1-1][:-1]
            timeE = words[i1+1]
            orglocal = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, ("en","UTF8"))
            self.starttime = time.strptime(day + time0, "%d-%b-%Y%H:%M:%S")
            self.stoptime = time.strptime(day + timeE, "%d-%b-%Y%H:%M:%S")
            locale.setlocale(locale.LC_TIME, orglocal)
            self.startsec = time.mktime(self.starttime)
            self.stopsec = time.mktime(self.stoptime)
        except Exception as err:
            print("Warning: starting or stopping time of scan could not be",
                  "determined: ", err)
            self.starttime = np.nan
            self.stoptime = np.nan
            self.startsec = np.nan
            self.stopsec = np.nan
        
    def __len__(self):
        return self.data.__len__()
    
    def __getitem__(self, indices):
        """
            Rewritten to handle columns names in FIOdata.colname
        """
        if isinstance(indices, str) and indices in self.colname:
            return self.data[:,self.colname.index(indices)]
        else:
            return self.data[indices]
    def __repr__(self):
        return self.comment
    def parameters_nice(self, format="%.4g"):
        """
            This function just returns a string containing the motor position
            and further parameters as they were during the measurement.
            It is preformatted in a well readable way.
            The ``format`` of the floating point numbers  can be specified
            using the common string formatting presentation types.
            
            The bare information is located in the FIOdata.parameters
            dictionary.
        """
        s=""
        p = self.parameters
        length = max([len(key) + len(format%val) 
                      for (key,val) in p.items()])
        length += 2
        for key in sorted(p):
            s += key + (length-len(key)-len(format%(p[key]))) * " " \
                     +  format%(p[key]) + os.linesep
        
        
        
        return s
    def normalize(self, col):
        """
            Normalizes all columns to a column specified by ``col`` and
            deletes column ``col``
        """
        if col in self.colname:
            col = self.colname.index(col)
        else:
            try: col = int(col)
            except:
                collow = map(str.lower, self.colname)
                thiscol = filter(lambda s: col.lower() in s, collow)
                col = collow.index(thiscol[0])
        for i in range(len(self.colname)):
            if i !=col and i!=0:
                self.data[:,i] /= self.data[:,col]
        ind = np.ones(len(self.colname)).astype(bool)
        ind[col]=False
        self.data = self.data[:,ind]
        self.colname.pop(col)
    def to_dat(self, FILENAME=None, delimiter=" ", fmt="%.18e"):
        """
            Translates the FIOdata.data into numpy`s default columned data
            string format plus 1 header line and stores it into the file 
            ``FILENAME`` or returns it as string.
        """
        output = delimiter.join(self.colname) + "\n"
        outfile = StringIO()
        np.savetxt(outfile, self.data, fmt, delimiter)
        output += outfile.getvalue()
        outfile.close()
        if FILENAME == None: return output
        else: 
            fh = open(FILENAME, "w")
            fh.write(output)
            fh.close()




