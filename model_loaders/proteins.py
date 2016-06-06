""" Loading data for Molecular Dynamics Simulations

Requires package: https://github.com/ajkluber/model_builder

"""
import numpy as np
import mdtraj as md

from pyfexd.model_loaders import ModelLoader
try:
    import model_builder as mdb
except:
    pass

class Protein(ModelLoader):
    """ Subclass for making a ModelLoader for a Protein Model
    
    Methods:
        See ModelLoader in pyfexd/super_model/ModelLoader
    
    """
    
    def __init__(self, ini_file_name):
        """ Initialize the Langevin model, override superclass
        
        Args:
            ini_file_name: Name of a .ini file to load containing the 
                model information.
        
        Attributes:
            See superclass for generic attributes.
            epsilons(array): Chosen from a specific list of tunable 
                parameters from the .ini file.
        
        """
        self.GAS_CONSTANT_KJ_MOL = 0.0083144621 #kJ/mol*k
        try:
            from langevin_model.model import langevin_model as lmodel
        except:
            raise IOError("model_builder package is not installed.")
        
        ##remove .ini suffix
        self.model, self.fittingopts = mdb.inputs.load_model(ini_file_name)
        
        if "fret_pairs" in self.fittingopts and not self.fittingopts["fret_pairs"] is None:
            self.fret_pairs = self.fittingopts["fret_pairs"]
        else:
            self.fret_pairs = [None]
            
        # get indices corresponding to epsilons to use
        # Assumes only parameters to change are pair interactions
        self.use_params = np.arange(len(self.model.Hamiltonian._pairs)) #assumes you use all pairs
        self.pairs = self.model.mapping._contact_pairs
        self.use_pairs = []
        for i in self.use_params: #only load relevant parameters
            self.use_pairs.append([self.pairs[i][0].index, self.pairs[i][1].index])
        
        self.epsilons = self.model.fitted_epsilons
        self.beta = 1.0 #set temperature
        
    
    def load_data(self,fname):
        """ Load a data file and format for later use
        
        For Proteins, it uses the self.pairs to load the pair-pair 
        distances for every frame. This is the data format that would be 
        used for computing the energy later.
        
        Args:
            fname(string): Name of a file to load.
        
        Return:
            Array(floats): First index is frame, second index is every 
                pair in the order of pairs.
            
        """
        
        traj = md.load(fname, top=self.model.mapping.topology)
        data = md.compute_distances(traj, self.use_pairs, periodic=False)

        return data
    
    def get_potentials_epsilon(self, data):
        """ Return PotentialEnergy(epsilons)  
        
        See superclass for full description of purpose.
        Override superclass. Potential Energy is easily calculated since
        for this model, all epsilons are linearly related to the 
        potential energy.
        
        """
        
        #check to see if data is the expected shape for this analysis:
        if not np.shape(data)[1] == np.shape(self.use_params)[0]:
            err_str = "dimensions of data incompatible with number of parameters\n"
            err_str += "Second index must equal number of parameters \n"
            err_str += "data is: %s, number of parameters is: %d" %(str(np.shape(data)), len(self.use_params))
            raise IOError(err_str)
        
        #list of constant pre factors to each model epsilons
        constants_list = [] 
        
        for i in self.use_params:
            constants_list.append(self.model.Hamiltonian._pairs[i].dVdeps(data[:,i]) * -1.0 * self.beta)
        
        #compute the function for the potential energy
        def hepsilon(epsilons):
            total = np.zeros(np.shape(data)[0])
            for i in range(np.shape(epsilons)[0]):
                total += epsilons[i]*constants_list[i]
            
            return total     
        
        #compute the function for the derivative of the potential energy
        def dhepsilon(epsilons):
            #first index is corresponding epsilon, second index is frame
            return constants_list
        
        return hepsilon, dhepsilon
        
        
class ProteinNonLinear(Protein):
    """ Same as protein, except handles nonlinear H(epsilons)
    
    Just like the class Protein, except it handles a non-linear 
    Hamiltonian function of epsilons. Thusly, only the 
    get_potentials_epsilon is overridden.
    
    """
        
    def get_potentials_epsilon(self, data):
        num_frames = np.shape(data)[0]

        functions_list = []
        dfunctions_list = []
        for i in self.use_params:
            functions_list.append(self.model.Hamiltonian._pairs[i].get_V_epsilons(data[:,i]))
            dfunctions_list.append(self.model.Hamiltonian._pairs[i].get_dV_depsilons(data[:,i]))
        #compute the function for the potential energy
        def hepsilon(epsilons):
            total = np.zeros(np.shape(data)[0])
            for i in range(np.shape(epsilons)[0]):
                total += functions_list[i](epsilons[i])
            total *= -1. * self.beta
            
            return total     
        
        #compute the function for the derivative of the potential energy
        def dhepsilon(epsilons):
            #first index is corresponding epsilon, second index is frame
            derivatives_list = []
            for func in dfunctions_list:
                derivatives_list.append(func(epsilons))
            return derivatives_list
        
        return hepsilon, dhepsilon

'''
        def hepsilon(epsilons):
            total_energy = np.zeros(np.shape(data)[0])
            for idx, param in enumerate(self.use_params):    
                self.model.Hamiltonian._pairs[param].set_epsilon(epsilons[idx])
                energy = self.model.Hamiltonian._pairs[param].V(data[:,idx])
                total_energy += energy
            
            return total_energy * self.beta * -1.
        
        
        def dhepsilon(epsilons):
            total_energy = np.zeros(np.shape(data))
            for idx, param in enumerate(self.use_params):    
                self.model.Hamiltonian._pairs[param].set_epsilon(epsilons[idx])
            
                energy = self.model.Hamiltonian._pairs[param].dVdeps(data[:,idx])
                total_energy[:,idx] += energy
            
            total_energy *= self.beta * -1.
            
            gradient = [total_energy[:,idx] for idx in range(np.shape(self.use_params)[0])]
            
            
            #assert len(gradient) == num_frames
            #for term in gradient:
            #    assert np.shape(term)[0] == np.shape(self.use_params)[0]
            return gradient 
        
        
        return hepsilon, dhepsilon
        
'''        
        
        
        
