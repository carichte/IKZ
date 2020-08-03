import collections
import xrayutilities as xu


class EmptyGeometry(object):
    """
        Abstract container for diffractometer angles
    """
    sample_rot = collections.OrderedDict()
    detector_rot = collections.OrderedDict()
    offsets = collections.defaultdict(float)
    
    # defines whether these motors are used. otherwise set to zero.
    usemotors = set()
    
    inc_beam = [1,0,0]
    
    def __init__(self, **kwargs):
        """
            Initialize diffractometer geomtry.
            
            Inputs: all motor names from self.sample_rot and self.detector_rot
                True  -- use motor
                False -- discard
        """
        usemotors = self.usemotors
        for motor in kwargs:
            usemotors.add(motor) if kwargs[motor] else usemotors.discard(motor)
        
    def getQconversion(self, inc_beam = None):
        if inc_beam is None:
            inc_beam = self.inc_beam

        sample_ax = [ax for (mot, ax) in self.sample_rot.items() if mot in self.usemotors]
        detector_ax = [ax for (mot, ax) in self.detector_rot.items() if mot in self.usemotors]

        qc = xu.experiment.QConversion(sample_ax, detector_ax, inc_beam)
        return qc
    
    def set_offsets(self, **kwargs):
        """
            Set offset for each motor to be subtracted from its position.
            Motors identified by keyword arguments.
        """
        for kw in kwargs:
            if kw in self.sample_rot or kw in self.detector_rot:
                self.offsets[kw] = float(kwargs[kw])


class P08kohzu(EmptyGeometry):
    def __init__(self, **kwargs):
        ### geometry of ID01 diffractometer
        ### x downstream; z upwards; y to the "outside" (righthanded)
        ### the order matters!
        self.sample_rot['omh'] = 'z+' # check mu is not 0
        self.sample_rot['om'] = 'y+'
        self.sample_rot['chi'] = 'x+'
        self.sample_rot['phis'] = 'z+'
        self.sample_rot['goni1'] = 'y+'
        self.sample_rot['goni2'] = 'x+'
        
        self.detector_rot['tth'] = 'z+'
        self.detector_rot['tt'] = 'y+'
        
        self.inc_beam = [-1,0,0]
        
        # defines whether these motors are used. otherwise set to zero
        #   typical defaults, can be overridden during __init__:
        self.usemotors = set(('om', 'chi', 'phis', 'tth', 'tt'))
        super(P08kohzu, self).__init__(**kwargs)



class ID01psic(EmptyGeometry):
    def __init__(self, **kwargs):
        ### geometry of ID01 diffractometer
        ### x downstream; z upwards; y to the "outside" (righthanded)
        ### the order matters!
        self.sample_rot['mu'] = 'z-' # check mu is not 0
        self.sample_rot['eta'] = 'y-'
        self.sample_rot['phi'] = 'z-'
        self.sample_rot['rhx'] = 'y+'
        self.sample_rot['rhy'] = 'x-'
        self.sample_rot['rhz'] = 'z+'
    
        self.detector_rot['nu'] = 'z-'
        self.detector_rot['delta'] = 'y-'
        
        self.inc_beam = [1,0,0]
        
        # defines whether these motors are used. otherwise set to zero
        #   typical defaults, can be overridden during __init__:
        self.usemotors = set(('eta', 'phi', 'nu', 'delta'))
        super(ID01psic, self).__init__(**kwargs)


class P23SixC(EmptyGeometry):
    def __init__(self, **kwargs):
        ### geometry of diffractometer
        ### x downstream; z upwards; y to the "outside" (righthanded)
        ### maintain the correct order: outer to inner rotation!
        self.sample_rot['omega_t'] = 'y-' # check mu is not 0
        self.sample_rot['mu'] = 'z-' # check mu is not 0
        self.sample_rot['omega'] = 'y-'
        self.sample_rot['chi'] = 'x-'
        self.sample_rot['phi'] = 'y+'

        self.detector_rot['gamma'] = 'z-'
        self.detector_rot['delta'] = 'y-'

        self.inc_beam = [1,0,0]

        # defines whether these motors are used. otherwise set to zero
        #   typical defaults, can be overridden during __init__:
        self.usemotors = set(('omega', 'chi', 'phi', 'gamma', 'delta'))
        super(P23SixC, self).__init__(**kwargs)

class SmartLab(EmptyGeometry):
    def __init__(self, **kwargs):
        ### geometry of ID01 diffractometer
        ### x downstream; z upwards; y to the "outside" (righthanded)
        ### the order matters!
        self.sample_rot['omega'] = 'y-'
        self.sample_rot['chi'] = 'x-' # cross check 
        self.sample_rot['phi'] = 'z-'
    
        self.detector_rot['tth'] = 'y-'
        
        self.inc_beam = [1,0,0]
        
        # defines whether these motors are used. otherwise set to zero
        #   typical defaults, can be overridden during __init__:
        self.usemotors = set(('omega', 'phi', 'tth'))
        super(SmartLab, self).__init__(**kwargs)
    
