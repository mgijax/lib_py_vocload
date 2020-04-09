# Ontology.py
#
# Classes:
#	OboTerm
#	OboOntology
#	OboParser
#	OboLoader

# Oct 2?, 2013 (jak)
# Changed OboOntology to support dynamic changes to the ontology after
# reading/parsing the ontology from a file.
# Modified Methods
#     addNode
#     addRelationship
#     setTermAttribute
#     getRoot replaced by getRoots
# New Methods
#     removeNode
#     removeRelationship
# Changed OboLoader class to use these new/modified methods
#
# Oct 8, 2013 (jak)
# Changed OboParser to remove comments (! to EOL), including changes to
# OboLoader to not depend on those !'s.
# Also added a cullCrossEdges option to OboLoader.
#
# Feb 23, 2011 (joel)
# Remove restriction that ontology has only one root. Newer OBO files
# will include some, but not all, terms from other ontologies. E.g.,
# the protein ontology contains some GO terms because some PRO terms
# reference GO terms.
#

#------------------------------------

import sys
import re
import types
import vocloadDAG

#------------------------------------
#
# Base class for an OboTerm, the node objects in an OboOntology.
# Subclass this if you need more functionality for terms, and pass your subclass
#   to the OboOntology constructor.
#
# Use OboOntology.setTermAttribute( term, ...) to set attributes of OboTerms
#
class OboTerm(object):
    def __init__(self, id, name, ontol):
        self.id = id
        self.name = name
        self.namespace = None
        self.is_obsolete = False
        self.is_nsroot = False		# is a root in a namespace, not needed?
        self.ontology = ontol

    def getUrl(self):
        tmplt = getattr(self.ontology.config, 'linkurl', None)
        if tmplt is None:
            return None
        return tmplt % self.id

    def __str__(self):
        s = self.id + " " + self.name
        if self.is_obsolete: s = s + "(obsolete)"
        return s

#------------------------------------
"""
An OboOntology is a DAG whose nodes are OboTerms (or subclasses thereof).
Hence each node has:
    id			(string)
    name		(string)
    namespace		(string)
    is_obsolete		(boolean)

Edges (relationships between nodes) have a relationshipType (a string), 
typically "is_a", "part_of", etc.

An OboOntology keeps track of various things about the ontology:
    header	      - dict: keyword -> value from the OBO header stanza
    namespaces	      - dict: namespace (string) -> 0 (value not used)
    relationshipTypes - dict: relationshiptype -> 0 (value not used)
    nsRoots	      - dict: namespace (string) -> list of root OboTerms in
                                                   that namespace
        Note the concept of "root" here:
        a term/node is a root if it has no parents in any namespace.
        One could imagine the concept of "root relative to a namespace"
        - where a term could be a root in a namespace if it has no parents
        *in that namespace* - we have not implemented it this way.

In general, most OboOntology methods pass terms by passing IDs or OboTerm objs.
(compare to DAG methods which take/return term objects themselves)

In the DAG representation,
the "in" edges to a node come from the node's parents, see vocloadDAG.iterInEdges()
the "out" edges from a node go to the node's children, see vocloadDAG.iterOutEdges()
"""
class OboOntology(vocloadDAG.DAG):
    def __init__(self, nodeType=OboTerm):
        # nodeType should be a subclass of OboTerm
        super(OboOntology, self).__init__()
        self.id2term = {}	# id (string) -> OboTerm object
        self.namespaces = {}	# ns (string) -> 0 (value meaningless)
                                #  all namespaces seen so far

        self.relationshipTypes = {} # reltype (string) -> 0 (value meaningless)
                                #   all relationshipTypes seen so far

        self.header = {}	# obo file header keyword (string) -> val (str)
                                # (header info from the OBO file)

        self.nsRoots = {}	# namespace (string) -> [ root OboTerms ]
        self.nodeType = nodeType  # type of term objects to instantiate

    def getNamespaces(self):
    # Return list of namespaces (list of string))
        return list(self.namespaces.keys())

    def getRelationshipTypes(self):
    # Return list of RelationshipTypes (list of string))
        return list(self.relationshipTypes.keys())

    def setAttribute(self, attr, value):
    # Set attribute of the OboOntology
        if type(value) is list:
            if len(value) == 0:
                value = ""
            elif len(value) == 1:
                value = value[0]
        self.header[attr] = value

    def getAttribute(self, attr, dflt=""):
    # get attribute of the OboOntology
        return self.header.get(attr,dflt)

    def addTerm(self, id, name=None):
    # Add an OboTerm to the ontology w/ the specified ID (string) if it is not
    #     already in the Ontology
    # Set/Update OboTerm's name if not None
    # Return the Oboterm, (either newly created or already existing)
        t = self.id2term.get(id,None)
        if t is None:		# ID is not in this OboOntology yet
            t = self.nodeType(id,name,self)
            self.id2term[id] = t
            self.addNode(t)
        else:			# existing term
            if name is not None:
                t.name = name
        self.nsRoots.clear()	# clear roots cache
        return t

    def removeTerm(self, term):
    # Remove the specified term from the ontology
    # This removes all relationships involving this term too.
    # Term can be an ID (string) or an OboTerm object itself.
    # Assumes the term is in the ontology

        if type(term) is str:	# if term is ID
            term = self.getTerm(term)
        id = term.id

        # loop through parents and children and remove relationships
        for p in self.getParents( term):
            self.removeRelationship( p, term)

        for c in self.getChildren( term):
            self.removeRelationship( term, c)

        self.removeNode( term)
        self.id2term.pop( id)
        self.nsRoots.clear()	# clear roots cache

    def hasTerm(self, id):
    # Return True if we have a term w/ the specified ID (string)
        return id in self.id2term

    def getTerm(self, id):
    # Return a term object for the specified ID (string)
    # Raises KeyError if there is no term w/ that ID
        return self.id2term[id]

    def setTermAttribute(self, term, attr, value):
    # Set an attr of a term.
    # term can be an ID (string) or an OboTerm object itself
    # It is important to use this method to set term attributes so
    #   we can keep track of various aspects of the Ontology.

        if type(term) is str:	# if term is ID
            term = self.getTerm(term)

        if attr == "id":
            raise Exception("Cannot set id attribute.")
        elif attr == "namespace":	# handle namespace counts
            if value != None:
                self.namespaces[value] = 0

        setattr(term,attr,value)

    def addRelationship(self, child, rel, parent):
    # Add the specified relationship to the ontology.
    # rel (string) is the relationship type
    # parent and child can be either IDs (string)) or OboTerms themselves
    # Assumes child and parent refer to existing OboTerms in the ontology.
        if type(parent) is str:	# if parent is ID
            parent = self.getTerm(parent)
        if type(child) is str:	# if child is ID
            child = self.getTerm(child)

        self.relationshipTypes[rel] = 0
        self.addEdge(parent, child, rel, checkCycles=False)
        self.nsRoots.clear()	# clear roots cache

    def removeRelationship(self, parent, child):
    # Remove the specified relationship from the ontology.
    # parent and child can be either IDs (string)) or OboTerms themselves
        if type(parent) is str:	# if parent is ID
            parent = self.getTerm(parent)
        if type(child) is str:	# if child is ID
            child = self.getTerm(child)

        self.removeEdge(parent, child)
        self.nsRoots.clear()	# clear roots cache

    def getRoots(self, ns=None):
    # Return a list of root nodes [OboTerms]
    # ns (string) is a namespace. If specified, just return list of roots
    #    in that namespace.
    # Does not consider obsolete terms as roots.
        if len(self.nsRoots) == 0:
            self.cacheRoots()
        if ns is None:
                        # flatten the list roots for each namespace
            return [r for sublist in list(self.nsRoots.values()) for r in sublist]
        else:
            return self.nsRoots[ns]

    def cacheRoots(self):
        '''
        Find/cache the root nodes.
        '''
        for t in self.iterNodes():	# clear all root tags
            t.is_nsroot = False

        # rebuild self.nsRoots - dict mapping namespace to list of root OboTerms
        self.nsRoots.clear()
        for ns in self.getNamespaces():
            self.nsRoots[ns] = []

        for r in self.iterRoots():
            if r.is_obsolete:
                continue
            ns = r.namespace
            self.nsRoots[ ns].append(r)
            r.is_nsroot = True

#------------------------------------
#
# OboParser
#
# Rudimentary parser for OBO format files. Parses lines into groups
# called stanzas. Passes each stanza to a provided function that processes
# the stanza. A stanza is simply a dict mapping string keys to list-of-string 
# values. 
#
# Example. Here's a stanza from an OBO file:
#
# [Term]
# id: GO:0000001
# name: mitochondrion inheritance
# namespace: biological_process
# def: "The distribution of ..." [GOC:mcc, PMID:10873824, PMID:11389764]
# exact_synonym: "mitochondrial inheritance" []
# is_a: GO:0048308 ! organelle inheritance
# is_a: GO:0048311 ! mitochondrion distribution
# relationship: part_of GO:12345 ! some comment
# relationship: part_of GO:23456 ! some comment
#
# Here's the dict that would be passed to the processing function:
#  (note comments are removed)
#
# {
# "__type__" : [ "Term" ]
# "id" : [ "GO:0000001" ]
# "name" : [ "mitochondrion inheritance" ]
# "namespace" : [ "biological_process" ]
# "def" : [ '"The distribution ..." [GOC:mcc, PMID:10873824, PMID:11389764]' ]
# "exact_synonym" : [ '"mitochondrial inheritance" []' ]
# "is_a" : [ "GO:0048308 ", "GO:0048311 " ]
# "relationship" : [ "part_of GO:12345 ", "part_of GO:23456 " ]
# }
#
# Things to note about the stanza:
#  The stanza's type is passed under the pseudo key "__type__".
#  (The header stanza has no type.)
#  Lines in the file having the same key are combined into a list under that
#  key. E.g., the two "is_a" lines in the example.
#  ALL values in the dict are lists, even if only a single value is allowed by OBO.
#  The stanza dict is reused for each new stanza. Thus the user's processing
#  function must copy any needed information out of the stanza before returning.
#

TYPE = "__type__"

class OboParser(object):
    def __init__(self, stanzaProcessor):
    # stanzaProcessor - call back function that is passed the stanza dict
    #		(above) for each stanza after it is parsed.
        self.fd = None
        self.count = 0
        self.stanza = {}
        self.stanzaProcessor = stanzaProcessor

    def parseFile(self, file):
        if type(file) is str:
            self.fd = open(file, 'r')
        else:
            self.fd = file
        self.__go__()
        if type(file) is str:
            self.fd.close()

    def __finishStanza__(self):
        if len(self.stanza) > 0:
            self.count += 1
            if self.count == 1 and TYPE not in self.stanza:
                self.stanza[TYPE] = ["Header"]
            self.stanzaProcessor(self.stanza)
            self.stanza = {}

    def __parseLine__(self, line):
        if line.startswith("["):
            j = line.find("]",1)
            return (TYPE, line[1:j])
        else:
            j = line.find(":")
            return (line[0:j], line[j+1:].strip())

    def __addToStanza__(self, line):
        k,v = self.__parseLine__(line)
        self.stanza.setdefault(k, []).append(v)
        
    def __go__(self):
        self.stanza = {}
        self.count = 0
        for line in self.fd:
            if len(line) == 1:	# jak: according to OBO standard, stanzas
                                #   end at next stanza, not a blank line.
                                # BUT this has been working, so leaving for now
                self.__finishStanza__()
            else:
                # remove comments (unescaped ! to EOL)
                #	must be an easier way to do this in python!
                e = line.find("!")
                while e > 0 and line[e-1] == "\\":  # have "!" & it's escaped
                    e = line.find("!", e+1)	# keep looking

                if e != -1:			# yup, got a comment
                    line = line[:e]		# remove it

                self.__addToStanza__(line)

        self.__finishStanza__()

#-----------------------------------
#
# An OboLoader parses an OBO file and returns the corresponding DAG.
#
class OboLoader(object):

    def __init__(self):
        self.parser = OboParser(self.processStanza)
        self.ontology = None
        self.cullObsolete = False
        self.loadMinimal = False
        self.defaultNamespace = "ontology." + str(id(self))
        self.nodeType = None
        self.cullCrossEdges = True

    def loadFile(self, file, cullObsolete=False, loadMinimal=False, config=None, nodeType=OboTerm, cullCrossEdges=True, termCallBack=None):
    # Return a new Ontology object representing the OBO file
    # file - either a filename (string) or an file descriptor open for reading.
    # cullObsolete - if true obsolete terms are skipped & not represented
    # loadMinimal - if true, only represent: IDs, term names, namespace, 
    #		 edges are handled. Other stanza entries are ignored
    #		 and termCallBack is not called.
    # nodeType - is the class of objects to create for each term in the file.
    #		 This needs to be a subclass of OboTerm.
    # cullCrossEdges - if true, any edges between terms in different namespaces
    #		 are omitted.
    # termCallBack is optional function to finalize a term from a term stanza
    #     in the OBO file. The function is passed the term object (nodeType)
    #     and a dict representing the stanza (see OboParser for dict details)
    #     after the stanza has been processed here.

        self.cullObsolete = cullObsolete
        self.loadMinimal = loadMinimal
        self.nodeType = nodeType
        self.ontology = OboOntology(nodeType=self.nodeType)
        self.ontology.config = config
        self.cullCrossEdges = cullCrossEdges
        self.termCallBack = termCallBack

        self.parser.parseFile(file)

        if self.cullCrossEdges: 
            # Prune out any edges that cross namespaces.
            # (GO is going to start including edges between process 
            # and function at some point).
            def efilt(p,c,d):
                return p.namespace != c.namespace
            vocloadDAG.SimplePruner(edgeFilt=efilt).go(self.ontology)

        return self.ontology

    def processStanza(self, stanza):
        stype = stanza["__type__"][0]
        if stype == "Term":
            self.processTerm(stanza)
        elif stype == "Header":
            self.processHeader(stanza)

    def processHeader(self,stanza):
        for (n,v) in stanza.items():
            if n != '__type__':		# skip stanza type inserted by parser
                self.ontology.setAttribute(n,v)

        self.defaultNamespace = stanza.get(
                              'default-namespace', [self.defaultNamespace] )[0]

    def processTerm(self, stanza):
        is_obsolete = (stanza.get('is_obsolete',False)==['true'])
        if is_obsolete and self.cullObsolete:
            return
        id = stanza['id'][0]		# assume stanza has an ID
        name = stanza['name'][0]	# assume stanza has a name
        namespace = stanza.get('namespace',[self.defaultNamespace])[0]

        t = self.ontology.addTerm(id,  name=name)
        self.ontology.setTermAttribute(t, 'is_obsolete', is_obsolete)
        self.ontology.setTermAttribute(t, 'namespace', namespace)

        for isa in stanza.get("is_a", []):
            id2 = isa.strip()
            self.ontology.addTerm(id2)		# don't know the term's name
            self.ontology.addRelationship(id, "is_a", id2)

        for reln in stanza.get("relationship", []):
            tokens = reln.split()		# should be edge-type parentID
            if len(tokens) != 2:
                raise Exception("Unexpected relationship specification: " + str(tokens))
            (rel,id2) = list(map(str.strip, tokens))
            self.ontology.addTerm(id2)		# don't know term's name
            self.ontology.addRelationship(id, rel, id2)

        if self.loadMinimal:
            return

        for attr, val in stanza.items():	# set any other attrs for term
                                                #   from this stanza
            if attr not in ['id','name','namespace','relationship','is_a']:
                self.ontology.setTermAttribute(t, attr, val)

        # call back for any custom stanza processing (if any)
        self.termCallBack and self.termCallBack(t, stanza)

#------------------------------------
#
# Example subclass of OboTerm
#   (if you want your terms to have more functionality)
#class MyTerm(OboTerm):
#
#    def __init__(self, id, name, ontol):
#	super(MyTerm, self).__init__(id, name, ontol)
#	self.foo="blah"
# end class MyTerm -------------------

__loader__ = OboLoader( )
load = __loader__.loadFile

#------------------------------------

if __name__ == "__main__":
    o = load(sys.argv[1], True)
    # o = load(sys.argv[1], True, nodeType=MyTerm)
