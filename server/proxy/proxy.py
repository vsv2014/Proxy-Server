import socket
import sys
import time
import datetime
import threading
import thread

# host,port,path,last_Accessed,time
cache = []

def parse_request(request):
    arr = request.split('\n')

    method  = arr[0].split(' ')[0]
    url     = arr[0].split(' ')[1]
    version = arr[0].split(' ')[2]

    # Removing http://
    if(url.find("http") != -1) :
        url = url[url.find("http")+7:]

    servername  = url.split('/')[0]
    path        = '/' + '/'.join(url.split('/')[1:])
    port        = 80

    if servername.find(":") != -1:
        idx         = servername.find(":");
        port        = int(servername[idx+1:])
        servername  = servername[:idx]

    arr[0]  = method + ' ' + path + ' ' + version
    request = '\n'.join(arr)

    return [servername,port,path,request]

def is_cached(host,port,path,req,conn):
    """
        This function checks whether the request from the
        client is already cached or not.

        If cached if revalidate the cache and sends the response
        to the client
    """

    # Whether request matches obj present in cache
    cache_idx = -1
    for i in range(len(cache)):
        obj = cache[i]
        if(obj["host"] == host and obj["port"] == port and obj["path"] == path):
            cache_idx = i
            break

    if(cache_idx == -1):
        return False

    # Request is in cache so validating the cached response 
    # by sending a "conditional get" request
    time_header = "If-Modified-Since: %s" % (cache[cache_idx]["last_mod"])
    cond_req = req.split('\n')
    cond_req.insert(1,time_header)
    cond_req = '\n'.join(cond_req)

    # Sending Conditional get request
    server_socket = socket.socket()
    server_socket.connect((host, port))
    server_socket.send(cond_req)


    # Read the response from the server untill all the 
    # headers are reached
    data = ''
    while (data.find("\n\n") == -1):
        res = server_socket.recv(1024)
        if(not res):
            break
        data += res

    # If file is not modified send the cached response
    if(data.split(' ')[1] == "304" ):
        print "Response in cache is up to date, Sending cached response"
        while True:
            if(not data):
                break
            data = server_socket.recv(1024)
        send_cache(cache_idx,conn)

    # Filter the above content and store in cache
    elif(data.split(' ')[1] == "200"):
        print "Response in cache is not up to date, so updating the cache and sending the response"
        obj = {}
        obj["host"] = host
        obj["port"] = port
        obj["path"] = path
        obj["time"] = time.time()
        obj["last_mod"] = find_date(data)

        # Updating the new response in the old response idx
        idx = cache_idx
        cache[idx] = obj
        with open(str(idx), 'wb') as file:
            while data:
                file.write(data)                
                data = server_socket.recv(1024)
        file.close()
        send_cache(idx,conn)

    # Handling other response messages like 404,....
    else:
        while data:
            conn.send(data)
            data = server_socket.recv(1024)

    server_socket.close()
    return True

def find_date(data):
    """
        Takes the header response and returns the 
        correct date format required by the server 
        in the conditional get
    """
    idx = data.find("Last-Modified:")
    if (idx == -1):
        return "-1"
    # if(idx == -1) Handle this later

    date = data[idx+len("Last-Modified: "):].split("\n")[0].strip()
    return date

def cache_position():
    """
        Returns the cache index which is last accessed
        and can be replaced with new information.
    """

    # If the cache is empty
    if(len(cache) < 3):
        cache.append({})
        return len(cache)-1

    # Finding the last accessed cache and returning the index
    idx = 0
    min_time = cache[0]["time"]
    for i in range(len(cache)):
        if(min_time > cache[i]["time"]):
            idx = i

    return idx

# Change the headers
def send_cache(idx,conn):
    """
        Send cache takes the cache idx to read the file and send
        the requested file with modified Date filed in the response.
    """
    
    # Updating the last accessed time for the cache
    cache[idx]["time"] = time.time()
    
    file = open(str(idx),'r')
    data = file.read(1024)
    while data:
        conn.send(data)
        data = file.read(1024)
    file.close()


def handle_client(conn):
    """
        This function takes the connection which was accepted by the server
        and acts as proxy for the client request

        "conn" is the socket connection to the client
    """
    try:
        req = conn.recv(1024)
        if not req:
            exit(0)

        # Parse request
        host,port,path,req = parse_request(req)

        # Handle caching
        cacheLock.acquire()
        if(is_cached(host,port,path,req,conn)):
            cacheLock.release()
            exit(0)
        cacheLock.release()

        print 'Not present in cache'
        # If not in cache contacting the server and passsing
        # the request of the client
        # print('host--',host, 'port --', port)
        server_socket = socket.socket()
        server_socket.connect((host, port))
        print "Connection established with main server to send request"
        server_socket.send(req)


        # Read the response from the server untill all the 
        # headers are reached
        data = ''
        while (data.find("\n\n") == -1):
            res = server_socket.recv(1024)
            if(not res):
                break
            data += res
        
        # Check if cachable or not
        if (cache_control(data) == 'must-revalidate'):
            print 'Caching the response'
            # Storing the host port path details in the cache object
            # Time field hold when the cached object is last accessed
            # last_mod holds the date provided by the server in the file request.
            obj = {}
            obj["host"] = host
            obj["port"] = port
            obj["path"] = path
            obj["time"] = time.time()
            obj["last_mod"] = find_date(data)

            cacheLock.acquire()
            # Finding the position in the cache for replacement and storing the object
            idx = cache_position()
            cache[idx] = obj

            # Writing the response from the main server to the disk
            with open(str(idx), 'wb') as file:
                while data:
                    file.write(data)            
                    data = server_socket.recv(1024)
            file.close()
            server_socket.close()

            # Once cached sending the response from the cache file via conn
            send_cache(idx,conn)
            cacheLock.release()

            conn.close()
        elif (cache_control(data) == 'no-cache'):
            print 'File cannot be cached'
            while data:
                conn.send(data)
                data = server_socket.recv(1024)
            conn.close()
            server_socket.close()

    except Exception as e:
        conn.close()
        server_socket.close()
        
    print 'Connection closed'
    exit(0)

def cache_control(data):
    '''
        Takes the response header and returns the 
        cache control value
    '''
    idx = data.find('Cache-control')
    if idx == -1:
        return 'no-cache'
    temp = data[idx: ].split('\r\n')[0]
    return temp[len('Cache-control: '):]

def server(host,port):
    """
        Run's the proxy server on the given host and port
    """
    server = socket.socket()

    server.bind((host, port))
    server.listen(5)
    print "Proxy Server runing on port ", port

    while True:
        conn, addr = server.accept()
        print '------------------------------------------------'
        print 'Got connection from', addr

        # handle_client(conn)
        thread.start_new_thread(handle_client, (conn, ))

host = ""
port = 60005
cacheLock = threading.Lock() 

if len(sys.argv) > 1:
    port = int(sys.argv[1])

server(host,port)