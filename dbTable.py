error = 'RecordSet.error'
bad_key = 'duplicate records for specified primary key, %s = %s'
no_key = 'no primary key defined for this RecordSet'
bad_diff = 'too many matches for RecordSet.diff where %s = %s'

class Record:
	def __init__ (self,
		dict
		):
		self.fields = dict
		self.pairs = None
		return
	def __getitem__ (self,
		key
		):
		return self.fields[key]
	def has_key (self,
		key
		):
		return self.fields.has_key(key)
	def keys (self):
		return self.fields.keys()
	def items (self):
		if self.pairs == None:
			self.pairs = self.fields.items()
			self.pairs.sort()
		return self.pairs
	def equals (self,
		record
		):
		return self.items() == record.items()
	def diff (self,
		record,
		keys
		):
		different = []
		for key in keys:
			if self[key] != record[key]:
				different.append (key)
		return different

class RecordSet:
	def __init__ (self,
		rows,			# list of dictionaries, each is a row
		primary_key = None	# string; name of pk field (if any)
		):
		self.primary_key = primary_key
		self.indexes = {}
		self.primary_keys = {}
		self.records = []

		for row in rows:
			if primary_key != None:
				key = row[primary_key]
				if self.has_key (key):
					raise error, bad_key % (primary_key, \
						key)
				self.primary_keys[key] = len(self.records)
			self.records.append (Record(row))
		return
	def __getitem__ (self,
		key_value
		):
		if self.primary_key == None:
			raise error, no_key
		return self.records[self.primary_keys[key_value]]
	def has_key (self,
		key_value
		):
		if self.primary_key == None:
			raise error, no_key
		return self.primary_keys.has_key(key_value)
	def find (self,
		field,
		value
		):
		if not self.indexes.has_key(field):
			self.makeIndex(field)
		if self.indexes[field].has_key(value):
			return self.indexes[field][value]
		return []
	def len (self):
		return len(self.records)
	def getRecords (self):
		return self.records
	def diff (self,
		set1,
		id_field,
		compare_fields	# list of fieldnames to check for changes
		):
		# returns [ records in set1 but not self ], 
		#	  [ records in self but not set1 ],
		#	  [ records in both self and set1, but changed ]

		set1_not_self = []
		self_not_set1 = []
		changed = []		# each item (self.record, set1.record,
					#	list of changed fieldnames)

		for record in self.records:
			matches = set1.find (id_field, record[id_field])
			if len(matches) > 1:
				raise error, bad_diff % (id_field,
					record[id_field])
			elif len(matches) == 0:
				self_not_set1.append (record)
			else:
				diff_fields = record.diff (matches[0],
					compare_fields)
				if diff_fields:
					changed.append ( (record, matches[0],
						diff_fields) )

		for record in set1.getRecords():
			matches = self.find (id_field, record[id_field])
			if len(matches) == 0:
				set1_not_self.append (record)
			elif len(matches) > 1:
				raise error, bad_diff % (id_field,
					record[id_field])

			# we already compared uniquely matching items in the
			# previous loop, so we don't need to do it again here

		return set1_not_self, self_not_set1, changed

	###--- Private Methods ---###

	def makeIndex (self,
		field
		):
		self.indexes[field] = {}
		for record in self.records:
			value = record[field]
			if not self.indexes[field].has_key(value):
				self.indexes[field][value] = []
			self.indexes[field][value].append (record)
		return
