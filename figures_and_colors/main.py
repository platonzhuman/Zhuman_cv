import numpy as np
from skimage.measure import label, regionprops
from skimage.io import imread
from skimage.color import rgb2hsv

image = imread("balls_and_rects.png")
hsv = rgb2hsv(image)
labeled = label(hsv[:, :, 2] > 0)  # Маркируем всё, что не черный фон
regions = regionprops(labeled, intensity_image=hsv[:, :, 0])

result = {}
for r in regions:
    hue = round(r.intensity_mean, 2)
    if hue not in result: result[hue] = {"rect": 0, "circles": 0}
    
    shape_type = "rect" if r.extent > 0.85 else "circles"
    result[hue][shape_type] += 1

print(f"ALL FIGURe: {len(regions)}")
for hue, counts in result.items():
    print(f"Ottenok == {hue} | \n | Pramougol == {counts['rect']} | \n | Krug == {counts['circles']} \n")
 