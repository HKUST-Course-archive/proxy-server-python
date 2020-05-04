import socket
import threading
import sys

try:
    # IPV4, TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print("socket creation failed - %s" %(err))

port = 80
try:
    host_ip = socket.gethostbyname('www.google.com')
except socket.gaierror:
    print("There was an error resolving the host")
    sys.exit()

s.connect((host_ip, port))
s.sendall('GET / HTTP/1.0\r\n\r\n'.encode('utf-8'))
print(s.recv(1024))
s.close()