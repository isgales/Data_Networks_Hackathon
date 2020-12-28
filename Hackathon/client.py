import random
import socket
import struct
import threading
import msvcrt
import traceback

stop_game = False
break_game = False

def stop_game_func(server_socket,asd):
    global stop_game, break_game
    server_socket.settimeout(10.1)
    try:
        msg = server_socket.recv(1024)
        if msg == b'break':
            break_game =True
    except socket.timeout:
        print('recv timeout client')
        break_game =True
    stop_game = True


def getServerSocket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', 13117))
    # feedbeef = bytes([0xfe,0xed,0xbe,0xef])
    while True:
        pack, address = server_socket.recvfrom(1024)
        message = struct.unpack('!III', pack)
        x = [x for x in message]
        if x[0] == int(0xfeedbeef) :
            port = x[2]
            break
    return address[0],port

def playGame(server_socket):
    global stop_game
    while not stop_game:
        if msvcrt.kbhit():
            print(msvcrt.kbhit())
            char = msvcrt.getch() 
            server_socket.sendall(char)
        if break_game:
            print("yalla bye")
            server_socket.close()
            continue

while True:
    stop_game = False
    break_game = False
    try:
        # get server socket details
        address, port = getServerSocket()
        # connect to this socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((address,port))
        server_socket.sendall(b'Gal\n')
        # recieve welcome msg
        Welcome = server_socket.recv(1024)
        print(Welcome.decode("utf-8"))
        # start thread awaiting to stop the game, in the meanwhile, play
       
       
       
        threading.Thread(target=stop_game_func, args=(server_socket,213)).start()
        playGame(server_socket)
        
        
        
        # shutdown msg 
        server_socket.shutdown(socket.SHUT_WR)
        # recieve victory msg
        Victory = server_socket.recv(1024)
        print(Victory.decode("utf-8")) 
        server_socket.shutdown(socket.SHUT_RD)
    except socket.timeout:
        print("timeout")
    except:
        traceback.print_exc()
        print("errorororoororor")
