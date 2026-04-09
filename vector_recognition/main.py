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

def classificator(region, templates):
    features = extractor(region)
    result = ''
    min_d = 10 ** 16
    for symbol, t in templates.items():
        d = ((t - features) ** 2).sum() ** 0.5
        if d < min_d:
            result = symbol
            min_d = d
    return result

template = imread('Alphabet-small.png')[:, :, :-1]
print(template.shape)
template = template.sum(2)
binary = template != 765

labeled = label(binary)
props = regionprops(labeled)

templates = dict()

for region, symbol in zip(props, ['8', '0', 'A', 'B', '1', 'W', 'X', '*', '/', '-']):
        templates[symbol] = extractor(region)

image = imread('Alphabet.png')[:, :, :-1]
a_binary = image.mean(2) > 0
a_labeled = label(a_binary)
print(f"Всего символов: {np.max(a_labeled)}")

a_props = regionprops(a_labeled)
a_templates = dict()
image_path = save_path / 'out'
image_path.mkdir(exist_ok=True)

plt.figure(figsize=(5, 7))

for region in a_props:
    symbol = classificator(region, templates)
    if symbol not in a_templates:
        a_templates[symbol] = 0
    a_templates[symbol] += 1
    plt.cla()
    plt.title(f'class - "{symbol}"')
    plt.imshow(region.image)
    plt.savefig(image_path / f'image_{region.label}.png')

print(f"Распознано: {a_templates['8']} символов")
plt.imshow(a_binary)
plt.show()