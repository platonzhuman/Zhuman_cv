import numpy as np
import socket      

host = "84.237.21.36"
port = 5152

# for need give bite me
def recvall(sock, n):
    date = b""  
    while len(date) < n:  
        part = sock.recv(n - len(date))  
        if not part:  
            return None
        date += part  
    return date

#connect servak
sock = socket.socket()
sock.connect((host, port))

#obrabotka isob
for i in range(10):
    sock.send(b"get")
    
    packet = recvall(sock, 40002)
    rows = packet[0]
    cols = packet[1]
    
    img = np.frombuffer(packet[2:], dtype=np.uint8)
    img = img.reshape(200, 200)
    img = img.copy()

    #max element check
    pos1 = np.unravel_index(np.argmax(img), img.shape)
    y1, x1 = pos1  


    img[max(0, y1-10):min(200, y1+10), max(0, x1-10):min(200, x1+10)] = 0
    #max element twow check
    pos2 = np.unravel_index(np.argmax(img), img.shape)
    y2, x2 = pos2

    dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
 
    result = round(dist, 1)

    print(f"{i+1} kartinka ===  rass = {result}")
  
    sock.send(str(result).encode())

sock.close()