import random
import socket
import struct
import threading
import msvcrt

stop_game = False

def stop_game_func(server_socket,asd):
    global stop_game
    print(server_socket.recv(1024))
    stop_game = True
while True:
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('', 13117))
        feedbeef = bytes([0xfe,0xed,0xbe,0xef])
        while True:
            pack, address = server_socket.recvfrom(1024)
            message = struct.unpack('!III', pack)
            x = [x for x in message]
            print(x)
            if x[0] == int(0xfeedbeef) :
                port = x[2]
                print(port)
                break
        print(address[0])
        print(port)
        print((address[0],port))
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((address[0],port))
        server_socket.sendall(b'Gal')
        Welcome = server_socket.recv(1024)
        print(Welcome.decode("utf-8"))
        threading.Thread(target=stop_game_func, args=(server_socket,213)).start()
        ###global stop_game
        while not stop_game:
            if msvcrt.kbhit():
                print('pressed')
                char = msvcrt.getch() 
                server_socket.sendall(char)
        Victory = server_socket.recv(1024)
        print(Victory.decode("utf-8"))

    except:
        print("errorororoororor")
