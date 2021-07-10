###Name - Subramanyam MNS, Pradeep Yarlagadda

###Instructions
####Server

- Go to server directory
```
python server.py
```

####Proxy
- Go to proxy directory
```
python proxy.py
```

- Main server will be running on localhost with port 20000.
- Proxy server starts running on localhost with port 60005.
- Set proxy in the browser and the files can be downloaded from the server http://localhost:20000.

####Curl Request Syntax
```
curl -i -H "Accept: application/json" -H "Content-Type: application/json" -X GET http://<server_host>:<server_port>/<filename> -x http://<proxy_host>:<proxy_port>
```

####Curl Request Example
```
curl -i -H "Accept: application/json" -H "Content-Type: application/json" -X GET http://localhost:20000/2.binary -x http://localhost:60005
```


###Implementation

####Proxy Server
- The client requests the object via the proxy server. It handles only HTTP GET requests.
- If the request is already cached it verifies whether the file is modified or not based on the response either updates the cache or sends the same file.

####Caching
- The cache holds at max 3 responses.
- The responses will be stored based on cache-control ie., 
	1) 'no-cache' => The file cannot be cached.
	2) 'must-revalidate' => The file is cached and verified before sending to the client.

####Bonus
- The proxy server is a non-blocking server which can handle multiple client requests.
- Implemented multiple requests at the same time using threading and synchronized the cache access using thread locks.
