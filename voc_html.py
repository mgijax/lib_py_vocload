
# This is a simple library to return an html
# str.to the program calling a method.
# This object contains no data; it simply
# encapsulates a few basic html operations

import vocloadlib

EOL = '\n'
TODAYS_DATE = vocloadlib.timestamp("")

# Starts an html table
def getStartTableHTML ():
   return "<Table border cellpadding = 2 cellspacing = 3 width = 90%><TR align=center>" + EOL

# Ends an html table
def getEndTableHTML():
   return "</Table>" + EOL

# Writes a table cell
def getCellHTML ( cellContent ):
   return "<TD>" + cellContent + "</TD>" + EOL

# Writes a table column header
def getTableHeaderLabelHTML( cellContent ):
   return getCellHTML ("<B>" + cellContent + "</B>") + EOL

# Starts a table row
def getStartTableRowHTML():
   return "<TR align=center>" + EOL

# Ends a table row
def getEndTableRowHTML():
   return "</TR>" + EOL

# Starts an HTML document
def getStartHTMLDocumentHTML( documentTitle ):
   return "<HTML>" + EOL + \
          "<HEAD>" + EOL + \
          "<TITLE>" + documentTitle + "</TITLE>" + EOL + \
          "</HEAD>" + EOL + \
          "<BODY bgcolor=#ffffff>" + EOL + \
          "<H1><U><CENTER>" + documentTitle + "</H1></U></CENTER>" + EOL + \
          "<H2><CENTER><I> DATE:" + TODAYS_DATE + "</I></CENTER></H2>"

# Commits an HTML document
def getEndHTMLDocumentHTML():
   return "</BODY>" + EOL + \
          "</HTML>" + EOL
