import matplotlib.pyplot as plt
import numpy as np
from skimage.measure import label, regionprops
from skimage.io import imread
from pathlib import Path

save_path = Path(__file__).parent

def count_holes(region):
    shape = region.image.shape
    new_image = np.zeros((shape[0] + 2, shape[1] + 2))
    new_image[1:-1, 1:-1] = region.image
    new_image = np.logical_not(new_image)
    labeled = label(new_image)
    return np.max(labeled) - 1

def count_lines(region):
    shape = region.image.shape
    image = region.image
    vlines = (np.sum(image, 0) / shape[0] == 1).sum()
    hlines = (np.sum(image, 1) / shape[1] == 1).sum()
    return vlines, hlines

def extractor(region):
    cy, cx = region.centroid_local
    cy /= region.image.shape[0]
    cx /= region.image.shape[1]
    perimeter = region.perimeter / region.image.size
    holes = count_holes(region)
    v, h = count_lines(region)
    v /= region.image.shape[1]
    h /= region.image.shape[0]
    eccentricity = region.eccentricity
    aspect = region.image.shape[0] / region.image.shape[1]
    return np.array([region.area / region.image.size, cy, cx, perimeter, holes, v, h, eccentricity, aspect])

def symmetry(region,tranpose=False):
    image=region.image
    if tranpose:
        image=image.T
    shape=image.shape
    top=image[:shape[0]//2]
    if shape[0]%2!=0:
        bottom=image[shape[0]//2+1:]
    else:
        bottom=image[shape[0]//2:]
    bottom=bottom[::-1]#np.flipud
    rezult=bottom==top
    return rezult.sum()/rezult.size

def classificator(region):
    holes=count_holes(region)
    if holes==2: # B, 8
        v,_=count_lines(region)
        v/=region.image.shape[1]
        if v>0.2:
            return "B"
        else:
            return "8"
    elif holes==1:# A,O
        # for p and d
        v, _ = count_lines(region)
        if v > 0:
            if symmetry(region) > 0.8:
                return "D"
            cy, _ = region.centroid_local
            if cy / region.image.shape[0] < 0.5:
                return "P"
            return "A"
        elif symmetry(region) > 0.7:
                return "0"
        else:
            return "A"
    elif holes==0: # 1,W, X,* -,/
        if region.image.sum()/region.image.size>0.95:
            return "-"
        shape=region.image.shape
        aspect=np.min(shape)/np.max(shape)
        if aspect>0.9:
            return "*"
        v_asym=symmetry(region)
        h_asym=symmetry(region,tranpose=True)
        if v_asym>0.8 and h_asym>0.8:
            return "X"
        elif h_asym>0.8:
            return "W"
        v,_=count_lines(region)
        if v>1:
            return "1"
        else:
            return "/"
    return"?"


template = imread('alphabet_ext.png')[:, :, :-1]
print(template.shape)
template = template.sum(2)
binary = template != 765

labeled = label(binary)
props = regionprops(labeled)
print(props[0].area, props[0].centroid, props[0].label)
# for prop in props:
#     plt.imshow(prop.image)
#     plt.show
()

templates = dict()

for region, symbol in zip(props, ['8', '0', 'A', 'B', '1', 'W', 'X', '*', '/', '-', 'P', 'D']):
        templates[symbol] = extractor(region)

# print(templates)
# print(classificator(props[0], templates))

image = imread('symbols.png')[:, :, :-1]
a_binary = image.mean(2) > 0
a_labeled = label(a_binary)
print(np.max(a_labeled))

a_props = regionprops(a_labeled)
a_templates = dict()
image_path = save_path / 'out_tree'
image_path.mkdir(exist_ok=True)

plt.figure(figsize=(5, 7))

for region in a_props:
    symbol = classificator(region)
    if symbol not in a_templates:
        a_templates[symbol] = 0
    a_templates[symbol] += 1
    plt.cla()
    plt.title(f'class - "{symbol}"')
    plt.imshow(region.image)
    plt.savefig(image_path / f'image_{region.label}.png')

print("Частотный словарь:")
print(a_templates)


plt.imshow(a_binary)
plt.show()
