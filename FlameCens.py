#------------importing modules------------
import numpy as np
import librosa 
import librosa.display
import scipy
import pygame, sys, random
from pygame.locals import *
import datetime
from numba import jit
import wave  
import pyaudio
import os

if (len(sys.argv)<3):
    print("The application needs at least two audio files as input")
    sys.exit()
       
file1=sys.argv[1]
file2=sys.argv[2]
a=sys.argv[3] if len(sys.argv) >3  else "Uknown"
b=sys.argv[4]if len(sys.argv) >4  else "Uknown"
title=sys.argv[5] if len(sys.argv) >5  else "Uknown"
tuning=int(sys.argv[6]) if len(sys.argv) >6  else 0

def play_music(file):
    pygame.init()
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()

def MIDItoWAV (song): 
    
    file_name = os.path.splitext(os.path.basename(song))[0]
    new_file = file_name + '.wav'
    
    print("Playing ")
    play_music(song)
        
    frames = []
        
    # Record frames while the song is playing
    while pygame.mixer.music.get_busy():
        frames.append(stream.read(buffer))
            
    # Stop recording
    stream.stop_stream()
    stream.close()
        
    # Configure wave file settings
    wave_file = wave.open(new_file, 'wb')
    wave_file.setnchannels(channels)
    wave_file.setsampwidth(audio.get_sample_size(format))
    wave_file.setframerate(sample_rate)
        
    print("Saving " + new_file)   
     
    # Write the frames to the wave file
    wave_file.writeframes(b''.join(frames))
    wave_file.close()

    # End PyAudio    
    audio.terminate()
 
#---------converting MIDI to WAV----------------
filetype = os.path.splitext(os.path.basename(file1))[1]

if filetype==".mid":
    sample_rate = 44100        
    channels = 1                
    buffer = 1024
    pa = pyaudio.PyAudio()
    x=pa.get_default_input_device_info()
    input_device=x['index']
    format = pyaudio.paInt16
    audio = pyaudio.PyAudio()
    stream = audio.open(format=format, channels=channels, rate=sample_rate, input=True, input_device_index=input_device,
                    frames_per_buffer=buffer)
    MIDItoWAV(file1)
  
newfile = os.path.splitext(os.path.basename(file1))[0]
file1=newfile+'.wav'

#----------------Reading signals-----------------
x1,fs1=librosa.load(file1)
x2,fs2=librosa.load(file2)

t1=np.arange(0,len(x1))/float(fs1)
t2=np.arange(0,len(x2))/float(fs2)

#-------------CENS Features - Normalized with Manhatann Norm-----------------------
l=41
chr1=librosa.feature.chroma_cens(y=x1,sr=fs1,norm=1,win_len_smooth=l)
if tuning==0:
    chr2=librosa.feature.chroma_cens(y=x2,sr=fs2,norm=1,win_len_smooth=l)
else:
    chr2=librosa.feature.chroma_cens(y=x2,sr=fs2,norm=1,tuning=tuning, win_len_smooth=l)
#---------------Cost Matrix----------------------
xt=np.transpose(chr1)
yt=np.transpose(chr2)
C = scipy.spatial.distance.cdist(yt,xt, 'cosine')

#-------------------Accumulated Cost Matrix---------------------

@jit(nopython=True)
def compute_accumulated_cost_matrix(C):

    N, M = C.shape
    D = np.zeros((N, M))
    D[:, 0] = np.cumsum(C[:, 0])
    D[0, :] = np.cumsum(C[0, :])
    for n in range(1, N):
        for m in range(1, M):
            D[n, m] = C[n, m] + min(D[n-1, m], D[n, m-1], D[n-1, m-1])
    return D

D =  compute_accumulated_cost_matrix(C)

#--------------Wapring Path------------
@jit(nopython=True)
def compute_optimal_warping_path(D):

    N, M = D.shape
    n = N - 1
    m = M - 1
    P = [(n, m)]

    while n > 0:
        if m == 0:
            cell = (n - 1, 0)
        else:
            val = min(D[n-1, m-1], D[n-1, m], D[n, m-1])
            if val == D[n-1, m-1]:
                cell = (n-1, m-1)
            elif val == D[n-1, m]:
                cell = (n-1, m)
            else:
                cell = (n, m-1)
        P.append(cell)
        n, m = cell
    P.reverse()
    return np.array(P)
        
path = compute_optimal_warping_path(D)

#----------Warping Path in Time Domain-------------------------
path_s = path * 512 / fs1 #512 is the hop size

#---------------dynamics to db-------------------
S1 = np.abs(librosa.stft(x1))
S2 = np.abs(librosa.stft(x2))

S1_mean=np.sum(S1,axis=0)
S2_mean=np.sum(S2,axis=0)
pref=max(np.max(S1),np.max(S2))
S1db=librosa.amplitude_to_db(S1_mean,ref=pref)
S2db=librosa.amplitude_to_db(S2_mean,ref=pref)

#---------------Initializing logfile-------------------
logfile="FlameCens_"+file1+"_"+file2+"_dev.csv"
f=open(logfile,"w")
f.write("Time(sec),Tempo(sec),Dynamics(db)\n")
f.close()

#---------------mapping of temporal deviation and dynamics difference-----------------
#---------------mapping of temporal deviation and dynamics difference-----------------
dev=[]
db=[]
f=open(logfile,"a")
for i in range (1,len(path_s)):
    if path_s[i-1,0] != path_s[i,0]:
        time_diff=path_s[i-1,1]-path_s[i-1,0] #temporal deviation
        dev.append(path_s[i-1,1]-path_s[i-1,0])
        timing=np.round_(path_s[i-1,0],3)
        indexs1=path[i-1,1]
        indexs2=path[i-1,0]
        db_diff=S2db[indexs2]-S1db[indexs1] #dynamics difference in db
        db.append(db_diff)
        f.write("%s,%s,%s\n" % (str(timing),str(np.round(time_diff,3)),str(np.round(db_diff,3))))
        
f.close()
dev=np.asarray(dev)
db=np.asarray(db)
point=max(abs(dev))
if point!=0:
    dev_norm=dev/point
else:
    dev_norm=dev
point=np.round(point,2)
S=np.interp(db, (db.min(), db.max()), (0, +8))


FPS = 60
WINDOWWIDTH = 800
WINDOWHEIGHT = 600
FIRE_YELLOW = pygame.image.load('fire_yellow.png')
linecolor=(255,0,0)

def particles(S,fs,dev,dev_sec,point,namea,nameb,title):
    global FPSCLOCK, DISPLAYSURF
    pygame.init()
    FPSCLOCK = pygame.time.Clock()  #time counter
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.mouse.set_visible(0)

    # particle_xysize Elements:
    # Its a List of Lists, where particle_xysize[element][0,1,2,3,4,5,6..]
    # 0=x
    # 1=y
    # 2=size(squared-same x,y size)
    # 3,4=direction
    # 5=type
    # 6=dynamics aspect
    # 7=color(RGB)
    #8=influence
    
    particles = 720
    particle_xysize = []
    while particles > 0:
        particle_xysize.append([0,0,0,0,0,0,0,(0,0,0),(0,0)])
        particles -= 1

    velocity = []
    for particle in particle_xysize:
        velocity.append(5)

    init_x = 400
    init_y = 600
    pygame.mixer.music.load(file2)
    pygame.mixer.music.play(0)
    color2=(255,255,0)
    t=0
    a = datetime.datetime.now()
    while True:
              
        # Get Events of Game Loop
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                pygame.mixer.music.stop()
                pygame.quit()
                sys.exit()
                       
        # Drawing Axis
        DISPLAYSURF.fill((0, 0, 0))
        pygame.draw.line(DISPLAYSURF,linecolor,(400,0),(400,600))
        pygame.draw.line(DISPLAYSURF,linecolor,(0,300),(800,300))
        pygame.draw.line(DISPLAYSURF,linecolor,(100,290),(100,310))
        pygame.draw.line(DISPLAYSURF,linecolor,(175,295),(175,305))
        pygame.draw.line(DISPLAYSURF,linecolor,(250,290),(250,310))
        pygame.draw.line(DISPLAYSURF,linecolor,(325,295),(325,305))
        pygame.draw.line(DISPLAYSURF,linecolor,(700,290),(700,310))
        pygame.draw.line(DISPLAYSURF,linecolor,(625,295),(625,305))
        pygame.draw.line(DISPLAYSURF,linecolor,(550,290),(550,310))
        pygame.draw.line(DISPLAYSURF,linecolor,(475,295),(475,305))
        
        #Displaying Info
        myFont = pygame.font.SysFont("Helvetica", 20)
        song_title=myFont.render(title, 1,color2)
        label2=myFont.render("By : ", 1,linecolor)
        label3=myFont.render("Compared to : ", 1,linecolor)
        pianist = myFont.render(nameb, 1,color2)
        compared = myFont.render(namea, 1,color2)
        DISPLAYSURF.blit(song_title, (3, 3))
        DISPLAYSURF.blit(label2, (3, 22))
        DISPLAYSURF.blit(pianist, (35, 22))
        DISPLAYSURF.blit(label3, (3, 42))
        DISPLAYSURF.blit(compared, (112, 42))
        
        # Draw Elements
        for element in range(len(particle_xysize)):
            width = particle_xysize[element][2]
            height = particle_xysize[element][2]
            particle_x = particle_xysize[element][0]
            particle_y = particle_xysize[element][1]
            dynamics = particle_xysize[element][6]
            influence = particle_xysize[element][8]
            color = particle_xysize[element][7]
            

            particle_x += velocity[element]  * particle_xysize[element][4] * dynamics
            particle_y += velocity[element]  * particle_xysize[element][3] * dynamics
            
    
            if particle_xysize[element][5] == 0:
                pygame.draw.ellipse(DISPLAYSURF, color, (particle_x - width , particle_y - height , width*2, height*2))
            elif particle_xysize[element][5] == 1:
                fire_yellow = pygame.transform.scale(FIRE_YELLOW, (int(width * 2), int(height * 2)))
                DISPLAYSURF.blit(fire_yellow,[particle_x - width,particle_y - height])
                

            
            if particle_xysize[element][2] > 0:
                particle_xysize[element][2] -= 0.5
                velocity[element] += 2
            else:
                while True:
                    b = datetime.datetime.now()
                    c = b - a
                    t=c.total_seconds()
                    
                    #Displaying Time and Deviation
                    randNumLabel = myFont.render("Time:(sec)", 1, linecolor)
                    timeDisplay = myFont.render(str(round(t,2)), 1,color2)
                    DISPLAYSURF.blit(randNumLabel, (600, 3))
                    DISPLAYSURF.blit(timeDisplay, (600, 23))
                    idx=librosa.time_to_frames(t,sr=fs, hop_length=512)
                    val=S[idx]
                    min_dev = myFont.render(str(-1*point), 1, color2)
                    half=round(point/2)
                    half_minus = myFont.render(str(-1*half), 1, color2)
                    DISPLAYSURF.blit(min_dev, (75, 260))
                    DISPLAYSURF.blit(half_minus, (230, 260))
                    max_dev = myFont.render(str(point), 1, color2)
                    half_plus = myFont.render(str(half), 1, color2)
                    DISPLAYSURF.blit(max_dev, (680, 260))
                    DISPLAYSURF.blit(half_plus, (535, 260))
                    text3 = myFont.render("Deviation(sec)", 1, color2)
                    DISPLAYSURF.blit(text3, (5, 310))
                    text1=myFont.render("Temporal Deviation (sec)",1,linecolor)
                    DISPLAYSURF.blit(text1, (600, 43))
                    timeDev = myFont.render(str(round(dev_sec[idx-1],2)), 1,color2)
                    DISPLAYSURF.blit(timeDev, (600, 63))
                    
                    if idx==(len(S)-1):
                        pygame.mixer.music.stop()
                        pygame.quit()
                        sys.exit()
                    
                    particle_xysize[element][3] = -1
                    particle_xysize[element][4] = dev[idx]
                    particle_xysize[element][5] = 1
                    particle_xysize[element][7] = (80,100,150)
                    particle_xysize[element][6] = val
                    particle_xysize[element][8] = (1,1)
                    particle_xysize[element][2] = random.randint(1, 15)
                    velocity[element] = 0
                    particle_xysize[element][0], particle_xysize[element][1] = init_x, init_y
                    break

        pygame.display.update()
        FPSCLOCK.tick(FPS)

particles(S,fs2,dev_norm,dev,point,a,b,title)


 


