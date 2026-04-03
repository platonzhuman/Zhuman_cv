import numpy as np
from skimage.measure import label, regionprops

image = np.load("stars.npy")

def star(image):
    labeled = label(image)
    region = regionprops(labeled)
    
    pl_count = 0
    cr_count = 0
    
    for reg in region:
        star_image = reg.image
        
        pixel = star_image[0, 0] + star_image[0, -1] + \
                        star_image[-1, 0] + star_image[-1, -1]
        
        if pixel > 0:
            cr_count += 1
        else:
            pl_count += 1
            
    return pl_count, cr_count

p, c = star(image)
print(f"плюсов: {p}, керестов: {c}")
