__author__ = "Ricardo Fernandes (ricardo.fernandes@esss.se)"
__contributor__ = "Han Lee (han.lee@esss.se)"
__copyright__ = "(C) 2015-2016 European Spallation Source (ESS)"
__license__ = "LGPL3"
__version__ = "1.2.1"
__date__ = "2016/FEB/24"
__description__ = "Kameleon, a behavior-rich and time-aware generic simulator. This simulator, or more precisely server, receives/sends commands/statuses from/to clients through the TCP/IP protocol."
__status__ = "Development"


# ============================
#  IMPORT PACKAGES (some packages are not needed by Kameleon itself but may be in .kam files - this is to easier end-users' life)
# ============================
import sys
import os
import math
import socket
import random
import datetime
import time
import thread
import traceback


# ============================
#  GLOBAL VARIABLES (internal to Kameleon and should not be consumed by end-users in .kam files)
# ============================
_COMMANDS = []
_STATUSES = []
_CONNECTION = None
_TIME_GRANULARITY = 10	# maximum time granularity in milliseconds (if end-users' needs are more demanding, Kameleon will be updated to cope with this)
_QUIET = False


# ============================
#  GLOBAL VARIABLES (may be consumed by end-users in .kam files)
# ============================
COMMAND_RECEIVED = ""	# this variable contains the command (i.e. data) that Kameleon has received from the client
TERMINATOR = ""
LF = "\n"
CR = "\r"
FIXED = 0
ENUM = 1
INCR = 2
RANDOM = 3
CUSTOM = 4


# ============================
#  FUNCTION THAT SERVES INCOMING REQUESTS
# ============================
def start_serving(port):
	global _CONNECTION
	global _STATUSES
	global COMMAND_RECEIVED

	# create/open socket (wait if not available)
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	while True:
		try:
			server_socket.bind(("", port))
			break
		except:
			print_message("Waiting for port '%d' to be released." % port)
			time.sleep(2)

	# print some info about .kam files being consumed
	for i in range(len(_COMMANDS)):
		print_message("Using file '%s' (contains %d commands and %s statuses)." % (_COMMANDS[i][0], len(_COMMANDS[i]) - 1, len(_STATUSES[i]) - 1))
	print_message("Start serving at port '%d'." % port)

	# process incoming requests
	thread.start_new_thread(process_statuses, ())
	while True:
		server_socket.listen(1)
		connection, _ = server_socket.accept()
		print_message("Client connection opened.")
		_CONNECTION = connection

		while True:
			try:
				COMMAND_RECEIVED = connection.recv(1024)
			except:
				COMMAND_RECEIVED = ""

			if COMMAND_RECEIVED == "":
				_CONNECTION = None
				connection.shutdown(socket.SHUT_WR)
				connection.close()
				print_message("Client connection closed.")
				break

			for i in range(len(_COMMANDS)):
				flag0 = False
				for j in range(1, len(_COMMANDS[i])):
					description, command, status, wait = _COMMANDS[i][j]
					if command.startswith("***") is True:
						if command.endswith("***") is True:
							if TERMINATOR == "":
								flag1 = (COMMAND_RECEIVED.find(command[3:-3]) != -1)
							else:
								flag1 = (COMMAND_RECEIVED.find(command[3:-3]) != -1 and COMMAND_RECEIVED.endswith(TERMINATOR))
						else:
							tmp = command[3:] + TERMINATOR
							flag1 = COMMAND_RECEIVED.endswith(tmp)
					else:
						if command.endswith("***") is True:
							if TERMINATOR == "":
								flag1 = COMMAND_RECEIVED.startswith(command[:-3])
							else:
								flag1 = (COMMAND_RECEIVED.startswith(command[:-3]) and COMMAND_RECEIVED.endswith(TERMINATOR))
						else:
							tmp = command + TERMINATOR
							flag1 = (COMMAND_RECEIVED == tmp)
					if flag1:
						flag0 = True
						print_message("Command '%s' (%s) received from client." % (convert_hex(COMMAND_RECEIVED), description))
						if type(status) is list:
							for tmp in status:
								if tmp > 0:
									if wait > 0:
										_STATUSES[i][tmp][7] = wait
									else:
										send_status(_STATUSES[i][tmp])
						else:
							if status > 0:
								if wait > 0:
									_STATUSES[i][status][7] = wait
								else:
									send_status(_STATUSES[i][status])
				if flag0 is False:
					print_message("Unknown command '%s' received from client." % convert_hex(COMMAND_RECEIVED))


# ============================
#  FUNCTION TO PRINT MESSAGE ALONG WITH A TIMESTAMP
# ============================
def print_message(message):
	if _QUIET is False:
		now = datetime.datetime.now()
		print "[%02d:%02d:%02d.%03d] %s" % (now.hour, now.minute, now.second, now.microsecond / 1000.0, message)


# ============================
#  FUNCTION TO PROCESS STATUSES THAT HAVE TIMED-OUT
# ============================
def process_statuses():
	while True:
		for status in _STATUSES:
			for i in range(1, len(status)):
				description, behavior, prefix, suffix, value, timeout, remaining0, remaining1, last_value = status[i]
				if timeout > 0:
					tmp = remaining0 - _TIME_GRANULARITY
					if tmp > 0:
						status[i][6] = tmp
					else:
						status[i][6] = timeout
						send_status(status[i])
				if remaining1 > 0:
					tmp = remaining1 - _TIME_GRANULARITY
					if tmp > 0:
						status[i][7] = tmp
					else:
						status[i][7] = 0
						send_status(status[i])
		time.sleep(_TIME_GRANULARITY / 1000.0)


# ============================
#  FUNCTION TO SEND STATUS TO THE CLIENT
# ============================
def send_status(status):
	description, behavior, prefix, suffix, value, timeout, remaining0, remaining1, last_value = status
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
			status[8] = tmp

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
			status[8] = tmp

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
		tmp = result + TERMINATOR
		_CONNECTION.sendall(tmp)
		print_message("Status '%s' (%s) sent to client." % (convert_hex(tmp), description))
	except:
		pass   # no need to print the exception as most probably it is due to the connection being closed in the meantime


# ============================
#  FUNCTION TO CONVERT CHARs BELOW 32 INTO A TEXTUAL REPRESENTATION
# ============================
def convert_hex(text):
	result = ""
	for c in text:
		if ord(c) < 32:
			result = "%s<%s>" % (result, format(ord(c), "#04x")) 	# convert char into a textual representation
		else:
			result = "%s%s" % (result, c)	# no conversion (i.e. char is used verbatim)
	return result


# ============================
#  FUNCTION TO SHOW THE HEADER OF THE TOOL
# ============================
def show_header():
	tmp = "Kameleon v%s (%s - %s)" % (__version__, __date__, __status__)
	i = len(__copyright__)
	print
	print "*" * (i + 6)
	print "*  %s  *" % (" " * i)
	print "*  %s %s *" % (tmp, " " * (i - len(tmp)))
	print "*  %s  *" % (" " * i)
	print "*  %s  *" % (" " * i)
	print "*  %s  *" % __copyright__
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
	port = 9999


	# ============================
	#  PROCESS ARGUMENTS
	# ============================
	terminator = None
	for argument in sys.argv[1:]:
		if argument.upper() == "--HELP":
			show_header()
			print "  --help          Show this help."
			print
			print "  --quiet         Do not show info messages when running."
			print
			print "  --port=X        Serve at port 'X'. If not specified, default port is '%d'." % port
			print
			print "  --file=X        Use file 'X' which describes the commands/statuses to"
			print "                  receive/send from/to clients. Multiple files can be used"
			print "                  at once by separating these with a comma (,)."
			print
			print "  --terminator=X  Define 'X' as the terminator of the commands/statuses. It can"
			print "                  either be an arbitrary string (e.g. 'END') or one of the"
			print "                  following pre-defined terminators:"
			print "                     LF   : line feed (0xA)"
			print "                     CR   : carriage return (0xD)"
			print "                     LF+CR: line feed (0xA) followed by a carriage return (0xD)"
			print "                     CR+LF: carriage return (0xD) followed by a line feed (0xA)"
			print
			sys.exit(0)

		elif argument.upper() == "--QUIET":
			_QUIET = True

		elif argument[:7].upper() == "--PORT=":
			tmp = argument[7:].strip()
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

		elif argument[:7].upper() == "--FILE=":
			file_list = argument[7:].strip()
			if file_list == "":
				print "Please specify the file that describes the commands/statuses to receive/send from/to clients."
				print
				sys.exit(-1)

			for tmp in file_list.split(","):
				# read file
				try:
					handler = open(tmp, "rb")
					content = handler.read()
					handler.close()
				except:
					print "Error when reading file '%s'." % tmp
					print
					sys.exit(-1)

				# evaluate file content
				try:
					exec(content)
				except Exception as e:
					_, _, trace_back = sys.exc_info()
					print "Error when processing line #%d in file '%s' (description: %s)." % (traceback.extract_tb(trace_back)[-1][1], tmp, e)
					print
					sys.exit(-1)

				# process STATUSES list
				status_list = [tmp]
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
							status_list.append([description, behavior, prefix, suffix, value, timeout, 0, 0, None])
						else:
							print "The status #%d in list 'STATUSES' has an incorrect form." % count
				except:
					print "The list 'STATUSES' is missing in file '%s' or its form incorrect." % tmp
				_STATUSES.append(status_list)

				# process COMMANDS list
				command_list = [tmp]
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
							length = len(status_list) - 1
							if type(status) is list:
								for i in range(len(status)):
									if status[i] < 0 or status[i] > length:
										print "The command '%s' in list 'COMMANDS' points to status #%d which does not exist in list 'STATUSES'." % (description, status[i])
										status[i] = 0
							else:
								if status < 0 or status > length:
									print "The command '%s' in list 'COMMANDS' points to status #%d which does not exist in list 'STATUSES'." % (description, status)
									status = 0
							command_list.append([description, command, status, wait])
						else:
								print "The command #%d in list 'COMMANDS' has an incorrect form." % count
				except:
					print "The list 'COMMANDS' is missing in file '%s' or its form incorrect." % tmp
				_COMMANDS.append(command_list)

		elif argument[:13].upper() == "--TERMINATOR=":
			terminator = argument[13:]

		else:
			print "Parameter '%s' invalid. Please execute with '--help' to see valid parameters." % argument
			print
			sys.exit(-1)


	# ============================
	#  SETUP TERMINATOR IF DEFINED THROUGH THE PARAMETER (this will overwrite the terminator defined in the .kam file)
	# ============================
	if terminator is None:
		TERMINATOR = str(TERMINATOR)
	else:
		tmp = terminator.replace(" ", "").upper()
		if tmp == "LF":
			TERMINATOR = LF
		elif tmp == "CR":
			TERMINATOR = CR
		elif tmp == "LF+CR":
			TERMINATOR = LF + CR
		elif tmp == "CR+LF":
			TERMINATOR = CR + LF
		else:
			TERMINATOR = terminator


	# ============================
	#  DISPLAY HEADER (if not in quiet mode)
	# ============================
	if _QUIET is False:
		show_header()


	# ============================
	#  START SERVING
	# ============================
	try:
		start_serving(port)
		sys.exit(0)
	except KeyboardInterrupt:
		print_message("Stop serving due to user request.")
		sys.exit(0)
	except Exception as e:
		print_message("Stop serving due to an error (description: %s)." % e)
		sys.exit(-1)
