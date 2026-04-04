import numpy as np
from skimage.measure import label, regionprops
from skimage.morphology import erosion

image = np.load("stars.npy")
#решил проще просто от общего отнять квадраты
def star(image):
    labeled = label(image)
    reg = regionprops(labeled)
    
    al = len(reg)
    
    count_kvadrat = 0
    
    struct = np.ones((3, 3))
    
    for i in reg:
        if np.any(erosion(i.image, footprint=struct)):
            count_kvadrat += 1
            
    star_count = al - count_kvadrat
    return star_count

result = star(image)
print(f"count stars = {result}")


