#!/usr/local/bin/python

#
# Program: loadDAG.py
#
# Purpose: to load the input file for a DAG into database tables
#   DAG_Node, DAG_Edge, DAG_Closure
#
# User Requirements Satisfied by This Program:
#
# System Requirements Satisfied by This Program:
#
#   Usage: see USAGE definition below
#
#   Uses:
#
#   Envvars:
#
#   Inputs:
#       1. tab-delimitd input file with the following columns:
#           Accession ID of object in child node (required)
#           Label for child node (optional)
#           Label for edge type (optional)
#           Accession ID of object in parent node (optional)
#             - no parent ID indicates child is a root node
#       2. mode (full or incremental)
#       3. primary ke of DAG being loaded
#           (why not the name?)
#
#   Outputs:
#
#   Exit Codes:
#       0. script completed successfully, data loaded okay
#       1. script halted, data did not load, error noted in stderr
#           (database is left in a consistent state)
#
#   Other System Requirements:
#
# Assumes:
#   We assume no other users are adding/modifying database records during
#   the run of this script.
#
# Implementation:
#   Modules:
#
# History
#
#
# 05/17/2004 lec
#	- TR 6806/enhanced DAG_Closure table.  Added _AncestorObject_key and _DescendentObject_key
#
# 04/02/2003 lec
#	- added os.environ calls
#	- changed bcp delimiter to pipe (|)
#

import sys      # standard Python libraries
import types
import string
import getopt
import os

import Log      # MGI-written Python libraries
import vocloadlib
import html

DEBUG = 0
mgiType = os.environ['MGITYPE']

USAGE = '''Usage: %s [-f|-i][-l <file>] <server> <db> <user> <pwd> <key> <input>
    -f | -i : full load or incremental load? (default is full)
    -n  : use no-load option (log changes, but don't execute them)
    -l  : name of the log file to create (default is stderr only)
    server  : name of the database server
    db  : name of the database
    user    : database login name
    pwd : password for 'user'
    key : _DAG_key to load
    input   : DAG input file
''' % sys.argv[0]

###--- Exceptions ---###

error = 'DAGLoad.error'

unknown_mode = 'unknown load mode: %s'

###--- SQL INSERT Statements ---###

    # templates placed here for readability of the code, and formatted for
    # readability of the log file

INSERT_NODE = '''insert DAG_Node (_DAG_key, _Node_key, _Object_key, _Label_key)
    values (%d, %d, %d, %d)'''

BCP_INSERT_NODE = '''%d|%d|%d|%d||\n'''

INSERT_EDGE = '''insert DAG_Edge (_Edge_key, _DAG_key, _Parent_key,
        _Child_key, _Label_key, sequenceNum)
    values (%d, %d, %d,
        %d, %d, %d)'''

BCP_INSERT_EDGE = '''%d|%d|%d|%d|%d|%d||\n'''

INSERT_CLOSURE = '''insert DAG_Closure (_DAG_key, _MGIType_key, _Ancestor_key, _Descendent_key, _AncestorObject_key, _DescendentObject_key, _AncestorLabel_key, _DescendentLabel_key)
    values (%d, %s, %d, %d, %d, %d)'''

BCP_INSERT_CLOSURE = '''%d|%s|%d|%d|%d|%d|%d|%d||\n'''

###--- Classes ---###

class DAGLoad:
    # IS: a 'data load' for the DAG_Node, DAG_Edge, and DAG_Closure tables
    #   in the MGI database
    # HAS: a database key identifying which DAG we are loading, a set of
    #   nodes (each of which represents an object in the db), and a
    #   set of edges between them.  Each node and each edge may have
    #   a label.  The object associated with each node is identified
    #   by its accession ID.
    # DOES: loads the data file representing a DAG into the corresponding
    #   database structures, doing either a full delete-and-reload or
    #   an incremental load which only updates changed portions.
    # Notes: This load has no particulary interesting OO design.  I
    #   implemented it as a class because it is convenient.  It can be
    #   easily invoked from the command-line or imported as a Python
    #   module and executed from another Python script.

    ###--- Public Methods ---###

    def __init__ (self,
        filename,   # string; path to the file containing DAG info
        mode,       # string; 'full' or 'incremental' load?
        dag,        # string dag name or integer dag key; the DAG
                #   to be loaded
        log,     # log.Log object; what to use for logging
        passwordFile
        ):
        # Purpose: constructor
        # Returns: nothing
        # Assumes: nothing
        # Effects: queries the database for various DAG attributes,
        #   does logging to 'log', reads the data from 'filename'
        # Throws: 1. 'error' if the 'mode' is invalid; 2. propagates
        #   'vocloadlib.error' if other errors are discovered
        # Attributes:
        #   log
        #   dag_key, dag_name
        #   vocab_key, vocab_name
        #   mode
        #   filename, datafile
        #   mgitype_key
        #   objToNode
        #   childrenOf
        #   max_node_key
        #   max_edge_key

        # remember the log

        self.log = log

        # open output BCP files

        self.passwordFile = passwordFile

        self.dagEdgeBCPFileName    = os.environ['DAG_EDGE_BCP_FILE']
        self.dagNodeBCPFileName    = os.environ['DAG_NODE_BCP_FILE']
        self.dagClosureBCPFileName = os.environ['DAG_CLOSURE_BCP_FILE']
                                                         
        self.dagEdgeBCPFile    = open( self.dagEdgeBCPFileName   , 'w')
        self.dagNodeBCPFile    = open( self.dagNodeBCPFileName   , 'w')
        self.dagClosureBCPFile = open( self.dagClosureBCPFileName, 'w')

        # flags which indicate whether or not to load BCP files
        self.loadEdgeBCP=0
        self.loadNodeBCP=0
        self.loadClosureBCP=0

        # find DAG key and name (propagate error if invalid)

        if type(dag) == types.StringType:
            self.dag_name = dag
            self.dag_key = vocloadlib.getDagKey (dag)
        else:
            self.dag_name = vocloadlib.getDagName (dag)
            self.dag_key = dag

        # find vocab key and name (propagate error if invalid)

        result = vocloadlib.sql (
            '''select voc.name, voc._Vocab_key
            from VOC_VocabDAG vocdag, VOC_Vocab voc
            where vocdag._DAG_key = %d
                and vocdag._Vocab_key = voc._Vocab_key''' % \
            self.dag_key)
        self.vocab_key = result[0]['_Vocab_key']
        self.vocab_name = result[0]['name']

        # write log header

        self.log.writeline ('=' * 40)
        self.log.writeline ('Loading %s Vocabulary, %s DAG...' % \
            (self.vocab_name, self.dag_name))
        self.log.writeline (vocloadlib.timestamp ('Init Start:'))

        # check that the mode is valid

        if mode not in [ 'full', 'incremental' ]:
            raise error, unknown_mode % mode
        self.mode = mode

        # remember the filename and read the data file

        self.filename = filename
        self.datafile = vocloadlib.readTabFile (filename,
            [ 'childID', 'node_label', 'edge_label', 'parentID' ])

        # remember the MGI Type (for DAG_DAG)

        self.mgitype_key = vocloadlib.VOCABULARY_TERM_TYPE

        self.objToNode = {} # object key -> node key
	self.nodeLabel = {} # node key -> label key
        self.childrenOf = {}    # parent key -> [ children's keys ]
        self.max_node_key = None    # max assigned _Node_key
        self.max_edge_key = None    # max assigned _Edge_key

        self.log.writeline (vocloadlib.timestamp ('Init Stop:'))

        return

    def go (self):
        # Purpose: runs the load
        # Returns: nothing
        # Assumes: nothing
        # Effects: nothing
        # Throws: raises 'error' if any exceptions occur

        try:
           self.openDiscrepancyFile()
           if self.mode == 'full':
               self.goFull()
           else:
               self.goIncremental()
           self.closeDiscrepancyFile()
           self.closeBCPFiles()
           self.loadBCPFiles()
        except:
           # raise 'error' with whatever the descriptive message
           # was originally
           raise error, sys.exc_value

        self.log.writeline ('=' * 40)

        return

    def openDiscrepancyFile ( self ):
        # Purpose: opens discrepancy file, and begins writing the HTML
        #          tags for the report content
        # Returns: nothing
        # Assumes: user executing program has write access in output directory;
        # Effects: discrepancy files are open for writing
        # Throws:  propagates all exceptions opening files

        # open the discrepancy file
        self.dagDiscrepFileName = os.environ['DAG_DISCREP_FILE']
        self.dagDiscrepFile     = open( self.dagDiscrepFileName     , 'w')

        # now write HTML header information
        self.dagDiscrepFile.write ( html.getStartHTMLDocumentHTML ( "DAG Discrepancy Report" ) )
        self.dagDiscrepFile.write ( html.getStartTableHTML () )
        self.dagDiscrepFile.write ( html.getStartTableRowHTML () )
        self.dagDiscrepFile.write ( html.getTableHeaderLabelHTML ( "Accession ID" ) )
        self.dagDiscrepFile.write ( html.getTableHeaderLabelHTML ( "Message" ) )
        self.dagDiscrepFile.write ( html.getEndTableRowHTML () )

    def closeDiscrepancyFile ( self ):
        # Purpose: writes HTML tags to close the table and document tags
        #          and physically closes discrepancy file
        # Returns: nothing
        # Assumes: discrepancy file is open
        # Effects: discrepancy files are closed
        # Throws:  propagates all exceptions closing files

        # write html tags to end the table and html document
        self.dagDiscrepFile.write ( html.getEndTableHTML () )
        self.dagDiscrepFile.write ( html.getEndHTMLDocumentHTML ( ) )

        # now, close the file
        self.dagDiscrepFile.close ()

    def writeDiscrepancyFile (self, accID, msg ):
        # Purpose: write a record to the discrepancy file
        # Returns: nothing
        # Assumes: discrepancy file is open and writeable
        # Effects: report output
        # Throws:  propagates any exceptions raised 
        self.dagDiscrepFile.write ( html.getStartTableRowHTML () )
        self.dagDiscrepFile.write ( html.getCellHTML ( accID ) )
        self.dagDiscrepFile.write ( html.getCellHTML ( msg   ) )
        self.dagDiscrepFile.write ( html.getEndTableRowHTML () )

    def loadBCPFiles (self):
        # Purpose: runs the BCP load
        # Returns: nothing
        # Assumes: nothing
        # Effects: nothing

        bcpLogFile   = os.environ['BCP_LOG_FILE']
        bcpErrorFile = os.environ['BCP_ERROR_FILE']

        if not vocloadlib.NO_LOAD:
           if self.loadEdgeBCP:
              vocloadlib.loadBCPFile ( self.dagEdgeBCPFileName, bcpLogFile, bcpErrorFile, 'DAG_Edge', self.passwordFile  )

           if self.loadNodeBCP:
              vocloadlib.loadBCPFile ( self.dagNodeBCPFileName, bcpLogFile, bcpErrorFile, 'DAG_Node', self.passwordFile  )

           if self.loadClosureBCP:
              vocloadlib.loadBCPFile ( self.dagClosureBCPFileName, bcpLogFile, bcpErrorFile, 'DAG_Closure', self.passwordFile  )


    def closeBCPFiles ( self ):
        # Purpose: closes BCP files
        # Returns: ?
        # Assumes: ?
        # Effects: ?
        self.dagEdgeBCPFile.close()    
        self.dagNodeBCPFile.close()    
        self.dagClosureBCPFile.close() 


              ###--- Private Methods ---###

    def goFull (self):
        # PRIVATE METHOD - should only be invoked by self.go()
        #
        # Purpose: run a full load (delete existing entries from the
        #   database and load the complete data set)
        # Returns: nothing
        # Assumes: nothing
        # Effects: does a complete delete-and-reload of data for this
        #   DAG from the MGI database
        # Throws: nothing
        # Notes: At this point, we do everything directly in SQL.
        #   Given time, it probably would be worthwhile to convert
        #   this over to use BCP files, thus improving efficiency.

        self.log.writeline (vocloadlib.timestamp ( 'Full DAG Load Start:'))

        # delete existing information for the structure of this DAG.
        count = vocloadlib.countNodes (self.dag_key)
        vocloadlib.deleteDagComponents (self.dag_key, self.log)
        self.log.writeline ('   deleted all (%d) remaining nodes' % count)

        # load dictionaries of labels and term IDs for the vocab which
        # contains this DAG.  (for efficiency, rather than looking
        # them up individually from the db)

        labels = vocloadlib.getLabels()     # label -> label key

        # ids[primary accID] -> object key
        ids = vocloadlib.getTermIDs(self.vocab_key)

        self.objToNode = {}
        self.childrenOf = {}
        self.roots = []

        # now that we're ready to add DAG elements, we need to see
        # what the highest remaining primary keys are in the node
        # and edge tables.  We use the max() function to ensure that
        # we start with 0 if getMax() returns None.

        self.max_node_key = max(0, vocloadlib.getMax ('_Node_key', 'DAG_Node'))
        self.max_edge_key = max(0, vocloadlib.getMax ('_Edge_key', 'DAG_Edge'))

        # We need to keep track of which nodes we've added to DAG_Node
        # so we'll use a dictionary to remember which keys we add:

        nodesAdded = {}     # dict; node_key -> 1, if added
        lineNum = 0         # line number in data file

        for record in self.datafile:
            lineNum = lineNum + 1

            # toss the four fields in the row into variables:

            childID = record['childID']
            node_label = record['node_label']
            edge_label = record['edge_label']
            parentID = string.rstrip(record['parentID'])

            # check that IDs and labels are valid, and look up the corresponding keys:

            errors = [] # list of strings (data errors found)

            # if we have a valid childID, look up its key:

            if not childID:
                errors.append ('Child ID is required')
            elif not ids.has_key (childID):
                errors.append ('Unknown child ID %s' % childID)
            else:
                [termKey, isObsolete, term, termFound] = ids[childID]
                child_key = termKey

            # if we have a valid parentID, look up its key.  If we
            # have no parentID, then this child is a root node.

            if not parentID:
                parent_key = None
                if child_key not in self.roots:
                    self.roots.append (child_key)
            elif not ids.has_key (parentID):
                parent_key = None
                errors.append ('Unknown parent ID %s' % parentID)
            else:
                [termKey, isObsolete, term, termFound] = ids[parentID]
                parent_key = termKey

            # if we have a label for this (child) node, then find
            # its label key.  If not, it defaults to "not
            # specified".

            if not node_label:
                node_label_key = vocloadlib.NOT_SPECIFIED
            elif not labels.has_key (node_label):
                errors.append ('Unknown node label "%s"' % node_label)
            else:
                node_label_key = labels[node_label]

            # if we have a label for this edge, then find its key.
            # if not, it defaults to "not specified".

            if not edge_label:
                edge_label_key = vocloadlib.NOT_SPECIFIED
            elif not labels.has_key (edge_label):
                errors.append ('Unknown edge label "%s"' % edge_label)
            else:
                edge_label_key = labels[edge_label]

            # now, if this (child) node has a parent, we need to
            # verify that it isn't a duplicate record.  To do
            # this, we examine the list of children for the given
            # parent key.

            if parent_key and self.childrenOf.has_key(parent_key):
                if child_key in self.childrenOf[parent_key]:
                    errors.append (
                        'Parent has duplicate child')

            # now if we've turned up any errors with this record,
            # we will report them in the log.  We will simply skip
            # this data line and proceed with the rest of the load

            if errors:
                msg = 'Input File: %s - ERROR: Skipped line %d:' % ( self.filename, lineNum )
                for error in errors:
                    msg = msg + " " + error
                self.writeDiscrepancyFile ( childID, msg )
                self.log.writeline ( msg )
                continue    # to next line

            # now, remember that this child node is a child of
            # its parent, if it has one

            if parent_key:
                if not self.childrenOf.has_key (parent_key):
                    self.childrenOf[parent_key] = []
                self.childrenOf[parent_key].append (child_key)

            # We now need to convert the _Object_keys for the
            # child and parent to be their corresponding node
            # keys.  If either (or both) have no node key, then
            # we must allocate a new one.

            if not self.objToNode.has_key (child_key):
                self.max_node_key = self.max_node_key + 1
                self.objToNode [child_key] = self.max_node_key

            if parent_key and not self.objToNode.has_key (parent_key):
                self.max_node_key = self.max_node_key + 1
                self.objToNode [parent_key] = self.max_node_key

            # if we haven't already added a node record for this
            # child, then we need to add one now

            child_node_key = self.objToNode [child_key]
            if not nodesAdded.has_key (child_node_key):
                self.addNode (child_node_key, child_key, node_label_key)
                nodesAdded[child_node_key] = 1
		self.nodeLabel [child_node_key] = node_label_key

            # finally, if this child has a parent then we need to
            # add the edge between them

            if parent_key:
                self.addEdge (self.objToNode[parent_key],
                    child_node_key, edge_label_key,
                    len(self.childrenOf[parent_key]))

        # and, after all the nodes and edges have been loaded, it's
        # time to recompute the full transitive closure of the DAG
        # and update the database accordingly.

        self.updateClosure()
        self.log.writeline (vocloadlib.timestamp ('Full DAG Load Stop:'))
        return

    def getNodeKey (self,
        object_key  # integer; what object's node key do we want?
        ):
        # PRIVATE METHOD - used for convenience in the
        #   self.updateClosure() method.
        #
        # Purpose: find the node key which corresponds to the given
        #   'object_key'
        # Returns: integer, or None if object_key is None
        # Assumes: self.objToNode.has_key (object_key)
        # Effects: nothing
        # Throws: nothing

        return self.objToNode [object_key]

    def updateClosure (self):
        # PRIVATE METHOD - used by self.goFull() and
        #   self.goIncremental() methods
        #
        # Purpose: recompute the transitive closure for this DAG and
        #   adjust the DAG_Closure table accordingly
        # Returns: nothing
        # Assumes: nothing
        # Effects: alters DAG_Closure, currently by doing a delete-
        #   and-reload on the table for this particulary DAG
        # Throws: nothing
        # Notes: This function uses the following interesting
        #   attributes of self:
        #       self.roots: list of parent-less object keys
        #       self.childrenOf: dict[parent object key] = 
        #               [ child object keys ]
        #   At some point in the future, we should revise this
        #   a bit, as 'dag' is unnecessarily large because we're
        #   using the node keys directly.  It would be better to
        #   map the node keys onto 1..n when building 'dag', then
        #   compute the closure, and map them back from 1..n to
        #   the node keys.

        self.log.writeline (vocloadlib.timestamp ('Closure start:'))

        # first, delete the existing closure for this DAG:

        vocloadlib.nl_sqlog ('delete from DAG_Closure where _DAG_key=%d' % self.dag_key, self.log)

        # build the dag as a list of lists where:
        #   dag[0] = list of parent-less term keys
        #   dag[n] = list of child terms of term n, for n>0
        dag = [self.roots]
	#self.log.writeline ('dag = [self.roots] %s' % dag)
        dag = dag + [ [] ] * self.max_node_key
	#self.log.writeline('DAG before:')
	#self.log.writeline(dag)
	#self.log.writeline(self.childrenOf.items() )
	#self.log.writeline('ITERATE THRU childrenof.items()')
        for (object_key, children) in self.childrenOf.items():
	    #self.log.writeline('objectKey: %s, children %s' % (object_key, children))
            if object_key:
                dag[object_key] = children
	#self.log.writeline('DAG after:')
        #self.log.writeline(dag)
        # now actually compute the closure...

        self.log.writeline (vocloadlib.timestamp ('Start Closure Computation: '))
        closure = getClosure (dag, self.log)
        self.log.writeline (vocloadlib.timestamp ('Stop Closure Computation: '))

        # and add each ancestor-descendant edge to the database.
	# we store both the _Node_key and the _Term_key for the Ancestor and Descendent in the DAG_Closure table
	# so, we need to translate each _Term_key to its appropriate _Node_key
        for (node, children) in closure.items():
	    if DEBUG:
		self.log.writeline('Node: %s Children %s' % (node, children))
            if node > 0:
               for child in children:
                   # write the BCP file 
                   self.loadClosureBCP=1
                   self.dagClosureBCPFile.write (BCP_INSERT_CLOSURE % (self.dag_key, mgiType, self.getNodeKey(node), self.getNodeKey(child), node, child, self.nodeLabel[self.getNodeKey(node)], self.nodeLabel[self.getNodeKey(child)]) )

        self.log.writeline (vocloadlib.timestamp ('Closure stop:'))
        return
        
    def addNode (self,
        node_key,   # integer; primary key for this node
        object_key, # integer; object key assoc. with this node
        label_key   # integer; key for label assoc. with this node
        ):
        # PRIVATE METHOD - used by self.goFull() and
        #   self.goIncremental()
        #
        # Purpose: add a record to DAG_Node with the given keys
        # Returns: nothing
        # Assumes: nothing
        # Effects: adds a record to DAG_Node
        # Throws: propagates any exceptions from vocloadlib.nl_sqlog()

        if DEBUG:
           self.log.writeline (INSERT_NODE % (self.dag_key, node_key,
                                object_key, label_key) )
        self.loadNodeBCP=1
        self.dagNodeBCPFile.write(BCP_INSERT_NODE % (node_key, self.dag_key,
                                  object_key, label_key) )
        return

    def addEdge (self,
        parent_node_key,    # integer; node key of parent node
        child_node_key,     # integer; node key of child node
        label_key,      # integer; key of label
        seqNum          # integer; sequence number of this
                    #   child for this parent
        ):
        # PRIVATE METHOD - used by self.goFull() and
        #   self.goIncremental()
        #
        # Purpose: add a record to DAG_Edge with the given keys
        # Returns: nothing
        # Assumes: nothing
        # Effects: adds a record to DAG_Edge; increments
        #   self.max_edge_key
        # Throws: propagates any exceptions from vocloadlib.nl_sqlog()

        self.max_edge_key = self.max_edge_key + 1
        if DEBUG:
            self.log.writeline (INSERT_EDGE % (
                self.max_edge_key,
                self.dag_key,
                parent_node_key,
                child_node_key,
                label_key,
                seqNum))


        # write the edge BCP file
        self.loadEdgeBCP=1
        self.dagEdgeBCPFile.write (BCP_INSERT_EDGE % (
                                   self.max_edge_key,
                                   self.dag_key,
                                   parent_node_key,
                                   child_node_key,
                                   label_key,
                                   seqNum) )
        return

    def goIncremental (self):
        # PRIVATE METHOD - called only by self.go()

        # For now, call goFull() since we are going to
        # try always doing delete/inserts
        self.goFull()
        return

###--- Private Functions ---###

def getClosure (
    dag, # the DAG, as a list of lists.
        #   list[0] = list of keys of parent-less nodes
        #   list[i] = list of keys of children of node i, for i>0
    log
    ):
    # Purpose: get the closure for the given 'dag'
    # Returns: dictionary where d[key i] = list of keys of all descendants
    #   of the node with key i
    # Assumes: 'dag' has no cycles, otherwise results will be incorrect.
    # Effects: nothing
    # Throws: nothing
    # Notes: This closure computation is based on the one in WTS, which
    #   was derived by Joel.  It is based on a recursive depth-first
    #   search of the DAG, caching intermediate results along the way.
    # Example:
    #   dag = [ [ 2 ],              2
    #       [ ],                   / \
    #       [ 1, 4 ],             1   4
    #       [ ],                  |
    #       [ 3 ],                3
    #       ]
    #   getClosure (dag) yields:
    #       { 0 : [ 2,1,4,3 ],
    #         1 : [ ],
    #         2 : [ 1,4,3 ],
    #         3 : [ ],
    #         4 : [ 3 ],
    #       }

    start = 0   # start with the list of parent-less nodes, so we will
            # do the closure for each (thus arriving at the
            # closure of the whole DAG)

    closure = {}    # the closure of the DAG, as computed so far
            #   closure[i] = list of keys of descendants of the node with key i

    getNodeClosure (dag, start, closure)
    #for a in closure.keys():
    #	log.writeline('ancestor: %s descendants: %s' % (a, closure[a]))
    return closure

def getNodeClosure (
    dag,        # the DAG, same format as for 'getClosure()' function
    i,      # integer index into 'dag', telling us where to start
            #   computing the closure (at what node).  To
            #   do the full DAG, i=0 so we start with all root
            #   nodes.
    closure     # dict as described in 'getClosure()' function; the
            #   closure as computed so far
    ):
    # Purpose: compute the closure of all nodes which are children of node
    #   'i' and store it in 'closure'
    # Returns: nothing
    # Assumes: 'dag' has no cycles
    # Effects: updates 'closure'
    # Throws: nothing
    # Notes: This function should only be invoked by the getClosure() 
    #   function, and should not be invoked separately.

    if closure.has_key (i):     # if we've already computed the
        return          # closure of this node, bail out

    # the closure of node 'i' will include all the children of 'i', plus
    # the closure of each child of 'i' (recursively traversing the DAG)

    closure[i] = dag[i][:]
    for child in dag[i]:
        getNodeClosure (dag, child, closure)
        for descendant in closure[child]:
            if not descendant in closure[i]:
                closure[i].append (descendant)
    return

###--- Main Program ---###

if __name__ == '__main__':
    try:
        options, args = getopt.getopt (sys.argv[1:], 'finl:')
    except getopt.error:
        print 'Error: Unknown command-line options/args'
        print USAGE
        sys.exit(1)

    if len(args) != 6:
        print 'Error: Wrong number of arguments'
        print USAGE
        sys.exit(1)

    mode = 'full'
    log = Log.Log ()
    [ server, database, username, passwordfilename ] = args[:4]
    [ dag_key, input_file ] = args[4:]
    dag_key = string.atoi (dag_key)

    noload = 0
    for (option, value) in options:
        if option == '-f':
            mode = 'full'
        elif option == '-i':
            mode = 'incremental'
        elif option == '-n':
            vocloadlib.setNoload()
            noload = 1
        else:
            log = Log.Log (filename = value)

    if noload:
        log.writeline ('Operating in NO-LOAD mode')

    password = string.strip(open(passwordfilename, 'r').readline())
    vocloadlib.setupSql (server, database, username, password)
    load = DAGLoad (input_file, mode, dag_key, log, passwordfilename)
    load.go()
    vocloadlib.unsetupSql ()
