"""
AtomicCoordinationConstraints contains classes for all constraints related to coordination numbers in shells around atoms.

.. inheritance-diagram:: fullrmc.Constraints.AtomicCoordinationConstraints
    :parts: 1
    
"""

# standard libraries imports
import itertools
import copy

# external libraries imports
import numpy as np

# fullrmc imports
from fullrmc.Globals import INT_TYPE, FLOAT_TYPE, PI, PRECISION, FLOAT_PLUS_INFINITY, LOGGER
from fullrmc.Core.Collection import is_number, is_integer
from fullrmc.Core.Constraint import Constraint, SingularConstraint, RigidConstraint
from fullrmc.Core.atomic_coordination import all_atoms_coord_number_coords, multi_atoms_coord_number_coords


class AtomicCoordinationNumberConstraint(RigidConstraint, SingularConstraint):
    """
    It's a rigid constraint that controls the coordination number between atoms. 
    
    .. raw:: html

        <iframe width="560" height="315" 
        src="https://www.youtube.com/embed/R8t-_XwizOI?rel=0" 
        frameborder="0" allowfullscreen>
        </iframe>
        
        
    :Parameters:
        #. coordNumDef (None, list, tuple): The coordination number definition. 
           It must be None or a list or tuple where every element is a list or a
           tuple of exactly 6 items and an optional 7th item for weight.
           
           #. the core atoms: Can be any of the following:
           
              * string: indicating atomic element
              * dictionary: Key an atomic attribute among (element, name) 
                and value is the attribute value.
              * list, tuple, set, numpy.ndarray: core atoms indexes  
           
           #. the in shell atoms: Can be any of the following:
           
              * string: indicating atomic element
              * dictionary: Key an atomic attribute among (element, name) 
                and value is the attribute value.
              * list, tuple, set, numpy.ndarray: in shell atoms indexes  
           
           #. the lower distance limit of the coordination shell.
           #. the upper distance limit of the coordination shell.
           #. :math:`N_{min}` : the minimum number of neighbours in the shell.
           #. :math:`N_{max}` : the maximum number of neighbours in the shell.
           #. :math:`W_{i}` : the weight contribution to the standard error, 
              this is optional, if not given it is set automatically to 1.0.
        #. rejectProbability (Number): rejecting probability of all steps where standardError increases. 
           It must be between 0 and 1 where 1 means rejecting all steps where standardError increases
           and 0 means accepting all steps regardless whether standardError increases or not.
    
    
    .. code-block:: python
    
        # import fullrmc modules
        from fullrmc.Engine import Engine
        from fullrmc.Constraints.AtomicCoordinationConstraints import AtomicCoordinationNumberConstraint
        
        # create engine 
        ENGINE = Engine(path='my_engine.rmc')
        
        # set pdb file
        ENGINE.set_pdb('system.pdb')
        
        # create and add constraint
        ACNC = AtomicCoordinationNumberConstraint()
        ENGINE.add_constraints(ACNC)
        
        # create definition
        ACNC.set_coordination_number_definition( [ ('Al','Cl',1.5, 2.5, 2, 2),
                                                   ('Al','S', 2.5, 3.0, 2, 2)] )
        
    """
    def __init__(self, coordNumDef=None, rejectProbability=1):
        # initialize constraint
        RigidConstraint.__init__(self, rejectProbability=rejectProbability)
        # initialize data
        self.__initialize_constraint_data()
        # set coordination number definition
        self.set_coordination_number_definition(coordNumDef)
        # set computation cost
        self.set_computation_cost(5.0)
        
        # set frame data
        FRAME_DATA = [d for d in self.FRAME_DATA]
        FRAME_DATA.extend(['_AtomicCoordinationNumberConstraint__coordNumDef',
                           '_AtomicCoordinationNumberConstraint__coresIndexes',
                           '_AtomicCoordinationNumberConstraint__numberOfCores',
                           '_AtomicCoordinationNumberConstraint__shellsIndexes',
                           '_AtomicCoordinationNumberConstraint__lowerShells',
                           '_AtomicCoordinationNumberConstraint__upperShells',
                           '_AtomicCoordinationNumberConstraint__minAtoms',
                           '_AtomicCoordinationNumberConstraint__maxAtoms',
                           '_AtomicCoordinationNumberConstraint__coordNumData',
                           '_AtomicCoordinationNumberConstraint__weights',
                           '_AtomicCoordinationNumberConstraint__asCoreDefIdxs',
                           '_AtomicCoordinationNumberConstraint__inShellDefIdxs',] )
        RUNTIME_DATA = [d for d in self.RUNTIME_DATA]
        RUNTIME_DATA.extend( ['_AtomicCoordinationNumberConstraint__coordNumData',] )
        object.__setattr__(self, 'FRAME_DATA',   tuple(FRAME_DATA)   )
        object.__setattr__(self, 'RUNTIME_DATA', tuple(RUNTIME_DATA) )
    
    def __initialize_constraint_data(self):
        # set definition
        self.__coordNumDef = None
        # the following is the parsing of defined shells
        self.__coresIndexes  = []
        self.__numberOfCores = []
        self.__shellsIndexes = []
        self.__lowerShells   = []
        self.__upperShells   = []
        self.__minAtoms      = []
        self.__maxAtoms      = []
        # upon computing constraint data, those values must be divided by len( self.__coresIndexes[i] )
        self.__coordNumData = []
        self.__weights      = [] 
        # atoms to cores and shells pointers
        self.__asCoreDefIdxs  = []
        self.__inShellDefIdxs = []
        # no need to dump to repository because all of those attributes will be written 
        # at the point of setting the definition. 

    @property
    def coordNumDef(self):
        """Get coordination number definition dictionary"""
        return self.__coordNumDef
    
    @property
    def coresIndexes(self):  
        """Get the list of coordination number core atoms indexes array as generated 
        from  coordination number definition."""  
        return self.__coresIndexes
        
    @property
    def shellsIndexes(self):  
        """ Get the list of coordination number shell atoms indexes array as generated 
        from coordination number definition."""
        return self.__shellsIndexes
        
    @property
    def lowerShells(self):  
        """Get array of lower shells distance as generated from coordination number 
        definition. """  
        return self.__lowerShells
    
    @property
    def upperShells(self):  
        """Get array of upper shells distance as generated from coordination number 
        definition. """    
        return self.__upperShells
    
    @property
    def minAtoms(self):  
        """Get array of minimum number of atoms in a shell as generated from 
        coordination number definition. """   
        return self.__minAtoms
    
    @property
    def maxAtoms(self):  
        """Get array of maximum number of atoms in a shell as generated from 
        coordination number definition. """
        return self.__maxAtoms
    
    @property
    def weights(self):  
        """Get shells weights which count in the computation of standard error."""  
        return self.__weights
        
    @property
    def data(self):  
        """Get coordination number constraint data."""  
        return self.__coordNumData
    
    @property
    def asCoreDefIdxs(self):  
        """Get the list of arrays where each element is pointing to a coordination 
        number definition where the atom is a core."""  
        return self.__asCoreDefIdxs
    
    @property
    def inShellDefIdxs(self):  
        """Get the list of arrays where each element is pointing to a coordination 
        number definition where the atom is in a shell."""    
        return self.__inShellDefIdxs
               
    def listen(self, message, argument=None):
        """   
        listen to any message sent from the Broadcaster.
        
        :Parameters:
            #. message (object): Any python object to send to constraint's listen method.
            #. argument (object): Any type of argument to pass to the listeners.
        """
        if message in("engine set", "update molecules indexes"):
            self.set_coordination_number_definition(self.__coordNumDef)
        elif message in("update boundary conditions",):
            self.reset_constraint()        
    
    def set_coordination_number_definition(self, coordNumDef):
        """
        Set the coordination number definition.

        :Parameters:
            #. coordNumDef (None, list, tuple): The coordination number definition. 
               It must be None or a list or tuple where every element is a list or a
               tuple of exactly 6 items and an optional 7th item for weight.
               
               #. the core atoms: Can be any of the following:
               
                  * string: indicating atomic element
                  * dictionary: Key an atomic attribute among (element, name) 
                    and value is the attribute value.
                  * list, tuple, set, numpy.ndarray: core atoms indexes  
               
               #. the in shell atoms: Can be any of the following:
               
                  * string: indicating atomic element
                  * dictionary: Key an atomic attribute among (element, name) 
                    and value is the attribute value.
                  * list, tuple, set, numpy.ndarray: in shell atoms indexes  
               
               #. the lower distance limit of the coordination shell.
               #. the upper distance limit of the coordination shell.
               #. :math:`N_{min}` : the minimum number of neighbours in the shell.
               #. :math:`N_{max}` : the maximum number of neighbours in the shell.
               #. :math:`W_{i}` : the weight contribution to the standard error, 
                  this is optional, if not given it is set automatically to 1.0.
               
               ::

                   e.g. [ ('Ti','Ti', 2.5, 3.5, 5, 7.1, 1), ('Ni','Ti', 2.2, 3.1, 7.2, 9.7, 100), ...]
                        [ ({'element':'Ti'},'Ti', 2.5, 3.5, 5, 7.1, 0.1), ...]  
                        [ ({'name':'au'},'Au', 2.5, 3.5, 4.1, 6.3), ...]  
                        [ ({'name':'Ni'},{'element':'Ti'}, 2.2, 3.1, 7, 9), ...]   
                        [ ('Ti',range(100,500), 2.2, 3.1, 7, 9), ...]   
                        [ ([0,10,11,15,1000],{'name':'Ti'}, 2.2, 3.1, 7, 9, 5), ...]   
        
        """
        if self.engine is None:
            self.__coordNumDef = coordNumDef
            return
        elif coordNumDef is None:
            coordNumDef = []
        ########## check definitions, create coordination number data ########## 
        self.__initialize_constraint_data()
        for CNDef in coordNumDef:
            assert isinstance(CNDef, (list, tuple)), LOGGER.error("coordNumDef item must be a list or a tuple")
            if len(CNDef) == 6:
                coreDef, shellDef, lowerShell, upperShell, minCN, maxCN = CNDef
                weight = 1.0
            elif len(CNDef) == 7:
                coreDef, shellDef, lowerShell, upperShell, minCN, maxCN, weight = CNDef
            else:
                raise LOGGER.error("coordNumDef item must have 6 or 7 items")
            # core definition
            if isinstance(coreDef, basestring):
                coreDef = str(coreDef)
                assert coreDef in self.engine.elements, LOGGER.error("core atom definition '%s' is not a valid element"%coreDef)
                coreIndexes = [idx for idx, el in enumerate(self.engine.allElements) if el==coreDef]
            elif isnstance(coreDef, dict):
                assert len(coreDef) == 1, LOGGER.error("core atom definition dictionary must be of length 1")
                key, value = coreDef.keys()[0], coreDef.values()[0]
                if key is "name":
                    assert value in self.engine.names, LOGGER.error("core atom definition '%s' is not a valid name"%coreDef)
                    coreIndexes = [idx for idx, el in enumerate(self.engine.allNames) if el==coreDef]
                elif key is "element":
                    assert value in self.engine.elements, LOGGER.error("core atom definition '%s' is not a valid element"%coreDef)
                    coreIndexes = [idx for idx, el in enumerate(self.engine.allElements) if el==coreDef]
                else:
                    raise LOGGER.error("core atom definition dictionary key must be either 'name' or 'element'")
            elif isnstance(coreDef, (list, tuple, set, np.ndarray)):
                coreIndexes = []
                if isinstance(coreDef, np.ndarray):
                    assert len(coreDef.shape)==1, LOGGER.error("core atom definition numpy.ndarray must be 1D")
                for c in coreDef:
                    assert is_integer(c), LOGGER.error("core atom definition index must be integer")
                    c = INT_TYPE(c)
                    assert c>=0, LOGGER.error("core atom definition index must be >=0")
                    assert c<len(self.engine.pdb), LOGGER.error("core atom definition index must be smaler than number of atoms in system")
                    coreIndexes.append(c)
            # shell definition
            if isinstance(shellDef, basestring):
                shellDef = str(shellDef)
                assert shellDef in self.engine.elements, LOGGER.error("core atom definition '%s' is not a valid element"%shellDef)
                shellIndexes = [idx for idx, el in enumerate(self.engine.allElements) if el==shellDef]
            elif isnstance(shellDef, dict):
                assert len(shellDef) == 1, LOGGER.error("core atom definition dictionary must be of length 1")
                key, value = shellDef.keys()[0], shellDef.values()[0]
                if key is "name":
                    assert value in self.engine.names, LOGGER.error("core atom definition '%s' is not a valid name"%shellDef)
                    shellIndexes = [idx for idx, el in enumerate(self.engine.allNames) if el==shellDef]
                elif key is "element":
                    assert value in self.engine.elements, LOGGER.error("core atom definition '%s' is not a valid element"%shellDef)
                    shellIndexes = [idx for idx, el in enumerate(self.engine.allElements) if el==shellDef]
                else:
                    raise LOGGER.error("core atom definition dictionary key must be either 'name' or 'element'")
            elif isnstance(shellDef, (list, tuple, set, np.ndarray)):
                shellIndexes = []
                if isinstance(shellDef, np.ndarray):
                    assert len(shellDef.shape)==1, LOGGER.error("core atom definition numpy.ndarray must be 1D")
                for c in shellDef:
                    assert is_integer(c), LOGGER.error("core atom definition index must be integer")
                    c = INT_TYPE(c)
                    assert c>=0, LOGGER.error("core atom definition index must be >=0")
                    assert c<len(self.engine.pdb), LOGGER.error("core atom definition index must be smaler than number of atoms in system")
                    shellIndexes.append(c)
            # lower and upper shells definition
            assert is_number(lowerShell), LOGGER.error("Coordination number lower shell '%s' must be a number."%lowerShell)       
            lowerShell = FLOAT_TYPE(lowerShell)
            assert lowerShell>=0, LOGGER.error("Coordination number lower shell '%s' must be a positive."%lowerShell)       
            assert is_number(upperShell), LOGGER.error("Coordination number upper shell '%s' must be a number."%key)       
            upperShell = FLOAT_TYPE(upperShell)
            assert upperShell>lowerShell, LOGGER.error("Coordination number lower shell '%s' must be smaller than upper shell %s"%(lowerShell,upperShell))       
            # minimum and maximum number of atoms definitions
            assert is_number(minCN), LOGGER.error("Coordination number minimum atoms '%s' must be a number."%minCN)       
            minCN = FLOAT_TYPE(minCN)
            assert minCN>=0, LOGGER.error("Coordination number minimim atoms '%s' must be >=0."%minCN)       
            assert is_number(maxCN), LOGGER.error("Coordination number maximum atoms '%s' must be a number."%key)       
            maxCN = FLOAT_TYPE(maxCN)
            assert maxCN>=minCN, LOGGER.error("Coordination number minimum atoms '%s' must be smaller than maximum atoms %s"%(minCN,maxCN))       
            # check weight
            assert is_number(weight), LOGGER.error("Coordination number weight '%s' must be a number."%weight)       
            weight = FLOAT_TYPE(weight)
            assert weight>0, LOGGER.error("Coordination number weight '%s' must be >0."%weight)       
            # append coordination number data
            self.__coresIndexes.append( sorted(set(coreIndexes)) )
            self.__shellsIndexes.append( sorted(set(shellIndexes)) ) 
            self.__lowerShells.append( lowerShell )    
            self.__upperShells.append( upperShell )    
            self.__minAtoms.append( minCN )      
            self.__maxAtoms.append( maxCN ) 
            self.__coordNumData.append( FLOAT_TYPE(0) ) 
            self.__weights.append( weight ) 
        ########## set asCoreDefIdxs and inShellDefIdxs points ##########  
        for _ in xrange(self.engine.numberOfAtoms):
            self.__asCoreDefIdxs.append( [] )
            self.__inShellDefIdxs.append( [] )
        for defIdx, indexes in enumerate(self.__coresIndexes):
            self.__coresIndexes[defIdx] = np.array( indexes, dtype=INT_TYPE )
            for atIdx in indexes:
                self.__asCoreDefIdxs[atIdx].append( defIdx )
        for defIdx, indexes in enumerate(self.__shellsIndexes):
            self.__shellsIndexes[defIdx] = np.array( indexes, dtype=INT_TYPE )
            for atIdx in indexes:
                self.__inShellDefIdxs[atIdx].append( defIdx )
        for atIdx in xrange(self.engine.numberOfAtoms):
            self.__asCoreDefIdxs[atIdx]  = np.array( self.__asCoreDefIdxs[atIdx], dtype=INT_TYPE )
            self.__inShellDefIdxs[atIdx] = np.array( self.__inShellDefIdxs[atIdx], dtype=INT_TYPE )
        # set all to arrays
        self.__coordNumData  = np.array( self.__coordNumData, dtype=FLOAT_TYPE )
        self.__weights       = np.array( self.__weights, dtype=FLOAT_TYPE )
        self.__numberOfCores = np.array( [len(idxs) for idxs in self.__coresIndexes], dtype=FLOAT_TYPE )
        # set definition
        self.__coordNumDef = coordNumDef
        # dump to repository
        self._dump_to_repository({'_AtomicCoordinationNumberConstraint__coordNumDef'  :self.__coordNumDef,
                                  '_AtomicCoordinationNumberConstraint__coordNumData' :self.__coordNumData,
                                  '_AtomicCoordinationNumberConstraint__weights'      :self.__weights,
                                  '_AtomicCoordinationNumberConstraint__numberOfCores':self.__numberOfCores,
                                  '_AtomicCoordinationNumberConstraint__coresIndexes' :self.__coresIndexes,
                                  '_AtomicCoordinationNumberConstraint__shellsIndexes':self.__shellsIndexes,
                                  '_AtomicCoordinationNumberConstraint__lowerShells'  :self.__lowerShells,
                                  '_AtomicCoordinationNumberConstraint__upperShells'  :self.__upperShells,
                                  '_AtomicCoordinationNumberConstraint__minAtoms'     :self.__minAtoms,
                                  '_AtomicCoordinationNumberConstraint__maxAtoms'     :self.__maxAtoms})

    def compute_standard_error(self, data):
        """ 
        Compute the standard error (StdErr) of data not satisfying constraint conditions. 
        
        .. math::        
            StdErr = \\sum \\limits_{i}^{S} Dev_{i}


        .. math::
            Dev_{i}=\\begin{cases}
              W_{i}*( N_{min,i}-\\overline{CN_{i}} ), & \\text{if $\\overline{CN_{i}}<N_{min,i}$}.\\\\
              W_{i}*( \\overline{CN_{i}}-N_{max,i} ), & \\text{if $\\overline{CN_{i}}>N_{max,i}$}.\\\\
              0                  , & \\text{if $N_{min,i}<=\\overline{CN_{i}}<=N_{max,i}$}
            \\end{cases}
        
                
        Where:\n
        :math:`S`                  is the total number of defined coordination number shells. \n
        :math:`W_{i}`              is the defined weight of coordination number shell i. \n
        :math:`Dev_{i}`            is the standard deviation of the coordination number in shell definition i. \n
        :math:`\\overline{CN_{i}}` is the mean coordination number value in shell definition i. \n
        :math:`N_{min,i}`          is the defined minimum number of neighbours in shell definition i. \n
        :math:`N_{max,i}`          is the defined maximum number of neighbours in shell definition i. \n
         

        :Parameters:
            #. data (numpy.array): The constraint value data to compute standardError.
            
        :Returns:
            #. standardError (number): The calculated standardError of the constraint.
        """
        coordNum = data/self.__numberOfCores
        StdErr   = 0.
        for idx, cn in enumerate( coordNum ):
            if cn < self.__minAtoms[idx]:
                StdErr += self.__weights[idx]*(self.__minAtoms[idx]-cn)
            elif cn > self.__maxAtoms[idx]:
                StdErr += self.__weights[idx]*(cn-self.__maxAtoms[idx])
        return StdErr
        
    def get_constraint_value(self):
        """
        Gets squared deviation per shell definition
        
        :Returns:
            #. MPD (dictionary): The MPD dictionary, where keys are the element wise intra and inter molecular MPDs and values are the computed MPDs.
        """
        if self.data is None:
            log.LocalLogger("fullrmc").logger.warn("data must be computed first using 'compute_data' method.")
            return None
        
    def compute_data(self):
        """ Compute data and update engine constraintsData dictionary. """
        all_atoms_coord_number_coords(boxCoords      = self.engine.boxCoordinates,
                                      basis          = self.engine.basisVectors,
                                      isPBC          = self.engine.isPBC,
                                      coresIndexes   = self.__coresIndexes,
                                      shellsIndexes  = self.__shellsIndexes,
                                      lowerShells    = self.__lowerShells,
                                      upperShells    = self.__upperShells,
                                      asCoreDefIdxs  = self.__asCoreDefIdxs,
                                      inShellDefIdxs = self.__inShellDefIdxs,
                                      coordNumData   = self.__coordNumData,
                                      ncores         = self.engine._runtime_ncores)
        self.__coordNumData /= FLOAT_TYPE(2.)         
        # update data
        self.set_data( self.__coordNumData )
        self.set_active_atoms_data_before_move(None)
        self.set_active_atoms_data_after_move(None)
        # set standardError
        stdErr = self.compute_standard_error(data = self.__coordNumData)
        self.set_standard_error(stdErr)

    def compute_before_move(self, indexes):
        """ 
        Compute constraint before move is executed
        
        :Parameters:
            #. indexes (numpy.ndarray): Group atoms indexes the move will be applied to
        """
        beforeMoveData = np.zeros(self.__coordNumData.shape, dtype=self.__coordNumData.dtype)
        multi_atoms_coord_number_coords( indexes        = indexes,
                                         boxCoords      = self.engine.boxCoordinates,
                                         basis          = self.engine.basisVectors,
                                         isPBC          = self.engine.isPBC,
                                         coresIndexes   = self.__coresIndexes,
                                         shellsIndexes  = self.__shellsIndexes,
                                         lowerShells    = self.__lowerShells,
                                         upperShells    = self.__upperShells,
                                         asCoreDefIdxs  = self.__asCoreDefIdxs,
                                         inShellDefIdxs = self.__inShellDefIdxs,
                                         coordNumData   = beforeMoveData,
                                         ncores         = self.engine._runtime_ncores)
        # set active atoms data before move
        self.set_active_atoms_data_before_move( beforeMoveData )
        self.set_active_atoms_data_after_move(None)                                                   
           
    def compute_after_move(self, indexes, movedBoxCoordinates):
        """ 
        Compute constraint after move is executed
        
        :Parameters:
            #. indexes (numpy.ndarray): Group atoms indexes the move will be applied to.
            #. movedBoxCoordinates (numpy.ndarray): The moved atoms new coordinates.
        """
        # change coordinates temporarily
        boxData = np.array(self.engine.boxCoordinates[indexes], dtype=FLOAT_TYPE)
        self.engine.boxCoordinates[indexes] = movedBoxCoordinates
        # compute after move data
        afterMoveData = np.zeros(self.__coordNumData.shape, dtype=self.__coordNumData.dtype)
        multi_atoms_coord_number_coords( indexes        = indexes,
                                         boxCoords      = self.engine.boxCoordinates,
                                         basis          = self.engine.basisVectors,
                                         isPBC          = self.engine.isPBC,
                                         coresIndexes   = self.__coresIndexes,
                                         shellsIndexes  = self.__shellsIndexes,
                                         lowerShells    = self.__lowerShells,
                                         upperShells    = self.__upperShells,
                                         asCoreDefIdxs  = self.__asCoreDefIdxs,
                                         inShellDefIdxs = self.__inShellDefIdxs,
                                         coordNumData   = afterMoveData,
                                         ncores         = self.engine._runtime_ncores)
        # reset coordinates
        self.engine.boxCoordinates[indexes] = boxData
        # set active atoms data after move
        self.set_active_atoms_data_after_move( afterMoveData )
        # compute after move standard error
        self.__coordNumDataAfterMove = self.__coordNumData-self.activeAtomsDataBeforeMove+self.activeAtomsDataAfterMove
        self.set_after_move_standard_error( self.compute_standard_error(data = self.__coordNumDataAfterMove) )

    def accept_move(self, indexes):
        """ 
        Accept move.
        
        :Parameters:
            #. indexes (numpy.ndarray): Group atoms indexes the move will be applied to
        """
        self.__coordNumData = self.__coordNumDataAfterMove
        # reset activeAtoms data
        self.set_active_atoms_data_before_move(None)
        self.set_active_atoms_data_after_move(None)
        # update standardError
        self.set_standard_error(self.afterMoveStandardError)
        self.set_after_move_standard_error( None )
        
    def reject_move(self, indexes):
        """ 
        Reject move.
        
        :Parameters:
            #. indexes (numpy.ndarray): Group atoms indexes the move will be applied to
        """
        # reset activeAtoms data
        self.set_active_atoms_data_before_move(None)
        self.set_active_atoms_data_after_move(None)
        # update standardError
        self.set_after_move_standard_error( None )


    
    
            