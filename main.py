import ws2812
#import uasyncio
import utime
import random

BLACK = (0, 0, 0)
RED = (122, 0, 0)
YELLOW = (122, 75, 0)
GREEN = (0, 122, 0)
CYAN = (0, 122, 122)
BLUE = (0, 0, 122)
PURPLE = (90, 0, 122)
BROWN = (150,33,7)
HWHITE = (122, 122, 122)
FWHITE = (255,255,255)
COLORS = (BLACK, RED, YELLOW, GREEN, CYAN, BLUE, PURPLE, HWHITE)
         

def blank():    
    ws2812.pixels_fill(BLACK)

    
    
#async def numbertest1():
#    try:
#        pn = input("Pixel number? ")
#        pn = int(pn)
#        ws2812.pixels_set(pn, FWHITE)
#        await ws2812.pixels_show()
#    except uasyncio.CancelledError:
#        pass


def setpixel(a,b):
        ws2812.pixels_set(a,b)
        



def fillrange(a,b,c):
    while a <= b:
        ws2812.pixels_set(a,c)
        a=a+1
    

# async def main1(a,b,c):
#     running_task = uasyncio.create_task(fillrange(a,b,c))
#     await running_task
#     
# async def clear():
#     running_task = uasyncio.create_task(blank())
#     await running_task


# BLACK = (0, 0, 0)
# RED = (122, 0, 0)
# YELLOW = (122, 75, 0)
# GREEN = (0, 122, 0)
# CYAN = (0, 122, 122)
# BLUE = (0, 0, 122)
# PURPLE = (90, 0, 122)
# BROWN = (112, 52, 0)
# HWHITE = (122, 122, 122)
# FWHITE = (255,255,255)

starts = [279, 278, 247, 245, 198, 196, 146, 144, 97]
directions = [1, -1, 1, -1, 1, -1, 1, -1, 1]
number_of_lights = [4, 16, 15, 23, 24, 25, 25, 23, 24]
snowing = []

flashinglist = [0,0,0,0,0,0,0,0]
startvalues = [11,16,21,25,43,48,53,58]
endvalues =   [15,20,24,32,47,52,57,61]
redorblue = 0

for i in range(len(flashinglist)):
                flashinglist[i] = random.randint(startvalues[i],endvalues[i])

if __name__ == "__main__":
        
    starttime = utime.ticks_ms()
    
    blank()
    ws2812.pixels_show()
    
    #snow_x_position = random.randint(0,24)
    
    #print(snow_x_position)
    
    while True:
       
        blank()
       
        ticks = utime.ticks_diff(utime.ticks_ms(), starttime)
        starcolour = abs((((ticks % 2000) - 1000) * 255) // 1000)
        #snow_y_position = (ticks % 2000) // 224
        
        if starcolour <= 2:
            for i in range(len(flashinglist)):
                flashinglist[i] = random.randint(startvalues[i],endvalues[i])
        
        if random.randint(0,1000) < 250:
            snowing.append({"start":utime.ticks_ms(), "x":random.randint(0,24)})
            
        
        
         
#  TREE
        fillrange(0, 6, HWHITE)
        fillrange(7, 10, BROWN)
        fillrange(11, 32, GREEN)
        fillrange(33, 37, (starcolour, starcolour, 0))
        fillrange(38, 61, GREEN)
        fillrange(62, 64, BROWN)
        fillrange(65, 71, HWHITE)
        
# TREE LIGHTS
        
        for i in range(len(flashinglist)):
            if redorblue == 0: # make red
                setpixel(flashinglist[i],(starcolour,0,0))
                redorblue = 1
            elif redorblue == 1:
                setpixel(flashinglist[i],(0,0,starcolour))
                redorblue = 0
        
#         setpixel(11, (0, 0, starcolour))
#         setpixel(16, (starcolour,0,0))
#         setpixel(21, (0, 0, starcolour))
#         setpixel(26, (starcolour,0,0))
#         
#         setpixel(43, (0, 0, starcolour))
#         setpixel(48, (starcolour,0,0))
#         setpixel(53, (0, 0, starcolour))
#         setpixel(58, (starcolour,0,0))
        
# SNOW FLOOR
        fillrange(72,95, HWHITE)
        
# SNOW FALLING
        #offset = (snow_x_position * directions[snow_y_position])
        
        for snow in snowing:
            
            # snow_y_position = (snowing["start"] % 2000) // 224
            
            snow_y_position = (utime.ticks_diff(utime.ticks_ms(), snow["start"]) % 2000) // 224
            
            
            if snow["x"] < number_of_lights[snow_y_position]:
                setpixel(starts[snow_y_position] + snow["x"] * directions[snow_y_position] , HWHITE)
        
#         if snow_x_position < number_of_lights[snow_y_position]:
#             setpixel(starts[snow_y_position] + snow_x_position * directions[snow_y_position] , HWHITE)
        
        if len(snowing) > 0:
            elapsed_ms = utime.ticks_diff(utime.ticks_ms(),snowing[0]["start"])
            
            if elapsed_ms >= 2000:
            
                snowing.pop(0)
            
        # setpixel(starts[snow_y_position], HWHITE)
        
# SHOW ALL CHANGES
        ws2812.pixels_show()
    
    


