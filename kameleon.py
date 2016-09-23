__author__ = "Ricardo Fernandes (ricardo.fernandes@esss.se)"
__contributor__ = "Han Lee (han.lee@esss.se), Nicolas Senaud (nicolas.senaud@cea.fr)"
__copyright__ = "(C) 2015-2016 European Spallation Source (ESS)"
__license__ = "LGPL3"
__version__ = "1.3.2"
__date__ = "2016/SEP/23"
__description__ = "Kameleon, a behavior-rich and time-aware generic simulator. This simulator, or more precisely server, receives/sends commands/statuses from/to clients through the TCP/IP protocol."
__status__ = "Production"


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
TERMINATOR_CMD = ""
TERMINATOR_STS = ""
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
def start_serving(host, port):
	global _CONNECTION
	global _STATUSES
	global COMMAND_RECEIVED

	# create/open socket
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	# wait until socket is released
	while True:
		try:
			server_socket.bind((host, port))
			break
		except:
			if host == "":
				print_message("Waiting for port '%d' to be released." % port)
			else:
				print_message("Waiting for port '%d' from hostname '%s' to be released." % (port, host))
			time.sleep(2)

	# print info about .kam files being consumed
	for i in range(len(_COMMANDS)):
		print_message("Using file '%s' (contains %d commands and %s statuses)." % (_COMMANDS[i][0], len(_COMMANDS[i]) - 1, len(_STATUSES[i]) - 1))

	# print info about the hostname and the port where Kameleon is serving requests
	if host == "":
		print_message("Start serving from any hostname that the machine has at port '%d'." % port)
	else:
		print_message("Start serving from hostname '%s' at port '%d'." % (host, port))

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

			# client closed the connection
			if COMMAND_RECEIVED == "":
				_CONNECTION = None
				connection.shutdown(socket.SHUT_WR)
				connection.close()
				print_message("Client connection closed.")
				break

			unknown_command = True
			for i in range(len(_COMMANDS)):
				for j in range(1, len(_COMMANDS[i])):
					description, command, status, wait = _COMMANDS[i][j]
					if command.startswith("***") is True:
						if command.endswith("***") is True:
							if TERMINATOR_CMD == "":
								flag = (COMMAND_RECEIVED.find(command[3:-3]) != -1)
							else:
								flag = (COMMAND_RECEIVED.find(command[3:-3]) != -1 and COMMAND_RECEIVED.endswith(TERMINATOR_CMD))
						else:
							tmp = command[3:] + TERMINATOR_CMD
							flag = COMMAND_RECEIVED.endswith(tmp)
					else:
						if command.endswith("***") is True:
							if TERMINATOR_CMD == "":
								flag = COMMAND_RECEIVED.startswith(command[:-3])
							else:
								flag = (COMMAND_RECEIVED.startswith(command[:-3]) and COMMAND_RECEIVED.endswith(TERMINATOR_CMD))
						else:
							tmp = command + TERMINATOR_CMD
							flag = (COMMAND_RECEIVED == tmp)
					if flag:
						unknown_command = False
						print_message("Command '%s' (%s) received from client." % (convert_hex(COMMAND_RECEIVED), description))
						if type(status) is int:
							if status > 0:
								if wait > 0:
									_STATUSES[i][status][7] = wait
								else:
									send_status(_STATUSES[i][status])
						elif type(status) is list:
							for tmp in status:
								if tmp > 0:
									if wait > 0:
										_STATUSES[i][tmp][7] = wait
									else:
										send_status(_STATUSES[i][tmp])
						else:
							try:
								eval(status)
							except Exception as e:
								print e

			if unknown_command is True:
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
			tmp = eval(value)
			if tmp is None:
				result = "%s%s" % (prefix, suffix)
			else:
				result = "%s%s%s" % (prefix, tmp, suffix)

		else:
			result = None

	except Exception as e:
		print e
		result = None

	# send status (if there is one) to the client requesting it
	if result is not None:
		try:
			tmp = result + TERMINATOR_STS
			_CONNECTION.sendall(tmp)
			print_message("Status '%s' (%s) sent to client." % (convert_hex(tmp), description))
		except:
			pass   # no need to print the exception as most probably it is due to the connection with the client being closed in the meantime


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
	#  SET DEFAULT VALUES
	# ============================
	host = ""
	port = 9999
	terminator = None
	terminator_cmd = None
	terminator_sts = None


	# ============================
	#  PARSE ARGUMENTS
	# ============================
	arguments = {"HELP": None, "QUIET": None, "HOST": None, "PORT": None, "EXECUTE": None, "EXECUTE-FILE": None, "FILE": None, "TERMINATOR": None, "TERMINATOR_CMD": None, "TERMINATOR_STS": None}
	for argument in sys.argv[1:]:
		tmp = argument.upper()

		if tmp == "--HELP":
			arguments["HELP"] = True

		elif tmp == "--QUIET":
			arguments["QUIET"] = True

		elif tmp.startswith("--HOST=") is True:
			arguments["HOST"] = argument

		elif tmp.startswith("--PORT=") is True:
			arguments["PORT"] = argument

		elif tmp.startswith("--EXECUTE=") is True:
			arguments["EXECUTE"] = argument

		elif tmp.startswith("--EXECUTE-FILE=") is True:
			arguments["EXECUTE-FILE"] = argument

		elif tmp.startswith("--FILE=") is True:
			arguments["FILE"] = argument

		elif tmp.startswith("--TERMINATOR=") is True:
			arguments["TERMINATOR"] = argument

		elif tmp.startswith("--TERMINATOR_CMD=") is True:
			arguments["TERMINATOR_CMD"] = argument

		elif tmp.startswith("--TERMINATOR_STS=") is True:
			arguments["TERMINATOR_STS"] = argument

		else:
			print "Parameter '%s' invalid. Please execute with '--help' to see valid parameters." % argument
			print
			sys.exit(-1)


	# ============================
	#  PROCESS ARGUMENTS
	# ============================
	if arguments["HELP"] is not None:
		show_header()
		print " --help              Show this help."
		print
		print " --quiet             Do not show info messages when running."
		print
		print " --host=X            Serve at hostname 'X'. If not specified, the connection"
		print "                     is done in any address the machine (where Kameleon is"
		print "                     running) happens to have."
		print
		print " --port=X            Serve at port 'X'. If not specified, default port is %d." % port
		print
		print " --execute=X         Execute (i.e. evaluate) Python statement 'X'. It can be"
		print "                     useful when needing to setup certain variables that are"
		print "                     consumed in the file that describes the commands/statuses."
		print
		print " --execute-file=X    Execute (i.e. evaluate) file 'X' containing Python"
		print "                     statement(s). It can be useful when needing to setup"
		print "                     certain variables that are consumed in the file that"
		print "                     describes the commands/statuses."
		print
		print " --file=X            Use file 'X' which describes the commands/statuses to"
		print "                     receive/send from/to clients. Multiple files can be used"
		print "                     at once by separating these with a comma (,)."
		print
		print " --terminator=X      Define 'X' as the terminator of both commands and"
		print "                     and statuses. If specified, it will overwrite the"
		print "                     terminator of both commands and statuses defined in the"
		print "                     .kam file. It can either be an arbitrary string"
		print "                     (e.g. END) or one of the following pre-defined"
		print "                     terminators:"
		print "                     LF   : line feed (0xA)"
		print "                     CR   : carriage return (0xD)"
		print "                     LF+CR: line feed (0xA) followed by a carriage return (0xD)"
		print "                     CR+LF: carriage return (0xD) followed by a line feed (0xA)"
		print
		print " --terminator_cmd=X  Define 'X' as the terminator of commands. If specified, it"
		print "                     will overwrite the terminator of commands defined in the"
		print "                     .kam file. It can either be an arbitrary string (e.g. END)"
		print "                     or one of the following pre-defined terminators:"
		print "                     LF   : line feed (0xA)"
		print "                     CR   : carriage return (0xD)"
		print "                     LF+CR: line feed (0xA) followed by a carriage return (0xD)"
		print "                     CR+LF: carriage return (0xD) followed by a line feed (0xA)"
		print
		print " --terminator_sts=X  Define 'X' as the terminator of statuses. If specified, it"
		print "                     will overwrite the terminator of statuses defined in the"
		print "                     .kam file. It can either be an arbitrary string (e.g. END)"
		print "                     or one of the following pre-defined terminators:"
		print "                     LF   : line feed (0xA)"
		print "                     CR   : carriage return (0xD)"
		print "                     LF+CR: line feed (0xA) followed by a carriage return (0xD)"
		print "                     CR+LF: carriage return (0xD) followed by a line feed (0xA)"
		print
		sys.exit(0)

	if arguments["QUIET"] is not None:
		_QUIET = True

	if arguments["HOST"] is not None:
		tmp = arguments["HOST"][7:].strip()
		if tmp == "":
			print "Please specify the hostname."
			print
			sys.exit(-1)
		else:
			host = tmp

	if arguments["PORT"] is not None:
		tmp = arguments["PORT"][7:].strip()
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

	if arguments["EXECUTE"] is not None:
		tmp = arguments["EXECUTE"][10:]
		if tmp == "":
			print "Please specify the Python statement(s) to execute (i.e. evaluate)."
			print
			sys.exit(-1)

		# evaluate content
		try:
			exec(tmp)
		except Exception as e:
			print "Error when executing '%s' (description: %s)." % (tmp, e)
			print
			sys.exit(-1)

	if arguments["EXECUTE-FILE"] is not None:
		tmp = arguments["EXECUTE-FILE"][15:].strip()
		if tmp == "":
			print "Please specify the file containing Python statement(s) to execute (i.e. evaluate)."
			print
			sys.exit(-1)

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
			print "Error when processing file '%s' (description: %s)." % (tmp, e)
			print
			sys.exit(-1)

	if arguments["FILE"] is not None:
		tmp = arguments["FILE"][7:].strip()
		if tmp == "":
			print "Please specify the file that describes the commands/statuses to receive/send from/to clients."
			print
			sys.exit(-1)

		for file in tmp.split(","):
			# read file
			try:
				handler = open(file, "rb")
				content = handler.read()
				handler.close()
			except:
				print "Error when reading file '%s'." % file
				print
				sys.exit(-1)

			# evaluate file content
			try:
				exec(content)
			except Exception as e:
				print "Error when processing file '%s' (description: %s)." % (file, e)
				print
				sys.exit(-1)

			# process STATUSES list
			status_list = [file]
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
				print "The list 'STATUSES' is missing in file '%s' or its form incorrect." % file
			_STATUSES.append(status_list)

			# process COMMANDS list
			command_list = [file]
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
						if type(status) is int:
							if status < 0 or status > length:
								print "The command '%s' in list 'COMMANDS' points to status #%d which does not exist in list 'STATUSES'." % (description, status)
								status = 0
						elif type(status) is list:
							for i in range(len(status)):
								if status[i] < 0 or status[i] > length:
									print "The command '%s' in list 'COMMANDS' points to status #%d which does not exist in list 'STATUSES'." % (description, status[i])
									status[i] = 0
						command_list.append([description, command, status, wait])
					else:
							print "The command #%d in list 'COMMANDS' has an incorrect form." % count
			except:
				print "The list 'COMMANDS' is missing in file '%s' or its form incorrect." % file
			_COMMANDS.append(command_list)

	if arguments["TERMINATOR"] is not None:
		terminator = arguments["TERMINATOR"][13:]

	if arguments["TERMINATOR_CMD"] is not None:
		terminator_cmd = arguments["TERMINATOR_CMD"][17:]

	if arguments["TERMINATOR_STS"] is not None:
		terminator_sts = arguments["TERMINATOR_STS"][17:]


	# ============================
	#  SETUP TERMINATOR OF COMMANDS (this will overwrite the terminator of commands defined in the .kam file)
	# ============================
	if terminator_cmd is None:
		TERMINATOR_CMD = str(TERMINATOR_CMD)
	else:
		tmp = terminator_cmd.replace(" ", "").upper()
		if tmp == "LF":
			TERMINATOR_CMD = LF
		elif tmp == "CR":
			TERMINATOR_CMD = CR
		elif tmp == "LF+CR":
			TERMINATOR_CMD = LF + CR
		elif tmp == "CR+LF":
			TERMINATOR_CMD = CR + LF
		else:
			TERMINATOR_CMD = terminator_cmd


	# ============================
	#  SETUP TERMINATOR OF STATUSES (this will overwrite the terminator of statuses defined in the .kam file)
	# ============================
	if terminator_sts is None:
		TERMINATOR_STS = str(TERMINATOR_STS)
	else:
		tmp = terminator_sts.replace(" ", "").upper()
		if tmp == "LF":
			TERMINATOR_STS = LF
		elif tmp == "CR":
			TERMINATOR_STS = CR
		elif tmp == "LF+CR":
			TERMINATOR_STS = LF + CR
		elif tmp == "CR+LF":
			TERMINATOR_STS = CR + LF
		else:
			TERMINATOR_STS = terminator_sts


	# ============================
	#  SETUP TERMINATOR OF BOTH COMMANDS AND STATUSES (this will overwrite the terminator of both commands and statuses defined through parameters or in the .kam file)
	# ============================
	if terminator is not None:
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
		TERMINATOR_CMD = TERMINATOR
		TERMINATOR_STS = TERMINATOR


	# ============================
	#  DISPLAY HEADER (if not in quiet mode)
	# ============================
	if _QUIET is False:
		show_header()


	# ============================
	#  START SERVING
	# ============================
	try:
		start_serving(host, port)
		sys.exit(0)
	except KeyboardInterrupt:
		print_message("Stop serving due to user request.")
		sys.exit(0)
	except Exception as e:
		print_message("Stop serving due to an error (description: %s)." % e)
		sys.exit(-1)

