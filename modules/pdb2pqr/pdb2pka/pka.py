#!/usr/bin/env python
#
# pKa calculations with APBS
#
# Copyright University College Dublin & Washington University St. Louis 2004-2007
# All rights reserved
#

#
# Get paths
#
debug=False
import optparse
import sys, os
from pKa_base import *

print __file__
import os
try:
    file_name=__file__
    if file_name[:2]=='./':
        scriptpath=os.getcwd()
    else:
        scriptpath=os.path.join(os.getcwd(),os.path.split(file_name)[0])
        if scriptpath[-1] == "/":
            scriptpath=scriptpath[:-1]
except:
    scriptpath=os.path.split(sys.argv[0])[0]
    if scriptpath=='.':
        scriptpath=os.getcwd()
#
# Add to import path
#
pdb2pqr_path=os.path.split(scriptpath)[0]
sys.path.append(pdb2pqr_path)
#
# Imports - these should be cleaned up
#
import string
import math
import string
import getopt
import time
from src import pdb
from src import utilities
from src import structures
from src import routines
from src import protein
from src import server
from src.pdb import *
from src.utilities import *
from src.structures import *
from src.definitions import *
from src.forcefield import *  
from src.routines import *
from src.protein import *
from src.server import *
from StringIO import *
from src.hydrogens import *


def usage(x):
    #
    # Print usage guidelines
    #
    print 'Usage: pka.py --ff <forcefield> --lig <ligand in MOL2> --pdie <protein diel cons> --maps <1 for using provided 3D maps; 2 for genereting new maps>'
    print '--xdiel <xdiel maps> --ydiel <ydiel maps> --zdiel <zdiel maps> --kappa <ion-accessibility map> '
    print '--smooth <st.dev [A] of Gaussian smooting of 3D maps at the boundary, bandthwith=3 st.dev> <pdbfile>'
    print 'Force field can be amber, charmm and parse'
    print
    return

#
# --------------------------------------------------
#

def startpKa():
    """
        Function for starting pKa script from the command line.

        Returns
            protein:    The protein object as generated by PDB2PQR
            routines:   The routines object as generated by PDB2PQR
            forcefield: The forcefield object as generated by PDB2PQR
    """
    print
    print 'PDB2PQR pKa calculations'
    print
    
    import optparse
    parser = optparse.OptionParser()

    ##
    ## set optparse options
    ##
    parser.add_option(
        '-v','--verbose',
        dest='verbose',
        action="store_true",
        default=False,
        )
    parser.add_option(
        '--pdie',
        dest='pdie',
        default=8,
        type='int',
        help='<protein dielectric constant>',
        )
    parser.add_option(
        '--sdie',
        dest='sdie',
        default=80,
        type='int',
        help='<solvent dielectric constant>',
        )
    parser.add_option(
        '--ff',
        dest='ff',
        type='choice',
        default='parse',
        choices=("amber","AMBER","charmm","CHARMM","parse","PARSE",),
        help='<force field (amber, charmm, parse)>',
        )
    parser.add_option(
        '--ligand',
        dest='ligand',
        type='str',
        action='append',
        default=[],
        help='<ligand in MOL2 format>',
        )
    parser.add_option(
        '--maps',
        dest='maps',
        default=None,
        type='int',
        help='<1 for using provided 3D maps; 2 for genereting new maps>',
        )
    parser.add_option(
        '--xdiel',
        dest='xdiel',
        default=None,
        type='str',
        help='<xdiel maps>',
        )
    parser.add_option(
        '--ydiel',
        dest='ydiel',
        default=None,
        type='str',
        help='<ydiel maps>',
        )
    parser.add_option(
        '--zdiel',
        dest='zdiel',
        default=None,
        type='str',
        help='<zdiel maps>',
        )
    parser.add_option(
        '--kappa',
        dest='kappa',
        default=None,
        type='str',
        help='<ion-accessibility map>',
        )
    parser.add_option(
        '--smooth',
        dest='sd',
        default=None,
        type='float',
        help='<st.dev [A] of Gaussian smooting of 3D maps at the boundary, bandthwith=3 st.dev>',
        )
    #
    # Cut off energy for calculating non-charged-charged interaction energies
    #
    parser.add_option('--pairene',dest='pairene',type='float',default=1.0,
                      help='Cutoff energy in kT for calculating non charged-charged interaction energies. Default: %default')
    #
    # Options for doing partial calculations
    #
    parser.add_option('--res_energy',
                      dest='desolvation_res',
                      default=[],
                      action='append',
                      type='string',
                      help='Calculate desolvation energy and interaction energy for this residue in its default protonation state. Protonation states can be specified with the --protonation_state argument')
    parser.add_option('--PS_file',dest='PS_file',default='',type='string',action='store',help='Set protonation states according to the pdb2pka protonation state file (option --PS_file)')
    (options,args,) = parser.parse_args()

    ##
    ## parse optparse options
    ##
    ff = options.ff.lower()
    pdie = options.pdie
    verbose = options.verbose
    maps = options.maps
    xdiel = options.xdiel
    ydiel = options.ydiel
    zdiel = options.zdiel
    kappa = options.kappa
    sd = options.sd
    if verbose == False:
        verbose = 0
    elif verbose == True:
        verbose = 1

    #
    # Find the PDB file
    #
    if len(args) != 1:
        sys.stderr.write("Usage: pka.py [options] <pdbfile>\n")
        sys.exit(0)
    path = args[0]

    #
    # Call the pre_init function
    #
    return pre_init(pdbfilename=path,
                    ff=ff,
                    pdie=pdie,
                    maps=maps,
                    xdiel=xdiel,
                    ydiel=ydiel,
                    zdiel=zdiel,
                    kappa=kappa,
                    sd=sd,
                    options=options),options



#
# ----
#


def pre_init(pdbfilename=None,ff=None,verbose=1,pdie=8.0,maps=None,xdiel=None,ydiel=None,zdiel=None,kappa=None,sd=None,options=None):
    """This function cleans the PDB and prepares the APBS input file"""
    #
    # remove hydrogen atoms
    #
    import pka_help
    pka_help.remove_hydrogens(pdbfilename)
    #
    # Get the PDBfile
    #
    global pdbfile_name
    pdbfile_name=pdbfilename
    pdbfile = getPDBFile(pdbfilename)
    pdblist, errlist = readPDB(pdbfile)
    #
    if len(pdblist) == 0 and len(errlist) == 0:
        print "Unable to find file %s!\n" % path
        os.remove(path)
        sys.exit(2)

    if len(errlist) != 0 and verbose:
        print "Warning: %s is a non-standard PDB file.\n" %pdbfilename
        print errlist

    if verbose:
        print "Beginning PDB2PQR...\n"
    #
    # Read the definition file
    #
    myDefinition = Definition()
    ligand_titratable_groups=None
    #
    #
    # Choose whether to include the ligand or not
    #
    # Add the ligand to the pdb2pqr arrays
    #
    Lig=None
    MOL2FLAG = False 
    if not options.ligand:
        dummydef = Definition()
        myProtein = Protein(pdblist, dummydef)
    else:
        #
        # Mol2 ligands and PDB ligands are treated differently
        #
        if options.ligand!=[]:
            for ligand in options.ligand:
                #
                # Open ligand mol2 file
                #
                if os.path.isfile(ligand):
                    ligfd=open(ligand, 'rU')
                else:
                    print 'skipping ligand',ligand
                    continue
                #
                # Read the ligand into Paul's code
                #
                from ligandclean import ligff
                myProtein, myDefinition, Lig = ligff.initialize(myDefinition, ligfd, pdblist, verbose)
                #
                # Create the ligand definition from the mol2 data
                #
                #import NEWligand_topology
                #MOL2FLAG = True # somethign is rotten here
                ##
                #X=NEWligand_topology.get_ligand_topology(Lig.lAtoms,MOL2FLAG)
                #
                # Add it to the 'official' definition
                #
                #ligresidue=myDefinition.parseDefinition(X.lines, 'LIG', 2)
                #myDefinition.AAdef.addResidue(ligresidue)
                #
                # Look for titratable groups in the ligand
                #
                #print '==============================\n================================\n======================='
                #ligand_titratable_groups=X.find_titratable_groups()
                #print '==============================\n================================\n======================='
                #print "ligand_titratable_groups", ligand_titratable_groups
            #
            # ------------------------------------------------------
            # Creation of ligand definition and identification of ligand titgrps done
            # Start loading everything into PDB2PQR
            #
            # Append the ligand data to the end of the PDB data
            #
            #newpdblist=[]
            # First the protein
            #for line in pdblist:
            #    if isinstance(line, END) or isinstance(line,MASTER):
            #        continue
            #    newpdblist.append(line)
            ## Now the ligand
            #for e in Lig.lAtoms:
            #    newpdblist.append(e)
            #
            # Add a TER and an END record for good measure
            #
            #newpdblist.append(TER)
            #newpdblist.append(END)
            #
            # Let PDB2PQR parse the entire file
            #
            #myProtein = Protein(newpdblist)
        #
        # Post-Processing for adding sybylTypes to lig-atoms in myProtein
        # Jens: that's the quick and easy solution
        #
        #for rrres in  myProtein.chainmap['L'].residues:
        #    for aaat in rrres.atoms:
        #        for ligatoms in Lig.lAtoms:
        #            if ligatoms.name == aaat.name:
        #                aaat.sybylType = ligatoms.sybylType
        #                #
        #                # setting the formal charges
        #                if ligatoms.sybylType == "O.co2":
        #                    aaat.formalcharge = -0.5
        #                else: aaat.formalcharge = 0.0
        #                xxxlll = []
        #                for xxx in ligatoms.lBondedAtoms:
        #                    xxxlll.append(xxx.name)
        #                aaat.intrabonds = xxxlll
        #                #
        #                # charge initialisation must happen somewhere else
        #                # but i don't know where...
        #                aaat.charge = 0.0#




        #
    #
    # =======================================================================
    #
    # We have identified the structural elements, now contiue with the setup
    #
    # Print something for some reason?
    #
    if verbose:
        print "Created protein object -"
        print "\tNumber of residues in protein: %s" % myProtein.numResidues()
        print "\tNumber of atoms in protein   : %s" % myProtein.numAtoms()
    #
    # Set up all other routines
    #
    myRoutines = Routines(myProtein, verbose) #myDefinition)
    myRoutines.updateResidueTypes()
    myRoutines.updateSSbridges()
    myRoutines.updateBonds()
    myRoutines.setTermini()
    myRoutines.updateInternalBonds()

    myRoutines.applyNameScheme(Forcefield(ff, myDefinition, None))
    myRoutines.findMissingHeavy()
    myRoutines.addHydrogens()
    myRoutines.debumpProtein()

    #myRoutines.randomizeWaters()
    myProtein.reSerialize()
    #
    # Inject the information on hydrogen conformations in the HYDROGENS.DAT arrays
    # We get this information from ligand_titratable_groups
    #
    from src.hydrogens import hydrogenRoutines
    myRoutines.updateInternalBonds()
    myRoutines.calculateDihedralAngles()
    myhydRoutines = hydrogenRoutines(myRoutines)
    #
    # Here we should inject the info!!
    #
    myhydRoutines.setOptimizeableHydrogens()
    myhydRoutines.initializeFullOptimization()
    myhydRoutines.optimizeHydrogens()
    myhydRoutines.cleanup()
    myRoutines.setStates()

    #
    # Choose the correct forcefield
    #
    myForcefield = Forcefield(ff, myDefinition, None)
    if Lig:
        hitlist, misslist = myRoutines.applyForcefield(myForcefield)
        #
        # Can we get charges for the ligand?
        #
        templist=[]
        ligsuccess=False
        for residue in myProtein.getResidues():
            if isinstance(residue, LIG):
                templist = []
                Lig.make_up2date(residue)
                net_charge=0.0
                print 'Ligand',residue
                print 'Atom\tCharge\tRadius'
                for atom in residue.getAtoms():
                    if atom.mol2charge:
                        atom.ffcharge=atom.mol2charge
                    else:
                        atom.ffcharge = Lig.ligand_props[atom.name]["charge"]
                    #
                    # Find the net charge
                    #
                    net_charge=net_charge+atom.ffcharge
                    #
                    # Assign radius
                    #
                    atom.radius = Lig.ligand_props[atom.name]["radius"]
                    print '%s\t%6.4f\t%6.4f' %(atom.name,atom.ffcharge,atom.radius)
                    if atom in misslist:
                        misslist.pop(misslist.index(atom))
                        templist.append(atom)
                    #
                    # Store the charge and radius in the atom instance for later use
                    # This really should be done in a nicer way, but this will do for now
                    #
                    atom.secret_radius=atom.radius
                    atom.secret_charge=atom.ffcharge
                    #
                    #
                    
                charge = residue.getCharge()
                if abs(charge - round(charge)) > 0.01:
                    # Ligand parameterization failed
                    myProtein.residues.remove(residue)
                    raise Exception('Non-integer charge on ligand: %8.5f' %charge)
                else:
                    ligsuccess = 1
                    # Mark these atoms as hits
                    hitlist = hitlist + templist
                #
                # Print the net charge
                #
                print 'Net charge for ligand %s is: %5.3f' %(residue.name,net_charge)
        #
        # Temporary fix; if ligand was successful, pull all ligands from misslist
       # Not sure if this is needed at all here ...? (Jens wrote this)
        #
        if ligsuccess:
            templist = misslist[:]
            for atom in templist:
                if isinstance(atom.residue, Amino) or isinstance(atom.residue, Nucleic): continue
                misslist.remove(atom)                    
    
    if verbose:
        print "Created protein object (after processing myRoutines) -"
        print "\tNumber of residues in protein: %s" % myProtein.numResidues()
        print "\tNumber of atoms in protein   : %s" % myProtein.numAtoms()
    #
    # Create the APBS input file
    #
    import src.psize
    size=src.psize.Psize()

    method=""
    async=0
    split=0
    import inputgen_pKa
    igen = inputgen_pKa.inputGen(pdbfilename)
    #
    # For convenience
    #
    igen.pdie = pdie
    print 'Setting protein dielectric constant to ',igen.pdie
    igen.sdie=options.sdie
    igen.maps=maps
    if maps==1:
        print "Using dielectric and mobile ion-accessibility function maps in PBE"
        if xdiel:
            igen.xdiel = xdiel
        else:
            sys.stderr.write ("X dielectric map is missing\n")
            usage(2)
            sys.exit(0)
        if ydiel:
            igen.ydiel = ydiel
        else:
            sys.stderr.write ("Y dielectric map is missing\n")
            usage(2)
            sys.exit(0)
        if zdiel:
            igen.zdiel = zdiel
        else:
            sys.stderr.write ("Z dielectric map is missing\n")
            usage(2)
            sys.exit(0)
        
        print 'Setting dielectric function maps: %s, %s, %s'%(igen.xdiel,igen.ydiel,igen.zdiel)
        
        if kappa:
            igen.kappa = kappa
        else:
            sys.stderr.write ("Mobile ion-accessibility map is missing\n")
            usage(2)
            sys.exit(0)
            
        print 'Setting mobile ion-accessibility function map to: ',igen.kappa
        
        if sd:
            xdiel_smooth, ydiel_smooth, zdiel_smooth = smooth(xdiel,ydiel,zdiel)
            igen.xdiel = xdiel_smooth
            igen.ydiel = ydiel_smooth
            igen.zdiel = zdiel_smooth
    #
    # Return all we need
    #
    return myProtein, myRoutines, myForcefield,igen, ligand_titratable_groups, maps, sd

#
# --------------
#
            
if __name__ == "__main__":

    state=1
    if state==0:
        import pMC_mult
        #
        # System definition
        #
        groups=2
        acidbase=[-1,1] # 1 if group is a base, -1 if group is an acid
        intpkas=[3.4,0.0,0.0,0.0,0.0,
                 9.6,0.0,0.0,0.0,0.0] 
        is_charged_state=[1,0,0,0,0,
                          1,0,0,0,0]
        #
        # Automatic configuration from here on
        #
        states=len(intpkas)/groups #States per group
        state_counter=[]
        linear=[]
        names=[]
        for group in range(groups):
            #
            # Names
            #
            names.append('Group %d' %group)
            #
            # Add state_counter
            #
            state_counter.append(states)
            #
            # Matrix
            #
            for group2 in range(groups):
                for state1 in range(states):
                    for state2 in range(states):
                        if state1==0 and state2==0 and group!=group2:
                            linear.append(-2.3)
                        else:
                            linear.append(0.0)
        mcsteps=50000
        phstart=2.0
        phend=14.0
        phstep=0.1
        #
        # Call our little C++ module
        #
        FAST=pMC_mult.MC(intpkas,linear,acidbase,state_counter,is_charged_state)
        FAST.set_MCsteps(int(mcsteps))
        print 'Starting to calculate pKa values'
        pKavals=FAST.calc_pKas(phstart,phend,phstep)
        count=0
        print '\n****************************'
        print 'Final pKa values'
        pkas={}
        for name in names:
            pkas[name]={'pKa':pKavals[count]}
            print '%s pKa: %5.2f ' %(name,pKavals[count])
            count=count+1
        #
        # Write the WHAT IF pKa file
        #
        for name in names:
            pkas[name]['modelpK']=0.0
            pkas[name]['desolv']=0.0
            pkas[name]['backgr']=0.0
            pkas[name]['delec']=0.0
        import pKaTool.pKaIO
        X=pKaTool.pKaIO.pKaIO()
        X.write_pka('test.pdb.PKA.DAT',pkas)
        #
        # Get the charges
        #
        charges={}
        pH_start=pKavals[count]
        pH_step=pKavals[count+1]
        num_pHs=pKavals[count+2]
        count=count+2
        for name in names:
            charges[name]={}
            for x in range(int(num_pHs)):
                count=count+1
                pH=pKavals[count]
                count=count+1
                charges[name][pH]=pKavals[count]
                pH=pH+pH_step
            if pKavals[count+1]==999.0 and pKavals[count+2]==-999.0:
                count=count+2
            else:
                print 'Something is wrong'
                print pKavals[count:count+30]
                raise Exception('Incorrect data format from pMC_mult')
    elif state==1:
        #
        # Do a real pKa calculation
        #
        (protein, routines, forcefield,apbs_setup, ligand_titratable_groups, maps, sd), options = startpKa()
        import pka_routines
        mypkaRoutines = pka_routines.pKaRoutines(protein, routines, forcefield, apbs_setup, maps, sd,
                                                 pdbfile_name,
                                                 options=options)
        #
        # Debugging
        #
        #if debug:
        #    CM.init_protein(mypkaRoutines)
        #
        # Deal with ligands
        #
        #if ligand_titratable_groups:
        #    print "lig (before mypKaRoutines) ", ligand_titratable_groups['titratableatoms']
        #    mypkaRoutines.insert_new_titratable_group(ligand_titratable_groups)
        #
        # What should we do?
        #
        if options.desolvation_res:
            print 'Doing desolvation for single residues',options.desolvation_res
            mypkaRoutines.calculate_desolvation_for_residues(residues=options.desolvation_res)
        else:
            print 'Doing full pKa calculation'
            mypkaRoutines.runpKa()
    elif state==2:
        #
        # Just assign charges
        #
        (protein, routines, forcefield,apbs_setup, ligand_titratable_groups,maps,sd),options = startpKa()
        for chain in protein.getChains():
            for residue in chain.get("residues"):
                for atom in residue.get("atoms"):
                    atomname = atom.get("name")
                    charge, radius = forcefield.getParams(residue, atomname)
                    print '%2s %4s %3d %4s %5.2f %5.2f' %(chain.chainID,residue.name,residue.resSeq,atomname,charge,radius)
