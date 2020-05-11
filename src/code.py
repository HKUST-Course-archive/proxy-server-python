import socket
import threading
import sys

SERVER_PORT = 32101
BUFF_SIZE = 65536
MAX_THREAD = 100

def get_header_value(data, tag):
    data = data.split(b'\r\n')
    for line in data:
        if (line.find(tag) == -1):
            return None
        return line[line.find(b':')+1:]

def recvall(sock):
    data = b''
    while True:
        try:
            part = sock.recv(BUFF_SIZE)
        except: 
            data = b'0'
            break
        if not part: break
        data += part
        if len(part) < BUFF_SIZE:
            break
    return data

def request_func(sock):
    #print("Peer IP: " + str(sock.getpeername()[0]) + ":" + str(sock.getpeername()[1]))
    data = recvall(sock)
    if (data == b''):
        sock.close()
        return
    sock.setblocking(0)
    flag = True
    requestLine = data.split(b'\r\n')[0]
    url = requestLine.split(b' ')[1]
    #print(requestLine)
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
        proxySocket.setblocking(0)
        while (data != b''):
            if (data != b'0'):
                dataRequest = requestLine.split(b' ')[0] + b" " + relativePath + b" " + requestLine.split(b' ')[2].split(b'\r\n')[0] + data[data.find(b'\r\n'):]
                proxySocket.sendall(dataRequest)
            dataReceive = recvall(proxySocket)
            if (dataReceive != b'0'):
                sock.sendall(dataReceive)
            data = recvall(sock)
        #print(dataRequest)
        proxySocket.close()
    elif (requestLine.split(b' ')[0] == b'CONNECT'):
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
    print("closed")
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
    thread = threading.Thread(target=request_func, args=(connfd,), daemon=True)
    thread.start()

for i in threading.enumerate():
    i.join()
