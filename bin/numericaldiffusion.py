# -*- coding: utf-8 -*-
import numpy as np
from scipy.constants import N_A

class SphericNumericalDiffusion(object):
    A = np.array([])
    def __init__(self, start, stop, xsteps, deltat, D, U = None):
        """
        Simulates diffusion with constant D in one dimension from start to stop with the timestep deltat and xstep number of bins.
        Implemented for spherical symmetry. 

        Args:
            start (float): Leftmost point of simulation
            stop (float): Rightmost point of simulation
            xsteps (int): Number of bins
            deltat (float): Length of one timestep
            D (float): Diffusion constant
            U (list<float>[xsteps], optional): Concentration profile at timepoint 0. Defaults to None.
        """
        self.start = start
        self.stop = stop
        self.xsteps = xsteps
        self.deltat = deltat
        self.D = D
        self.deltax = (stop - start)/xsteps
        self.time = 0
        if type(U) != type(None):
            self.U = np.zeros((xsteps, 1))
            self.U[:U.shape[0], :U.shape[1]] = U
        else:
            self.U = np.zeros((xsteps, 1))
        self.makeArray(xsteps, deltat, self.deltax, D)
        
    def setDiffusionConstant(self, d):
        self.D = d
        
    def makeArray(self, xsteps, deltat, deltax, D):
        """
        Generates the solution matrix to the systems of differential equations.

        Args:
            xsteps (int): number of bins
            deltat (float): length of one timestep
            deltax (float): width of one bin
            D (float): diffusivity constant
        """
        K = D*deltat / deltax**2
        r = lambda i : i*deltax + self.start
        
        xn = lambda i : 1 + 2*K/r(i)**2 *(r(i)**2 + deltax**2)
        xp = lambda i : -(r(i) + deltax)**2 * K/r(i)**2
        xm = lambda i : -(r(i) - deltax)**2 *K/r(i)**2

        A = np.diag([xn(i) for i in range(xsteps)], 0)
        A += np.diag([xp(i) for i in range(xsteps - 1)], 1)
        A += np.diag([xm(i) for i in range(xsteps - 1)], -1)
        A[0,0] = 1 + K/r(0)**2 * (r(0)**2 + deltax**2)
        A[-1,-1] = 1 + K/r(xsteps)**2 *(r(xsteps)**2 + deltax**2)
        A = np.linalg.inv(A)
        self.A = A

    def timeStep(self):
        """
        Performs one timestep using Eulers method
        """
        self.U = np.matmul(self.A, self.U)
        self.time += self.deltat


class SphericIncrementedDiffusion(SphericNumericalDiffusion):
    def __init__(self, start, stop, xsteps, deltat, D, ke, cBacteria=1e12, U = None):
        """Simulates diffusion whith more material being added at pos x=start.

        Args:
            Same as SphericNumericalDiffusion and 
            ke (float): secretion rate
        """
        super().__init__(start, stop, xsteps, deltat, D, U)
        self.ke = ke
        self.bactomol = (N_A/cBacteria)
    

    def timeStep(self):
        if type(self.U) == int:
            raise ValueError
        if type(self.U) != type(None):
            self.U[0,0] += self.ke*self.bactomol*self.deltat/N_A/(4/3*np.pi*((self.start + self.deltax)**3 - self.start**3)*1e3)
        super().timeStep()

class UniformIncrementedDiffusion(object):
    def __init__(self, deltat, ke, c0 = None):
        """Simulates concentration in a homogenous solution were more substance is added every second. 

        Args:
            deltat (float): length of one timestep
            ke (float): secretion rate
            U (float, optional): Inital concentration in the solution. Defaults to 0.
        """
        self.deltat = deltat
        self.time = 0
        if c0 != None:
            self.c = c0
        else:
            self.c = 0
        self.ke = ke
    
    def timeStep(self):
        self.c += self.ke*self.deltat
        self.time += self.deltat

class CsgADiffusion(SphericIncrementedDiffusion, UniformIncrementedDiffusion):
    
    R0 = 380e-9
    D = 8*1e-11
    
    def __init__(self, dist, xsteps, deltat, cBacteria=1e12,how='uniform', c0=None):
        """Simmulates the diffusion of CsgA monomers. 

        Args:
            dist (float): length away from membrane to be simulated
            xsteps (int): number of bins
            deltat (float): length of one timestep
            how (string): "spherical" or "uniform". How the 
            U0 (float or list<int>[xsteps]): Initial concentration or concentration profile
        """
        self.how = how
        self.ke = 1e-10 / 1e12 *cBacteria
        if how == 'spherical':
            SphericIncrementedDiffusion.__init__(self, self.R0, dist + self.R0, xsteps, deltat, self.D, self.ke, cBacteria, c0)
        elif how == 'uniform':
            UniformIncrementedDiffusion.__init__(self, deltat, self.ke, c0)
        else: 
            raise ValueError("How must be 'spherical' or 'uniform'")
        
    def timeStep(self):
        if self.how == 'spherical':
            SphericIncrementedDiffusion.timeStep(self)
        else:
            UniformIncrementedDiffusion.timeStep(self)

class Inhibitor(SphericIncrementedDiffusion, UniformIncrementedDiffusion):
    R0 = 380e-9
    D = 1.2 *1e-10
    def __init__(self, dist, xsteps, deltat, ke, cBacteria=1e12,how='uniform', c0=None):
        """Utility class to simulate the behavior of inhibitors secreted from a bacteria. 

        Args:
            dist (float): distance from the membrane to simulate
            xsteps (int): number of bins
            deltat (float): length of one timestep
            ke (float): secretion rate
            how (str, optional): "spherical" or "uniform". Defaults to 'uniform'.
            U0 (float or list<int>[xsteps], optional): Initial concentration profile. Defaults to None.
        """
        self.how = how
        ke = ke *cBacteria*1e-12
        if how == 'spherical':
            SphericIncrementedDiffusion.__init__(self,self.R0, dist + self.R0, xsteps, deltat, self.D, ke,cBacteria, c0)
        elif how == 'uniform':
            UniformIncrementedDiffusion.__init__(self,deltat, ke, c0)
        else: 
            raise ValueError("How must be 'spherical' or 'uniform'")
    
    def bindingFunc(self,other):
        """Describes how the inhibitor will affect the CsgA concentration. The concentration profile is accesed and altered inplace \
             through the CgsADiffusion.U attribute.

        Args:
            other (CsgADiffusion): The diffusion object for the CsgA monomers. 

        Returns:
            None
        """
        return None

    def rateFunc(self,other, kwrates):
        """Describes how the inhibitor will affect the binding rates of CsgA monomers to Curli fibrils.\
            Only implemented for uniform distributions of the inhibitor. kwrates is only implemented to contain kplus for now.

        Args:
            other (CsgADiffusion): The concentration profile of the CsgA 
            kwrates (dic<string, float>): The rate constants. 

        Returns:
            kwrates (dict) : The modified rate konstants
        """
        return kwrates

    def timeStep(self, other):
        if self.how == 'uniform':
            UniformIncrementedDiffusion.timeStep(self)
        else:
            raise ValueError("Inhibitors can only follow a uniform distribution")
        
        self.bindingFunc(other)
    
class inhibitedCsgAC(CsgADiffusion):
    def __init__(self, dist, xsteps, deltat, cBacteria, how, c0, inhibitors):
        """Final subclass that combines the inhibitors with the CsgA class. 
        """
        super().__init__(dist, xsteps, deltat, cBacteria, how, c0)
        self.inhibitors = inhibitors
    
    def timeStep(self):
        super().timeStep()
        list(map(lambda i : i.timeStep(self), self.inhibitors))