__author__ = "Ricardo Fernandes"
__email__ = "ricardo.fernandes@esss.se"
__copyright__ = "(C) 2015 European Spallation Source (ESS)"
__license__ = "LGPL3"
__version__ = "1.0.0"
__date__ = "2015/MAR/13"
__description__ = "Kameleon, a behavior-rich and time-aware generic simulator. This server receives/sends commands/statuses from/to clients through the TCP/IP protocol."
__status__ = "Production"


# ============================
#  IMPORT PACKAGES
# ============================
import sys
import os
import math
import socket
import random
import datetime
import time
import thread


# ============================
#  GLOBAL VARIABLES
# ============================
_COMMANDS = []
_STATUSES = []
_CONNECTION = None
_TIMEOUT = 10.0
_QUIET = False
FIXED = 0
ENUM = 1
INCR = 2
RANDOM = 3
CUSTOM = 4


# ============================
#  FUNCTION THAT SERVES INCOMING REQUESTS
# ============================
def start_serving(host, port, config_file):
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	while True:
		try:
			server_socket.bind((host, port))
			break
		except:
			print_message("Waiting for port '%d' at host '%s' to be released." % (port, host))
			time.sleep(2)
	if config_file is None:
		print_message("Start serving at host '%s' in port '%d'." % (host, port))
	else:
		print_message("Start serving at host '%s' in port '%d' using file '%s' (contains %d commands and %s statuses)." % (host, port, config_file, len(_COMMANDS), len(_STATUSES)))
	thread.start_new_thread(process_statuses, ())
	while True:
		server_socket.listen(1)
		connection, _ = server_socket.accept()
		print_message("Client connection opened.")
		globals()["_CONNECTION"] = connection
		while True:
			try:
				data = connection.recv(1024)
			except:
				data = ""
			if data == "":
				globals()["_CONNECTION"] = None
				connection.close()
				print_message("Client connection closed.")
				break
			else:
				flag = False
				for element in _COMMANDS:
					description, command, status, wait = element
					if data == command:
						flag = True
						print_message("Command '%s' (%s) received from client." % (convert_hex(command), description))
						if status > 0:
							if wait > 0:
								globals()["_STATUSES"][status - 1][7] = wait
							else:
								send_status(_STATUSES[status - 1])
				if flag is False:
					print_message("Unknown command '%s' received from client." % convert_hex(data))


# ============================
#  FUNCTION TO PRINT MESSAGE ALONG WITH A TIMESTAMP
# ============================
def print_message(message):
	if _QUIET is False:
		now = datetime.datetime.now()
		print "[%02d:%02d:%02d] %s" % (now.hour, now.minute, now.second, message)


# ============================
#  FUNCTION TO PROCESS STATUSES THAT HAVE TIMED-OUT
# ============================
def process_statuses():
	while True:
		for element in _STATUSES:
			description, behavior, prefix, suffix, value, timeout, remaining0, remaining1, last_value = element
			if timeout > 0:
				remaining = remaining0 - _TIMEOUT
				if remaining > 0:
					element[6] = remaining
				else:
					element[6] = timeout
					send_status(element)
			if remaining1 > 0:
				remaining = remaining1 - _TIMEOUT
				if remaining > 0:
					element[7] = remaining
				else:
					element[7] = 0
					send_status(element)
		time.sleep(_TIMEOUT / 1000.0)


# ============================
#  FUNCTION TO SEND STATUS TO THE CLIENT
# ============================
def send_status(element):
	description, behavior, prefix, suffix, value, timeout, remaining0, remaining1, last_value = element
	try:
		if behavior == FIXED:
			result = "%s%s%s" % (prefix, value, suffix)
		elif behavior == ENUM:
			if last_value is None:
				if type(value) is list:
					tmp = value[0]
				else:
					tmp = value
			else:
				if type(value) is list:
					try:
						tmp = value[value.index(last_value) + 1]
					except:
						tmp = value[0]
				else:
					tmp = value
			result = "%s%s%s" % (prefix, tmp, suffix)
			element[8] = tmp
		elif behavior == INCR:
			if last_value is None:
				if type(value) is list:
					if int(value[2]) > 0:
						tmp = value[0]
					else:
						tmp = value[1]
				else:
					tmp = "0"
			else:
				if type(value) is list:
					i = int(last_value) + int(value[2])
					if int(value[2]) > 0:
						if i > int(value[1]):
							tmp = value[0]
						else:
							tmp = i
					else:
						if i < int(value[0]):
							tmp = value[1]
						else:
							tmp = i
				else:
					tmp = int(last_value) + int(value)
			result = "%s%s%s" % (prefix, tmp, suffix)
			element[8] = tmp
		elif behavior == RANDOM:
			if type(value) is list:
				i = int(value[0])
				j = int(value[1])
				if i > j or (i == 0 and j == 0):
					result = "%s0%s" % (prefix, suffix)
				else:
					result = "%s%s%s" % (prefix, random.randrange(i, j + 1), suffix)
			else:
				i = int(value)
				if i == 0:
					result = "%s0%s" % (prefix, suffix)
				elif i > 0:
					result = "%s%s%s" % (prefix, random.randrange(0, i + 1), suffix)
				else:
					result = "%s%s%s" % (prefix, random.randrange(i, 1), suffix)
		elif behavior == CUSTOM:
			result = "%s%s%s" % (prefix, eval(value), suffix)
		else:
			result = ""
	except Exception as e:
		print e
		result = ""
	try:
		_CONNECTION.sendall(result)
		print_message("Status '%s' (%s) sent to client." % (convert_hex(result), description))
	except:
		pass   # no need to print the exception as most probably it is due to the connection be closed in the meantime


# ============================
#  FUNCTION TO CONVERT CHARs BELOW 32 INTO A TEXTUAL REPRESENTATION
# ============================
def convert_hex(text):
	result = ""
	for c in text:
		if ord(c) < 32:
			result = "%s<%s>" % (result, format(ord(c), "#04x"))
		else:
			result = "%s%s" % (result, c)
	return result


# ============================
#  FUNCTION TO SHOW THE HEADER OF THE TOOL
# ============================
def show_header():
	tmp = "Kameleon v%s (%s - %s)" % (__version__, __date__, __status__)
	i = len(tmp)
	print
	print "*" * (i + 6)
	print "*  %s  *" % (" " * i)
	print "*  %s  *" % tmp
	print "*  %s  *" % (" " * i)
	print "*  %s  *" % (" " * i)
	print "*  %s%s  *" % (__copyright__, " " * (len(tmp) - len(__copyright__)))
	print "*  %s  *" % (" " * i)
	print "*" * (i + 6)
	print


# ============================
#  MAIN PROGRAM
# ============================
if __name__ == "__main__":


	# ============================
	#  DEFAULT VALUES
	# ============================
	host = "127.0.0.1"
	port = 9999
	config_file = None


	# ============================
	#  PROCESS ARGUMENTS
	# ============================
	for argument in sys.argv[1:]:
		if argument.upper() == "-HELP":
			show_header()
			print "  -help       Show this help."
			print "  -quiet      Do not show info messages when running."
			print "  -port:X     Serve at port 'X'. If not specified, default port is '%d'." % port
			print "  -file:X     Use file 'X' which describes the commands/statuses to receive/send from/to clients."
			print
			sys.exit(0)
		elif argument[:6].upper() == "-QUIET":
			_QUIET = True
		elif argument[:6].upper() == "-PORT:":
			tmp = argument[6:].strip()
			if tmp == "":
				print "Please specify the port number."
				print
				sys.exit(-1)
			else:
				try:
					port = int(tmp)
				except:
					print "Port '%s' invalid." % tmp
					print
					sys.exit(-1)
		elif argument[:6].upper() == "-FILE:":
			config_file = argument[6:].strip()
			if config_file == "":
				print "Please specify the file that describes the commands/statuses to receive/send from/to clients."
				print
				sys.exit(-1)
			else:
				try:
					handler = open(config_file, "rb")
					content = handler.read()
					handler.close()
				except:
					print "Error when reading file '%s'." % config_file
					print
					sys.exit(-1)
				try:
					exec(content)
				except Exception as e:
					print "Error when processing line '%d' in file '%s' (description: %s)." % (e.lineno, config_file, e)
					print
					sys.exit(-1)
				try:
					count = 0
					for element in STATUSES:
						count = count + 1
						i = len(element)
						if i == 3:
							description, behavior, value = element
							prefix = ""
							suffix = ""
							timeout = 0
							flag = True
						elif i == 4:
							description, behavior, value, prefix = element
							suffix = ""
							timeout = 0
							flag = True
						elif i == 5:
							description, behavior, value, prefix, suffix = element
							timeout = 0
							flag = True
						elif i == 6:
							description, behavior, value, prefix, suffix, timeout = element
							flag = True
						else:
							flag = False
						if flag is True:
							_STATUSES.append([description, behavior, prefix, suffix, value, timeout, 0, 0, None])
						else:
							print "The status #%d in list 'STATUSES' has an incorrect form." % count
				except:
					print "The list 'STATUSES' is missing in file '%s' or its form incorrect." % config_file
				try:
					count = 0
					for element in COMMANDS:
						count = count + 1
						i = len(element)
						if i == 2:
							description, command = element
							status = 0
							wait = 0
							flag = True
						elif i == 3:
							description, command, status = element
							wait = 0
							flag = True
						elif i == 4:
							description, command, status, wait = element
							flag = True
						else:
							flag = False
						if flag is True:
							if status >= 0 and status <= len(_STATUSES):
								_COMMANDS.append([description, command, status, wait])
							else:
								print "The command '%s' in list 'COMMANDS' points to status #%d which does not exist in list 'STATUSES'." % (description, status)
								_COMMANDS.append([description, command, 0, wait])
						else:
								print "The command #%d in list 'COMMANDS' has an incorrect form." % count
				except:
					print "The list 'COMMANDS' is missing in file '%s' or its form incorrect." % config_file
		else:
			print "Parameter '%s' invalid. Please execute with '-help' to see valid parameters." % argument
			print
			sys.exit(-1)


	# ============================
	#  START SERVING
	# ============================
	if _QUIET is False:
		show_header()
	try:
		start_serving(host, port, config_file)
		sys.exit(0)
	except KeyboardInterrupt:
		print_message("Stop serving due to user request.")
		sys.exit(0)
	except Exception as e:
		print e
		print_message("Stop serving due to an error.")
		sys.exit(-1)

