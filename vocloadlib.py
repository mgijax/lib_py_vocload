#!/usr/local/bin/python

# Name: vocloadlib.py
#
# Purpose: provides standard functions for use throughout the vocabulary load
#   product (including the DAG load as well)
#
# On Import: Following the importation of this module, you should make sure
#   to call the setupSql() function to ensure you're looking at the right
#   database.
#
# Modification History
#
# 04/03/2003	lec
#	- TR 4564; added support for comments
#

import sys      # standard Python modules
import time
import types
import re
import string
import os

import db       # MGI-written Python modules
import dbTable  # dbTable library

###--- Exceptions ---###

error = 'vocloadlib.error'  # exception raised in this module, values:

unknown_dag = 'unknown DAG name "%s"'
unknown_dag_key = 'unknown DAG key "%s"'
unknown_vocab = 'unknown vocabulary name "%s"'
unknown_vocab_key = 'unknown vocabulary key "%s"'
unknown_synonymtype = 'unknown synonym type "%s"'

bad_line = '%s:Incorrect Line Format for Line Number %d\n%s'

###--- Globals ---###

VOCABULARY_TERM_TYPE = 13   # default _MGIType_key for vocab terms
NOT_SPECIFIED = -1          # traditional 'n.s.' for vocabs
NO_LOAD = 0         # boolean (0/1); are we in a no-load state?
                #   (log SQL, but don't run it)
TERM_IDS = None         # dictionary mapping term ID to term key,
                #   set by TermLoad when running in
                #   no-load mode

###--- Functions ---###

def setupSql (server,   # string; name of database server
    database,   # string; name of database
    username,   # string; user with full permissions on database
    password    # string; password for 'username'
    ):
    # Purpose: initialize the 'db' module to use the desired database
    #   login information
    # Returns: nothing
    # Assumes: the parameters are all valid
    # Effects: initializes the 'db' module with the given login info, and
    #   tells it to use one connection (rather than a separate
    #   connection for each sql() call)
    # Throws: nothing

    db.set_sqlLogin (username, password, server, database)
    db.useOneConnection(1)
    return

def unsetupSql ():
    # Purpose: un-initialize the 'db' module
    # Returns: nothing
    # Assumes: nothing
    # Effects: resets the db.useOneConnection() value
    # Throws: nothing

    db.useOneConnection(0)
    return

def sql (
    commands    # string of SQL, or list of SQL strings
    ):
    # Purpose: wrapper over the db.sql() function, so we don't need to
    #   specify 'auto' with each call.
    # Returns: as db.sql(), returns:
    #   list of dictionaries of 'commands' is a string
    #   list of lists of dictionaries if 'commands' is a list
    # Assumes: setupSql() has been invoked appropriately
    # Effects: queries the database
    # Throws: propagates any exceptions raised by db.sql()

    return db.sql (commands, 'auto')

def sqlog (
    commands,   # string of SQL, or list of SQL strings
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: write the given 'commands' to the given 'log', then execute
    #   those SQL 'commands'
    # Returns: see sql()
    # Assumes: see sql()
    # Effects: writes to 'log', sends 'commands' to database
    # Throws: propagates any exceptions raised by db.sql()

    log.writeline (commands)
    return sql (commands)

def setNoload (
    on = 1      # boolean (0/1); turn no-load on (1) or off (0)?
    ):
    # Purpose: set/unset the global NO_LOAD flag to indicate whether we
    #   are running in a no-load state
    # Returns: nothing
    # Assumes: nothing
    # Effects: alters the global NO_LOAD
    # Throws: nothing

    global NO_LOAD

    NO_LOAD = on
    return

def nl_sqlog (
    commands,   # string of SQL, or list of SQL strings
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: write the given 'commands' to the given 'log'.  If we are
    #   not in a no-load state, then execute those SQL 'commands'.
    # Returns: see sql()
    # Assumes: see sql()
    # Effects: writes to 'log', may send 'commands' to database
    # Throws: propagates any exceptions raised by db.sql()
    # Notes: This is the no-load version of sqlog(), hence the "nl_"
    #   prefix.  It will check the no-load flag before executing
    #   the SQL.

    log.writeline (commands)
    if not NO_LOAD:
        return sql (commands)
    return []


def beginTransaction (
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: open a Sybase transaction
    # Returns: nothing
    # Assumes: an open db connection
    # Effects: writes to 'log', may send begin transaction to database
    # Throws: propagates any exceptions raised by db.sql()
    # Notes: This is the no-load version. It will check the 
    # no-load flag before opening the transaction.
    
    beginTransactionString = "begin transaction"

    log.writeline ( "Beginning Transaction..." )
    log.writeline ( beginTransactionString )
    if not NO_LOAD:
        sql (beginTransactionString)
    return


def commitTransaction (
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: commit a Sybase transaction
    # Returns: nothing
    # Assumes: an open db connection
    # Effects: writes to 'log', may send commit to database
    # Throws: propagates any exceptions raised by db.sql()
    # Notes: This is the no-load version. It will check the 
    # no-load flag before committing the transaction.

    commitTransactionString = "commit transaction"

    log.writeline ( "Committing Transaction..." )
    log.writeline ( commitTransactionString )
    if not NO_LOAD:
        sql (commitTransactionString)
    return


def rollbackTransaction (
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: rollback a Sybase transaction
    # Returns: nothing
    # Assumes: an open db connection
    # Effects: writes to 'log', may send rollback to database
    # Throws: propagates any exceptions raised by db.sql()
    # Notes: This is the no-load version. It will check the 
    # no-load flag before rolling back the transaction.

    rollbackTransactionString = "rollback transaction"

    log.writeline ( "Rolling Back Transaction..." )
    log.writeline ( rollbackTransactionString )
    if not NO_LOAD:
        sql (rollbackTransactionString)
    return


def updateStatistics ( tableName,
    log     # Log.Log object to which to log the 'commands'
    ):
    # Purpose: update statistics for table passed in
    # Returns: nothing
    # Assumes: an open db connection
    # Effects: writes to 'log', and updates statistics on database
    # Throws: propagates any exceptions raised by db.sql()
    # Notes: This is the no-load version. It will check the 
    # no-load flag before updating statistics.

    updateStatisticsString = "update statistics %s" % tableName

    log.writeline ( "Updating Statistics for %s..." % tableName )
    log.writeline ( updateStatisticsString )
    if not NO_LOAD:
        sql (updateStatisticsString)
    return


def setVocabMGITypeKey (
    key     # integer; _MGIType_key for vocabulary terms
    ):
    # Purpose: set the global VOCABULARY_TERM_TYPE value to be a new
    #   value.  should correspond to the correct _MGIType_key in
    #   ACC_MGIType
    # Returns: nothing
    # Assumes: nothing
    # Effects: alters VOCABULARY_TERM_TYPE
    # Throws: nothing

    global VOCABULARY_TERM_TYPE

    VOCABULARY_TERM_TYPE = key
    return

def anyTermsCrossReferenced (
    vocab_key       # integer; corresponds to VOC_Vocab._Vocab_key
    ):
    # Purpose: determine if any terms in the vocabulary identified by
    #   'vocab_key' are cross-referenced from the VOC_Evidence and/or
    #   VOC_Annot tables
    # Returns: boolean (0/1) indicating whether any such cross-refs exist
    # Assumes: see sql()
    # Effects: queries the database
    # Throws: propagates any exceptions raised by sql()

    results = sql ( [
            '''select ct = count(1)
            from VOC_Term vt, VOC_Evidence ve
            where vt._Vocab_key = %d
                and vt._Term_key = ve._EvidenceTerm_key
            ''' % vocab_key,

            '''select ct = count(1)
            from VOC_Term vt, VOC_Annot va
            where vt._Vocab_key = %d
                and vt._Term_key = va._Term_key
            ''' % vocab_key,
            ])
    return results[0][0]['ct'] + results[1][0]['ct'] > 0

def getAnyTermMarkerCrossReferences (
    termKey,       # integer; corresponds to VOC_Term._Term_key
    annotationKey  # integer; corresponds to the VOC_AnnotType._AnnotType_key
    ):
    # Purpose: get any annotations to a term/annotationType
    # Returns: list of annotations
    # Assumes: see sql()
    # Effects: queries the database
    # Throws:  propagates any exceptions raised by sql()
    # Notes:   please be aware that this function only
    #          gets term to marker annotations

    try:
       results = sql ( 
            ''' select m.symbol
                      ,t.term
                      ,t._term_key
                from   VOC_Term t
                      ,VOC_Annot a
                      ,MRK_Marker m
                where  t._Term_key      = %d
                and    t._Term_key      = a._Term_key
                and    a._AnnotType_key = %s
                and    a._Object_key    = m._Marker_key
            ''' % ( termKey, annotationKey ))
    except:
       raise 'xref error', sys.exc_value
    return results

def timestamp (
    label = 'Current time:'     # string; preface to the timestamp
    ):
    # Purpose: return a timestamp including the given 'label' followed by
    #   the current date and time in the format mm/dd/yyyy hh:mm:ss
    # Returns: string
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing

    return '%s %s' % \
        (label,
        time.strftime ("%m/%d/%Y %H:%M:%S",
            time.localtime (time.time())))

def getDagName (
    dag     # integer; corresponds to DAG_DAG._DAG_key
    ):
    # Purpose: return the name of the DAG identified by 'dag'
    # Returns: string
    # Assumes: nothing
    # Effects: queries the database
    # Throws: 1. error if the given 'dag' is not in the database;
    #   2. propagates any exceptions raised by sql()

    result = sql ('select name from DAG_DAG where _DAG_key = %d' % dag)
    if len(result) != 1:
        raise error, unknown_dag_key % dag
    return result[0]['name']

def getDagKey (
    dag,        # string; corresponds to DAG_DAG.name
    vocab = None    # string vocab name or integer vocab key
    ):
    # Purpose: return the _DAG_key for the given 'dag' name
    # Returns: integer
    # Assumes: nothing
    # Effects: queries the database
    # Throws: 1. error if the given 'dag' is not in the database;
    #   2. propagates any exceptions raised by sql()
    # Notes: Since the DAG_DAG.name field is does not require unique
    #   values, we may also need to know which 'vocab' it relates to.

    if vocab:
        if type(vocab) == types.StringType:
            vocab = getVocabKey (vocab)
        result = sql ('''select dd._DAG_key
                from DAG_DAG dd, VOC_VocabDAG vvd
                where dd._DAG_key = vvd._DAG_key
                    and vvd._Vocab_key = %d
                    and dd.name = "%s"''' % (vocab, dag))
    else:
        result = sql ('''select _DAG_key
                from DAG_DAG
                where name = "%s"''' % dag)
    if len(result) != 1:
        raise error, unknown_dag % dag
    return result[0]['_DAG_key']

def getVocabName (
    vocab       # integer; key corresponding to VOC_Vocab._Vocab_key
    ):
    # Purpose: return the vocabulary name for the given 'vocab' key
    # Returns: string
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions raised by getVocabAttributes()

    return getVocabAttributes (vocab)[3]

def getVocabKey (
    vocab       # string; vocab name from VOC_Vocab.name
    ):
    # Purpose: return the vocabulary key for the given 'vocab' name
    # Returns: integer
    # Assumes: nothing
    # Effects: queries the database
    # Throws: 1. error if the given 'vocab' is not in the database
    #   2. propagates any exceptions raised by sql()

    result = sql ('select _Vocab_key from VOC_Vocab where name = "%s"' % \
        vocab)
    if len(result) != 1:
        raise error, unknown_vocab % vocab
    return result[0]['_Vocab_key']

def getSynonymTypeKey (
    synonymType       # string; synonym type from MGI_SynonymType.synonymType
    ):
    # Purpose: return the synonym type key for the given 'vocab' synonym type
    # Returns: integer
    # Assumes: nothing
    # Effects: queries the database
    # Throws: 1. error if the given synonym type is not in the database
    #   2. propagates any exceptions raised by sql()

    result = sql ('select _SynonymType_key from MGI_SynonymType where synonymType = "%s" and _MGIType_key = %d' % (synonymType, VOCABULARY_TERM_TYPE))
    if len(result) != 1:
        raise error, unknown_synonymtype % synonymType
    return result[0]['_SynonymType_key']

def checkVocabKey (
    vocab_key   # integer; key for vocabulary, as VOC_Vocab._Vocab_key
    ):
    # Purpose: check that 'vocab_key' exists in the database
    # Returns: nothing
    # Assumes: nothing
    # Effects: queries the database
    # Throws: 1. raises TypeError if 'vocab_key' is not an integer
    #   2. propogates 'error' if 'vocab_key' is not in VOC_Vocab
    #   3. also propagates any other exceptions raised by
    #       getVocabAttributes()

    if type(vocab_key) != types.IntegerType:
        raise TypeError, 'Integer vocab key expected'

    # We use this function to retrieve basic info about the vocab, but we
    # don't need to do anything with it.  (We're just seeing that it
    # exists, and letting the exceptions propagate if it doesn't.)

    getVocabAttributes (vocab_key)
    return

def isSimple (
    vocab   # integer vocabulary key or string vocabulary name
    ):
    # Purpose: determine if 'vocab' is a simple vocabulary or a DAG
    # Returns: boolean (0/1); returns 1 if 'vocab' is a simple vocabulary
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from getVocabAttributes()

    return getVocabAttributes (vocab)[0]

def isPrivate (
    vocab   # integer vocabulary key or string vocabulary name
    ):
    # Purpose: determine if 'vocab' is private
    # Returns: boolean (0/1); returns 1 if 'vocab' is private
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from getVocabAttributes()

    return getVocabAttributes (vocab)[1]

def countTerms (
    vocab   # integer vocabulary key or string vocabulary name
    ):
    # Purpose: count the number of terms in the given 'vocab'
    # Returns: integer; count of the terms
    # Assumes: 'vocab' exists in the database
    # Effects: queries the database
    # Throws: propagates any exceptions from sql()

    if type(vocab) == types.StringType:
        vocab = getVocabKey (vocab)
    result = sql ('''select ct = count(1)
            from VOC_Term
            where _Vocab_key = %d''' % vocab)
    return result[0]['ct']

def countNodes (
    dag,        # integer DAG key or string DAG name
    vocab = None    # integer vocab key or string vocab name; required if
            # 'dag' is the name of the DAG
    ):
    # Purpose: count the number of nodes in the given 'dag'
    # Returns: integer; count of the nodes
    # Assumes: 'dag' exists in the database
    # Effects: queries the database
    # Throws: propagates any exceptions from sql()
    # Notes: Because DAG names are not required to be unique, we also need
    #   the associated vocab to uniquely identify a DAG when given
    #   a DAG name.

    if type(dag) == types.StringType:
        dag = getDagKey (dag, vocab)
    result = sql ('''select ct = count(1)
            from DAG_Node
            where _DAG_key = %d''' % dag)
    return result[0]['ct']

def getTerms (
    vocab   # integer vocabulary key or string vocabulary name
    ):
    # Purpose: retrieve the terms for the given 'vocab' and their
    #   respective attributes
    # Returns: dbTable.RecordSet object
    # Assumes: 'vocab' exists in the database
    # Effects: queries the database
    # Throws: propagates exceptions from sql()
    # Notes: The RecordSet object returned contains dictionaries, each
    #   of which represents a term and its attributes.  The
    #   dictionaries may be accessed using the desired term's key.

    if type(vocab) == types.StringType:
        vocab = getVocabKey (vocab)

    [ voc_term, voc_text, voc_synonym, voc_comment ] = sql( [
        '''select *             -- basic term info
        from VOC_Term
        where _Vocab_key = %d''' % vocab,

        '''select vx.*              -- text for term
        from VOC_Text vx, VOC_Term vt
        where vt._Vocab_key = %d
            and vt._Term_key = vx._Term_key
        order by vx._Term_key, vx.sequenceNum''' % vocab,

        '''select vs.*, vst.synonymType   -- synonyms/synonymTypes for term
        from MGI_Synonym vs, MGI_SynonymType vst, VOC_Term vt
        where vt._Vocab_key = %d
            and vt._Term_key = vs._Object_key
            and vs._MGIType_key = %d
            and vs._SynonymType_key = vst._SynonymType_key
        order by vs.synonym''' % (vocab, VOCABULARY_TERM_TYPE),

	'''select n._Object_key, nc.note, nc.sequenceNum
	from VOC_Term vt, MGI_Note n, MGI_NoteChunk nc
	where vt._Vocab_key = %d
	and vt._Term_key = n._Object_key
	and n._NoteType_key = %s
	and n._Note_key = nc._Note_key
	order by n._Object_key, nc.sequenceNum''' % (vocab, os.environ['VOCAB_COMMENT_KEY'])
        ] )
    
    # build a dictionary of 'notes', mapping a term key to a string of
    # notes.  We take care to join multiple 255-character chunks into
    # one string.

    notes = {}
    for row in voc_text:
        term_key = row['_Term_key']
        if notes.has_key (term_key):
            notes[term_key] = notes[term_key] + row['note']
        else:
            notes[term_key] = row['note']

    # build a dictionary of 'comments', mapping a term key to a string of
    # notes.  We take care to join multiple 255-character chunks into
    # one string.

    comments = {}
    for row in voc_comment:
        term_key = row['_Object_key']
        if comments.has_key (term_key):
            comments[term_key] = comments[term_key] + row['note']
        else:
            comments[term_key] = row['note']

    # build a dictionary of 'synonyms', mapping a term key to a list of
    # strings (each of which is one synonym)

    synonyms = {}
    synonymTypes = {}
    for row in voc_synonym:
        term_key = row['_Object_key']
        if not synonyms.has_key (term_key):
            synonyms[term_key] = []
            synonymTypes[term_key] = []
        synonyms[term_key].append (row['synonym'])
        synonymTypes[term_key].append (string.upper(row['synonymType']))
        # synonyms[term_key].append ([row['_Synonym_key'], row['synonym']])

    # Each dictionary in 'voc_term' represents one term and contains all
    # its basic attributes.  We step through the list to add any 'notes'
    # 'comments' and 'synonyms' for each.

    for row in voc_term:
        term_key = row['_Term_key']

        if notes.has_key (term_key):
            row['notes'] = notes[term_key]
        else:
            row['notes'] = None

        if comments.has_key (term_key):
            row['comments'] = comments[term_key]
        else:
            row['comments'] = None

        if synonyms.has_key (term_key):
            row['synonyms'] = synonyms[term_key]
            row['synonymTypes'] = synonymTypes[term_key]
        else:
            row['synonyms'] = []
            row['synonymTypes'] = []

    # convert the list of dictionaries 'voc_term' into a RecordSet object
    # keyed by the _Term_key, and return it

    return dbTable.RecordSet (voc_term, '_Term_key')

def getLabels ():
    # Purpose: find the complete set of DAG labels from the database
    # Returns: dictionary mapping labels to their keys
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from sql()

    result = sql ('select label, _Label_key from DAG_Label')
    labels = {}
    for row in result:
        labels[row['label']] = row['_Label_key']
    return labels

def setTermIDs (
    dict        # dictionary mapping term IDs to term keys
    ):
    # Purpose: To have the TermLoad and DAGLoad cooperate for the no-load
    #   option, we need to be able to pass the ID to key mapping to
    #   the DAG Load rather than getting it from the db.
    # Returns: nothing
    # Assumes: nothing
    # Effects: sets global TERM_IDS
    # Throws: nothing

    global TERM_IDS

    TERM_IDS = dict
    return

def getTermIDs (
    vocab       # integer vocabulary key or string vocabulary name
    ):
    # Purpose: get a dictionary which maps from a primary accession ID
    #   to its associated term key and isObsolete value
    # Returns: see Purpose
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from sql()

    if TERM_IDS:            # if global is set, use it
        return TERM_IDS

    if type(vocab) == types.StringType:
        vocab = getVocabKey (vocab)
    result = sql ('''select acc.accID, vt._Term_key, vt.isObsolete, vt.term
            from VOC_Term vt, ACC_Accession acc
            where vt._Vocab_key = %d
                and acc._MGIType_key = %d
                and vt._Term_key = acc._Object_key
                and acc.preferred = 1''' % \
            (vocab, VOCABULARY_TERM_TYPE))
    ids = {}
    for row in result:
        #NOTE: The '0' added to the end of the list is a flag used to 
        #track whether or not a term in the database has a corresponding
        #term in the input file
        ids[row['accID']] = [row['_Term_key'], row['isObsolete'], row['term'], 0]
    return ids

def getSecondaryTermIDs (
    vocab       # integer vocabulary key or string vocabulary name
    ):
    # Purpose: get a dictionary which maps from a secondary accession ID
    #   to its associated term key
    # Returns: see Purpose
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from sql()

    if type(vocab) == types.StringType:
        vocab = getVocabKey (vocab)

    result = sql ('''select acc.accID, vt._Term_key, vt.term
            from VOC_Term vt, ACC_Accession acc
            where vt._Vocab_key = %d
                and acc._MGIType_key = %d
                and vt._Term_key = acc._Object_key
                and acc.preferred = 0''' % \
            (vocab, VOCABULARY_TERM_TYPE))
    ids = {}
    for row in result:
        #NOTE: The '0' added to the end of the list is a flag used to 
        #track whether or not a term in the database has a corresponding
        #term in the input file
        ids[row['accID']] = [row['_Term_key'], row['term'], 0]
    return ids

def readTabFile (
    filename,   # string; path to a tab-delimited file to read
    fieldnames  # list of strings; each is the name of one field
    ):
    # Purpose: read a tab-delimited file and convert each line to a
    #   dictionary mapping from fieldnames to values
    # Returns: list of dictionaries
    # Assumes: 'filename' is readable
    # Effects: reads 'filename'
    # Throws: 1. IOError if we cannot read from 'filename';
    #   2. error if a line has the wrong number of fields
    # Example: Consider the following tab-delimited file 'foo.txt':
    #       3   Joe Smith
    #       5   Jane    Jones
    #   Then, readTabFile ('foo.txt', ['key', 'first', 'last' ])
    #   returns:
    #       [ { 'key' : 3, 'first' : 'Joe', 'last' : 'Smith' },
    #         { 'key' : 5, 'first' : 'Jane', 'last' : 'Jones' } ]

    num_fields = len(fieldnames)
    lines = []
    fp = open (filename, 'r')
    line = fp.readline()
    lineNbr = 0
    while line:
        lineNbr = lineNbr + 1
        # note that we use line[:-1] to trim the trailing newline
        fields = re.split ('\t', line[:-1])

        if len(fields) != num_fields:
            raise error, bad_line % (filename, lineNbr, line)

        # map each tab-delimited field to its corresponding fieldname
        i = 0
        dict = {}
        while i < num_fields:
            dict[fieldnames[i]] = fields[i]
            i = i + 1

        lines.append(dict)  # add to the list of dictionaries
        line = fp.readline()
    fp.close()
    return lines

def splitBySize (
    s,      # string; the string to be split
    size = 255  # integer; max number of characters per output string
    ):
    # Purpose: break 's' into a list of strings containing at most 'size'
    #   characters
    # Returns: list of strings
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing
    # Notes: string.join (splitBySize (s, n), '') == s, for all n

    len_s = len(s)
    parts = []
    i = 0
    while i < len_s:
        parts.append (s[i:i+size])
        i = i + size
    return parts

def getMax (
    fieldname,  # string; name of a field in 'table' in the database
    table       # string; name of a table in the database
    ):
    # Purpose: return the maximum value of 'fieldname' in 'table'
    # Returns: depends on the datatype of 'fieldname' in 'table'; will be
    #   None if 'table' contains no records
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates all exceptions from sql()

    result = sql ('select mx=max(%s) from %s' % (fieldname, table))

    if result[0]['mx'] == None:
	return 0
    else:
	return result[0]['mx']

def getLogicalDBkey (
    vocab       # integer vocabulary key or string vocabulary name
    ):
    # Purpose: retrieve the logical database key (_LogicalDB_key) for
    #   the given 'vocab'
    # Returns: integer
    # Assumes: nothing
    # Effects: queries the database
    # Throws: propagates any exceptions from getVocabAttributes()

    return getVocabAttributes (vocab)[2]

def escapeDoubleQuotes (
    s       # string in which to duplicate any double-quotes
    ):
    # Purpose: duplicate any double-quotes (") which appear in s
    # Returns: string
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing
    # Notes: This function is used to prepare strings to be sent as part
    #   of a SQL command to Sybase.  We delimit string fields for
    #   sybase using double-quotes, so if the string contains any
    #   double-quotes, we need to duplicate them.

    return re.sub ('"', '""', s)

def setNull (
    s      
    ):
    # Purpose: set any strings set to "null" to ""
    # Returns: string
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing
    # Notes: This function is used to prepare strings to be sent as part
    #   of a BCP command to Sybase.  
    if s == 'null':
       s = ""
    return s

def deleteVocabTerms (
    vocab_key,  # integer; vocabulary key from VOC_Vocab._Vocab_key
    log = None  # Log.Log object; where to log the deletions
    ):
    # Purpose: delete all terms for the given vocabulary key, and any
    #   associated attributes (like text blocks and synonyms)
    # Returns: nothing
    # Assumes: setupSql() has been called appropriately, and VOC_Term_Delete
    #          trigger exists
    # Effects: removes records from all tables defined by the
    #          VOC_Term_Delete trigger
    # Throws:  propagates any exceptions from sqlog() or sql()
    # Notes:   VOC_Term has a trigger VOC_Term_Delete which propogates
    #          deletions to all underlying term-related tables
    #          Also, we need to check that we are not in
    #          a no-load state before calling the sql() function.

    sql = 'delete from VOC_Term where _Vocab_key = %d' % vocab_key
    nl_sqlog ( sql, log)
    return

def deleteDagComponents (
    dag_key,    # integer; DAG key from DAG_DAG._DAG_key
    log = None  # Log.Log object; where to log the deletions
    ):
    # Purpose: delete all components of the DAG with the given key,
    #   including its nodes, terms, and closure.  (but not its actual
    #   DAG_DAG entry)
    # Returns: nothing
    # Assumes: setupSql() has been called appropriately
    # Effects: removes records from all tables defined by the
    #          DAG_Node_Delete trigger
    # Throws:  propagates any exceptions from sqlog() or sql()
    # Notes:   DAG_Node has a trigger DAG_Node_Delete which propogates
    #          deletions to all underlying dag-related tables,
    #          namely DAG_edge and DAG_Closure, in addition to DAG_Node
    #          Also, we need to check that we are not in
    #          a no-load state before calling the sql() function.

    sql = 'delete from DAG_Node where _DAG_key = %d' % dag_key
    nl_sqlog ( sql, log)
    return

def isNoLoad ():
    # Purpose: returns boolean (0/1) telling if we are running as no-load
    #   (1) or not (0)
    # Returns: 0/1
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing

    return NO_LOAD

def loadBCPFile ( bcpFileName, bcpLogFileName, bcpErrorFileName, tableName, passwordFile ):
    # Purpose: Physically loads BCP files to the database via a system command to bcp
    # Returns: nothing
    # Assumes: bcp is available and exists in PATH
    # Effects: loads data to whatever table it is executing on
    # Raises:  raises an exception if bcp returns a non-zero (i.e.,
    #          value

    bcpCmd = 'cat %s | bcp %s..%s in %s -c -t"|" -e %s -S%s -U%s >> %s' \
      % (passwordFile, db.get_sqlDatabase(), \
      tableName, bcpFileName, bcpErrorFileName, \
      db.get_sqlServer(), db.get_sqlUser(), bcpLogFileName  )

    rc = os.system( bcpCmd )
    if rc:
       raise 'bcp error', sys.exc_value
    return


def truncateTransactionLog (
    database,       # string; name of the database
    log = None      # Log.Log object; where to log the command
    ):
    # Purpose: truncate the transaction log for the given database
    # Returns: nothing
    # Assumes: nothing
    # Effects: see Purpose, does not save the log's contents to a file
    # Throws: propagates any exceptions from sql()
    # Notes: We do not dump the transaction log if running in no-load
    #   mode.

    cmd = 'dump transaction %s with truncate_only' % database
    if log:
        nl_sqlog (cmd, log)
    elif not NOLOAD:
        sql (cmd)
    return

###--- Private Functions ---###

vocab_info_cache = {}   # used as a cache for 'getVocabAttributes()' function

def getVocabAttributes (
    vocab       # integer vocabulary key or string vocabulary name
    ):
    # PRIVATE FUNCTION
    #
    # Purpose: retrieve some basic info for the given 'vocab'
    # Returns: tuple containing: (boolean isSimple, boolean isPrivate,
    #   integer _LogicalDB_key, string name, integer vocab key)
    # Assumes: 'vocab' exists in the database
    # Effects: queries the database
    # Throws: 1. propagates any exceptions from sql();
    #   2. raises 'error' if 'vocab' is not in the database

    global vocab_info_cache

    if type(vocab) == types.StringType: # ensure we work w/ the key
        vocab = getVocabKey (vocab)

    # get it from the database if it's not in the cache already

    if not vocab_info_cache.has_key (vocab):
        result = sql('''select isSimple, isPrivate, _LogicalDB_key,
                    _Vocab_key, name
                from VOC_Vocab
                where _Vocab_key = %d''' % vocab)
        if len(result) != 1:
            raise error, unknown_vocab_key % vocab
        r = result[0]

        # store resulting info in the cache

        vocab_info_cache[vocab] = (r['isSimple'], r['isPrivate'],
            r['_LogicalDB_key'], r['name'], r['_Vocab_key'])

    return vocab_info_cache[vocab]
