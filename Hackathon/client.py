#!/usr/bin/env python3
import socket
import struct
import threading
# Windows
import msvcrt
# Linux
#import getch
import traceback

stop_game = False
break_game = False
VictoryPrint = " "
UDP_PORT = 13117
Magic_cookie = 0xfeedbeef
Client_Name = 'BABY GOT ACK'

def stop_game_func(server_socket):
    """
    seperated thread should enter this function, and wait for victory msg from server.
    Timeout is set to be 12 seconds, just in case of mis-matching time sync.
    param: server_socket: client's socket.
    """
    global stop_game, break_game, VictoryPrint
    server_socket.settimeout(12)
    try:
        VictoryPrint = server_socket.recv(1024)       
    except :
        # got timeout, raise flag to 'break' the game.
        break_game =True
    # Raise flag to stop the game, since we got victory msg.
    stop_game = True

def getServerSocket():
    """
    Get the server socket, wait for incoming offers in port 13117 via UDP.
    When connection is established, check for magic coockie, and if it matches, extract the TCP port
    to be connected to.
    return: IP address of server, TCP port to connect.
    """
    print('Client started, listening for offer requests...')
    global UDP_PORT, Magic_cookie
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', UDP_PORT))
    while True:
        pack, address = server_socket.recvfrom(1024)
        try:
            # Interpret the msg by: I - 4 bytes, b - 1 byte, H - 2 bytes.
            message = struct.unpack('>IbH', pack)
            # Extract the message components.
            x = [x for x in message]
            if x[0] == int(Magic_cookie) :
                port = x[2]
                break
        except:
            pass
    print(f'Received offer from {address[0]}, attempting to connect...')
    return address[0],port

def playGame(server_socket):
    """
    function simulates the game.
    while flag is not raised, get presses from keyboard, and send it via the socket to the server.
    if 'break_game' is true, stop the game.
    param: server_socket: client's socket.
    """
    global stop_game
    while not stop_game:
        # Linux ver: remover if and char
        # char = getch.getch()
        if msvcrt.kbhit():
            char = msvcrt.getch() 
            try:
                server_socket.send(bytes(char))
            except BrokenPipeError:
                pass
            except :
                pass
        if break_game:
            break

"""
Main run of the client. 'While True' because of the demand that the client runs until the user stops the program.
Get the server's socket, connect to it, play the game, and repeat everything.
"""
while True:
    stop_game = False
    break_game = False
    VictoryPrint = " "
    try:
        # get server socket details
        address, port = getServerSocket()
        # connect to this socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((address,port))
        server_socket.sendall(bytes(Client_Name+"\n","utf-8"))
        # recieve welcome msg
        Welcome = server_socket.recv(1024)
        print(Welcome.decode("utf-8"))
        # start thread awaiting to stop the game, in the meanwhile, play
        threading.Thread(target=stop_game_func, args=(server_socket,)).start()
        playGame(server_socket)
        # game is done, close the socket.
        server_socket.close()
        # recieve victory msg
        if type(VictoryPrint) is str:
            print(VictoryPrint)
        else:
            print(VictoryPrint.decode("utf-8"))     
    except:
        server_socket.close()
    print('Server disconnected, listening for offer requests...')
