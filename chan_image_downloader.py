import urllib.request
from urllib.error import HTTPError
import json
import os
import shutil
import threading
import sys
from datetime import datetime

#Thread safe print function
print = lambda x : sys.stdout.write("%s\n" % x)

board_url_format = "https://a.4cdn.org/{}/threads.json"
thread_url_format = "https://a.4cdn.org/{}/thread/{}.json"
image_url_format = "https://i.4cdn.org/{}/{}{}"
save_folder_format = "img/{}/{}"
save_image_format = "img/{}/{}/{}{}"
save_thread_list = "img/saved.txt"
save_thread_list_backup_format = "img/saved_{}.txt"


def downloadThreadSetDefaults(board, thread):
    save = input("Save thread in updater (Y/n): ").strip().lower() == "y"
    downloadThread(board, thread, save)
    

def downloadThread(board, thread, save=True):
    #TODO Check the last modified
    #Reset counters that are returned
    counterImage = 0
    counterImageWrite = 0
    print("{}/{}: Checking thread".format(board, thread))
    url = thread_url_format.format(board, thread)
    with urllib.request.urlopen(url) as page:
        pageJson = json.loads(page.read().decode('utf-8'))
        #Create the local directory
        os.makedirs(save_folder_format.format(board, thread), exist_ok=True)
        #Reset counters
        counterPost = 0
        counterPostTotal = len(pageJson['posts'])
        #Loop posts
        for post in pageJson['posts']:
            counterPost += 1
            print("{}/{}: Processing post {}/{}".format(board, thread, counterPost, counterPostTotal))
            if 'tim' in post:
                counterImage += 1
                save_img = save_image_format.format(board, thread, post['tim'], post['ext'])
                if not os.path.isfile(save_img):
                    counterImageWrite += 1
                    url = image_url_format.format(board, post['tim'], post['ext'])
                    urllib.request.urlretrieve(url, save_img)
        #Print counters
        print("{}/{}: New images saved: {}/{}".format(board, thread, counterImageWrite, counterImage))
        if save:
            #Check thread is not already in the saved list
            no_match = True
            if os.path.isfile(save_thread_list):
                with open(save_thread_list, 'r') as fin:
                    for saved_thread in fin:
                        board_thread = saved_thread.strip().split("/")
                        if board_thread[0] == board and board_thread[1] == thread:
                            no_match = False
                            break
            if no_match:
                #Write thread to saved list
                print("{}/{}: Saving thread".format(board, thread))
                with open(save_thread_list, 'a') as fout:
                    #TODO Write last modified
                    fout.write(board+"/"+thread+"\n")
            else:
                print("{}/{}: Thread already saved".format(board, thread))
    return (counterImage, counterImageWrite)


def downloadSavedThreadsSetDefaults():
    backupSave = input("Backup saved threads (y/N): ").strip().lower() == "y"
    threaded = input("Experimental Threading (y/N): ").strip().lower() == "y"
    if threaded:
        print("WARNING: You may encounter errors and be unable to stop the program.")
        print("WARNING: Pause on completed will not work with this option.")
        threaded = input("Experimental Threading confirm (y/N): ").strip().lower() == "y"
    downloadSavedThreads(threaded, backupSave)
    

def downloadSavedThreads(threaded=False, backup_save=False):
    if backup_save:
        shutil.copy2(save_thread_list, save_thread_list_backup_format.format(datetime.now().strftime('%y%m%d')))
        print("Saved threads backed up")
    if threaded:
        print("Running multi-threaded")
        global pause_on_done
        pause_on_done = False
    else:
        print("Running single-threaded")
    #Load file into memory
    with open(save_thread_list, 'r') as fin:
        board_threads = []
        for saved_thread in fin:
            board_threads.append(saved_thread.strip().split("/"))
    print("Checking {} threads".format(len(board_threads)))
    #Delete file
    os.remove(save_thread_list)
    #Reset counters
    totalImage = 0
    totalImageWrite = 0
    #Download list from stored
    for board_thread in board_threads:
        ts = []
        try:
            if threaded:
                t = threading.Thread(target=downloadThread, args=(board_thread[0], board_thread[1]))
                t.daemon = True
                ts.append(t)
                t.start()
            else:
                countImage, countWrite = downloadThread(board_thread[0], board_thread[1])
                totalImage += countImage
                totalImageWrite += countWrite
        except HTTPError:
            #Thread probably 404, skip it and continue
            print("{}/{}: Probably 404".format(board_thread[0], board_thread[1]))
    #Loop over threads unless an Interrupt is sent
    try:
        for t in ts:
            while t.isAlive():
                t.join(1)
    except (KeyboardInterrupt, SystemExit):
        print("Attempting to stop threads")
        exit()
    if not threaded:
        print("New images saved: {}/{}".format(totalImageWrite, totalImage))
        

def downloadBoardSetDefaults(board):
    save_threads = input("Save threads (y/N): ").strip().lower() == "y"
    downloadBoard(board, save_threads)


def downloadBoard(board, save_threads=False):
    url = board_url_format.format(board)
    with urllib.request.urlopen(url) as page:
        pageJson = json.loads(page.read().decode('utf-8'))
        for p in pageJson:
            print("/{}/: page {}".format(board, p['page']))
            for thread in p['threads']:
                try:
                    downloadThread(board, str(thread['no']), save_threads)
                except HTTPError:
                    #Thread probably 404, skip it and continue
                    print("{}/{}: Probably 404".format(board, str(thread['no'])))
                

if __name__ == "__main__":
    board = input("Enter board: ").strip().lower()
    thread = input("Enter thread: ").strip().lower()
    set_defaults = not input("Use default settings (Y/n): ").strip().lower() == "n"
    pause_on_done = False
    if not set_defaults:
        pause_on_done = input("Pause when completed (y/N): ").strip().lower() == "y"
    if board is '' and thread is '':
        print("Downloading from stored list")
        if set_defaults:
            downloadSavedThreads()
        else:
            downloadSavedThreadsSetDefaults()
    elif not board is '' and thread is '':
        print("Download board")
        if set_defaults:
            downloadBoard(board)
        else:
            downloadBoardSetDefaults(board)
    else:
        if set_defaults:
            downloadThread(board, thread)
        else:
            downloadThreadSetDefaults(board, thread)
    if pause_on_done:
        input("Completed. Press any key to exit")
