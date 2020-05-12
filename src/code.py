import socket # basic lib for socket programming
import threading # for multithreading
#import sys #
import json # for processing json file (used for access control)
import hashlib # for caching function
import os.path # for caching function
import locale
from time import strftime, gmtime

SERVER_PORT = 32101
BUFF_SIZE = 65536
# max number of concurrent session
MAX_THREAD = 1000
locale.setlocale(locale.LC_TIME, 'en_US')

# Load the json file which contain a list of blacklisted URL
f = open('blacklistURL.json')
blacklist = json.load(f)
f.close()

def get_header_value(data, tag):
    data = data.split(b'\r\n')
    for line in data:
        if (line.find(tag) == -1):
            continue
        return line[line.find(b':')+1:]
    return None

# To recv all data available in the socket
def recvall(sock):
    data = b''
    contentLength = -1
    while True:
        try:
            part = sock.recv(BUFF_SIZE)
        except: 
            if (contentLength == -1):
                data = b'0'
                break
            else: continue
        if (not part) and contentLength == -1: break
        if contentLength == -1:
            contentLength = (int)(get_header_value(part, b'Content-Length').decode('utf-8')) if get_header_value(part, b'Content-Length') != None else -1
        data += part
        if (len(data[data.find(b'\r\n\r\n')+3:])-1 >= contentLength if data.find(b'\r\n\r\n') != -1 else len(part) < BUFF_SIZE):
            break
    return data

# The main function to forward connection
def request_func(sock):
    #print("Peer IP: " + str(sock.getpeername()[0]) + ":" + str(sock.getpeername()[1]))
    data = recvall(sock)
    #print(data)
    if (data == b''):
        sock.close()
        return
    sock.setblocking(0)
    requestLine = data.split(b'\r\n')[0]
    url = requestLine.split(b' ')[1]

    # Access control part
    for blacklistURL in blacklist["blacklistURL"]:
        if (blacklistURL in url.decode('utf-8')):
            sock.sendall(b'HTTP/1.1 404 Not Found\r\n\r\n')
            sock.close()
            return

    # HTTP requests
    if (requestLine.split(b' ')[0] != b'CONNECT'):
        serverName = url[7:url.find(b'/', 7)]
        relativePath = url[url.find(b'/', 7):]
        port = 80 if url.find(b':', 7) == -1 else int(url[url.find(b':', 7)+1:])
        #print(relativePath)
        try:
            proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as err:
            print("Error: init socket to connect web server\n")
        proxySocket.connect((socket.gethostbyname(serverName), port))
        while (data != b''):
            cache = False
            readedRequest = False
            if (data != b'0'):
                readedRequest = True
                requestLine = data.split(b'\r\n')[0]
                print(requestLine)
                url = requestLine.split(b' ')[1]
                relativePath = url[url.find(b'/', 7):]
                absolutePath = serverName + relativePath
                cachePath = hashlib.md5(requestLine + serverName).hexdigest()
                # Check cache exist
                if os.path.exists("cache/"+cachePath) and requestLine.split(b' ')[0] == b'GET':
                    # Check if cache is latest version
                    # print("check update needed")
                    proxySocket.sendall(b'GET ' + \
                        relativePath + \
                        b' HTTP/1.1\r\n' + \
                        b'Host:' + get_header_value(data, b'Host') + \
                        b'\r\nIf-Modified-Since: ' + \
                        strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(os.path.getmtime("cache/"+cachePath))).encode() + \
                        b'\r\n\r\n')
                    cache = True
                else:
                    dataRequest = requestLine.split(b' ')[0] + b" " + relativePath + b" " + requestLine.split(b' ')[2].split(b'\r\n')[0] + data[data.find(b'\r\n'):]
                    proxySocket.sendall(dataRequest)

            dataReceive = recvall(proxySocket)
            if (dataReceive != b'0'):
                if (cache and dataReceive.split(b' ')[1] == b'304'):
                    # read from cache
                    f = open("cache/"+cachePath, 'rb')
                    dataReceive = f.read()
                    f.close()
                    print("Return from cache")
                elif (dataReceive != b'' and readedRequest):
                    # update cache file
                    f = open("cache/"+cachePath, 'wb+')
                    f.write(dataReceive)
                    f.close()
                    print("save cache")
                #elif (dataReceive != b'' and not readedRequest):
                    # update cache file
                #    f = open("cache/"+cachePath, 'ab')
                #    f.write(dataReceive)
                #    f.close()
                elif (dataReceive == b''):
                    break
                sock.sendall(dataReceive)
            data = recvall(sock)
        #print(dataRequest)
        proxySocket.close()
    
    # HTTPS request
    elif (requestLine.split(b' ')[0] == b'CONNECT'):
        print(requestLine)
        serverName = url[:url.find(b':')]
        port = int(url[url.find(b':')+1:])
        try:
            proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as err:
            print("Error: init socket to connect web server\n")
        proxySocket.connect((socket.gethostbyname(serverName), port if port>-1 else 443))
        proxySocket.setblocking(0)
        sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
        while (data != b''):
            data = recvall(sock)
            if (data != b'0'):
                proxySocket.sendall(data)
            dataRec = recvall(proxySocket)
            if (dataRec != b'0'):
                sock.sendall(dataRec)
        proxySocket.close()
    sock.close()
    print("closed " + serverName.decode('utf-8'))
    return

# init server socket
try:
    listenfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print("Error: init socket\n")
listenfd.bind(('', SERVER_PORT)) # INADDR_ANY, PORT
listenfd.listen()
print("Proxy server running...")
print("Server IP: " + str(listenfd.getsockname()[0]) + ":" + str(listenfd.getsockname()[1]))

while True:
    print("Listening...")
    while (len(threading.enumerate()) >= MAX_THREAD):
        pass
    connfd, address = listenfd.accept()
    # multithreading
    thread = threading.Thread(target=request_func, args=(connfd,), daemon=True)
    thread.start()

for i in threading.enumerate():
    i.join()
