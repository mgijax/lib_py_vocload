
# Name: Log.py
# Purpose: to provide a class for easy logging to stderr and/or a log file

import types	# standard Python libraries
import sys

###--- Exceptions ---###

error = 'Log.error'					# exception raised
closed_log = 'attempted to write to a closed Log'	# value for exception

###--- Classes ---###

class Log:
	# IS: a log in which to record information while a script runs
	# HAS: a file to which to write
	# DOES: writes strings to a log file and/or stderr
	# Notes: Be sure to use the close() method when done writing to the
	#	Log, to be sure any remaining buffers are flushed.

	def __init__ (self,
		toStderr = 1,	# boolean (0/1); write to stderr or not?
		filename = None	# string; path to log file to write
		):
		# Purpose: constructor
		# Returns: nothing
		# Assumes: 'filename' is writeable
		# Effects: instantiates a Log object
		# Throws: IOError if the 'filename' is not writeable

		# path to the log file
		self.filename = filename

		# boolean (0/1) indicating whether to write to stderr
		self.toStderr = toStderr

		# boolean (0/1) indicating whether this Log is open for
		# writing
		self.isClosed = not (filename or toStderr)

		# file pointer, opened for writing, corresponding to the
		# log file (if one was specified)
		self.logfile = None
		if self.filename:
			self.logfile = open (self.filename, 'w')
		return

	def write (self,
		items		# string or list of strings to write to Log
		):
		# Purpose: write the given 'items' to the log
		# Returns: nothing
		# Assumes: nothing
		# Effects: writes to stderr and/or the log file, or bails out
		#	if neither is open
		# Throws: nothing
		# Notes: 'items' may actually contain a string, a list of
		#	strings, any object with a str() function defined,
		#	or a list of such objects

		if self.isClosed:		# don't write to a closed Log
			return

		# if 'items' is a list, then recursively invoke this method
		# to handle each item in the list

		if type(items) == types.ListType:
			for item in items:
				self.write (item)
			return

		# if we got this far, then we know that 'items' is a single
		# item rather than a list.  And, we know that the Log is open,
		# so we write to stderr and/or the log file, as appropriate.

		if self.toStderr:
			sys.stderr.write (str(items))
		if self.logfile:
			self.logfile.write (str(items))
		return

	def writeline (self,
		items		# string or list of strings to write to Log
		):
		# Purpose: write the given 'items' to the log, and add a new-
		#	line after each
		# Returns: nothing
		# Assumes: nothing
		# Effects: writes to stderr and/or the log file, or bails out
		#	if neither is open
		# Throws: nothing
		# Notes: 'items' may actually contain a string, a list of
		#	strings, any object with a str() function defined,
		#	or a list of such objects.  We use the write() method
		#	to do the actual writing.

		# if 'items' is a list, then we need to add a newline to the
		# string representation of each item in the list.  then write
		# them.

		if type(items) == types.ListType:
			self.write (map (lambda x : str(x) + '\n', items))
			return

		# otherwise, we have a single item, so add a newline to it
		# before we write it

		self.write (str(items) + '\n')
		return

	def close (self):
		# Purpose: close this Log, flushing any buffers and prevent-
		#	ing any additional writing to it
		# Returns: nothing
		# Assumes: nothing
		# Effects: closes the Log (and the log file, if one was open)
		# Throws: nothing

		if self.logfile:			# if log file open,
			self.logfile.close()		# close it
			self.logfile = None
		self.isClosed = 1
		return
